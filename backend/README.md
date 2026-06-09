# Backend — EH Brewing API

API REST + WebSocket construída com **FastAPI** para monitoramento em tempo real de temperatura das panelas de fermentação da EH Brewing.

---

## Sumário

- [Stack Tecnológico](#stack-tecnológico)
- [Arquitetura](#arquitetura)
- [Estrutura de Pastas](#estrutura-de-pastas)
- [Modelos de Dados](#modelos-de-dados)
- [Endpoints da API](#endpoints-da-api)
- [Sistema de Autenticação](#sistema-de-autenticação)
- [WebSocket](#websocket)
- [Banco de Dados e Migrations](#banco-de-dados-e-migrations)
- [Testes](#testes)
- [Lint e Qualidade de Código](#lint-e-qualidade-de-código)

---

## Stack Tecnológico

| Tecnologia | Versão | Função |
|---|---|---|
| Python | 3.11 | Linguagem principal |
| FastAPI | latest | Framework web async |
| SQLAlchemy | latest | ORM para banco de dados |
| Pydantic v2 | ≥2.0 | Validação de dados e schemas |
| TimescaleDB | PG16 | Banco de dados de série temporal |
| Redis | 7 | Pub/Sub para distribuição de mensagens |
| Alembic | latest | Migrations de banco de dados |
| python-jose | ≥3.3 | Geração e validação de tokens JWT |
| passlib + bcrypt | bcrypt==4.0.1 | Hash seguro de senhas |
| Uvicorn | latest | Servidor ASGI |
| pytest | ≥8.0 | Framework de testes |
| Ruff | ≥0.6 | Linter e formatador Python |

---

## Arquitetura

O backend segue uma arquitetura orientada a eventos com os seguintes fluxos principais:

### Fluxo de uma Leitura de Temperatura

```
CLP (ou simulador)
       ↓
POST /api/v1/readings { tank_id, temperature }
       ↓
FastAPI valida com Pydantic v2
       ↓
Persiste no TimescaleDB (tabela readings — hypertable)
       ↓
Publica no canal Redis  →  tanks:{id}:readings
       ↓
Motor de alertas verifica faixa configurada (temp_min / temp_max)
    ├─ fora da faixa → cria Alert no banco
    └─ dentro da faixa → resolve Alert ativo se existir
       ↓
WebSocket subscriber recebe do Redis e faz broadcast
       ↓
Dashboard React re-renderiza em tempo real
```

### Fluxo de Autenticação

```
POST /auth/login { username, password }
       ↓
Verifica hash bcrypt no banco
       ↓
Gera access_token (JWT, 15min) + refresh_token (JWT, 7 dias)
       ↓
Armazena hash do refresh_token no banco (tabela refresh_tokens)
       ↓
Retorna { access_token, refresh_token, token_type }

POST /auth/refresh { refresh_token }
       ↓
Verifica assinatura JWT + JTI no banco (não revogado)
       ↓
Revoga token antigo + emite novo par de tokens (rotação)

POST /auth/logout { refresh_token }
       ↓
Marca JTI como revogado no banco
```

---

## Estrutura de Pastas

```
backend/
├── api/                        # Código-fonte principal
│   ├── main.py                 # App FastAPI, todos os endpoints, hub WebSocket
│   ├── models.py               # Modelos SQLAlchemy (entidades do banco)
│   ├── schemas.py              # Schemas Pydantic (request/response)
│   ├── auth.py                 # JWT, bcrypt, helpers de autenticação
│   ├── database.py             # Engine SQLAlchemy, SessionLocal, Base
│   ├── alembic.ini             # Configuração do Alembic
│   ├── migrations/             # Migrations versionadas
│   │   └── versions/
│   │       ├── 001_initial_schema.py   # Esquema inicial
│   │       ├── 002_hypertable.py       # Converte readings em hypertable
│   │       └── 003_tank_control.py     # Tabela de controle de panela
│   └── scripts/
│       ├── seed_tanks.py               # Popula 8 panelas + usuário admin
│       └── test_websocket_clients.py   # Script de teste manual de WS
├── db/
│   └── init-timescale.sql      # Ativa extensão TimescaleDB no PostgreSQL
├── tests/
│   ├── conftest.py             # Fixtures pytest (SQLite em memória, TestClient)
│   ├── helpers.py              # Funções auxiliares (make_user, make_tank, etc.)
│   ├── test_api.py             # Testes de endpoints (auth, tanks, readings, alerts, batches)
│   ├── test_auth.py            # Testes unitários de auth.py (hash, JWT)
│   ├── test_integration.py     # Testes de integração (fluxos completos)
│   ├── test_schemas.py         # Testes de validação dos schemas Pydantic
│   └── test_utils.py           # Testes de funções utilitárias
├── Dockerfile
├── entrypoint.sh               # Roda migrations + inicia Uvicorn
├── requirements.txt            # Dependências de produção
├── requirements-dev.txt        # Dependências de desenvolvimento/testes
└── pyproject.toml              # Configuração de Ruff e pytest
```

---

## Modelos de Dados

### `User`
Usuário do sistema com controle de acesso por role.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID do usuário |
| `username` | String UNIQUE | Nome de usuário |
| `hashed_password` | String | Hash bcrypt da senha |
| `role` | String | `admin`, `operador` ou `viewer` |

### `RefreshToken`
Armazena tokens de refresh para controle de revogação por JTI.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID do token |
| `jti` | String UNIQUE | JWT ID único do token |
| `user_id` | FK → User | Usuário dono do token |
| `token_hash` | String | Hash SHA-256 do token |
| `expires_at` | DateTime | Data de expiração |
| `revoked` | Boolean | Se o token foi revogado |

### `Tank`
Representa uma panela de fermentação.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID da panela |
| `name` | String | Nome (ex: "Panela 1") |
| `temp_min` | Float | Temperatura mínima permitida (°C) |
| `temp_max` | Float | Temperatura máxima permitida (°C) |
| `current_temperature` | Float | Última temperatura registrada |
| `last_reading_at` | DateTime | Timestamp da última leitura |

### `Reading`
Leitura de temperatura — hypertable TimescaleDB (particionada por tempo).

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID da leitura |
| `tank_id` | FK → Tank | Panela que originou a leitura |
| `temperature` | Float | Temperatura medida (°C) |
| `recorded_at` | DateTime | Timestamp da leitura |

### `Alert`
Alerta disparado quando a temperatura sai da faixa configurada.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID do alerta |
| `tank_id` | FK → Tank | Panela com problema |
| `temperature` | Float | Temperatura que disparou o alerta |
| `fired_at` | DateTime | Quando o alerta foi disparado |
| `resolved_at` | DateTime | Quando foi resolvido (null = ativo) |
| `acknowledged` | Boolean | Se foi reconhecido pelo operador |

### `YeastProfile`
Perfil de levedura reutilizável em múltiplos lotes.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID do perfil |
| `name` | String UNIQUE | Nome da levedura (ex: "WY1056") |
| `strain` | String | Linhagem/strain |
| `temp_min` | Float | Faixa ideal mínima (°C) |
| `temp_max` | Float | Faixa ideal máxima (°C) |
| `description` | String | Notas sobre a levedura |

### `Batch`
Lote de produção com ciclo de vida completo.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID do lote |
| `name` | String | Nome do lote |
| `style` | String | Estilo da cerveja |
| `status` | String | `planned`, `active`, `completed`, `cancelled` |
| `original_gravity` | Float | Densidade inicial (OG) |
| `final_gravity` | Float | Densidade final (FG) |
| `abv` | Float | Calculado automaticamente (ABV%) |
| `yeast_profile_id` | FK → YeastProfile | Perfil de levedura usado |
| `events` | JSON | Log de eventos do lote |
| `started_at` | DateTime | Início da fermentação |
| `completed_at` | DateTime | Fim da fermentação |

---

## Endpoints da API

### Health
| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/health` | ❌ | Status da API |

### Autenticação
| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| POST | `/register` | ❌ | Criar novo usuário |
| POST | `/auth/login` | ❌ | Login — retorna tokens |
| POST | `/auth/refresh` | ❌ | Renovar tokens |
| POST | `/auth/logout` | ❌ | Revogar refresh token |

### Panelas
| Método | Endpoint | Role mínimo | Descrição |
|---|---|---|---|
| GET | `/api/v1/tanks` | viewer | Listar todas as panelas |
| GET | `/api/v1/tanks/{id}/status` | viewer | Status de uma panela |
| PATCH | `/api/v1/tanks/{id}/config` | admin | Editar nome e faixa de temperatura |
| GET | `/api/v1/tanks/{id}/readings` | viewer | Histórico de leituras por período |

### Leituras
| Método | Endpoint | Role mínimo | Descrição |
|---|---|---|---|
| POST | `/api/v1/readings` | operador | Enviar nova leitura de temperatura |

### Alertas
| Método | Endpoint | Role mínimo | Descrição |
|---|---|---|---|
| GET | `/api/v1/alerts` | viewer | Listar alertas (filtro por status/tank) |
| PATCH | `/api/v1/alerts/{id}/acknowledge` | operador | Reconhecer alerta |

### Lotes
| Método | Endpoint | Role mínimo | Descrição |
|---|---|---|---|
| GET | `/api/v1/batches` | viewer | Listar lotes (filtro por status) |
| POST | `/api/v1/batches` | operador | Criar novo lote |
| GET | `/api/v1/batches/{id}` | viewer | Detalhe de um lote |
| PATCH | `/api/v1/batches/{id}` | operador | Atualizar lote |
| PATCH | `/api/v1/batches/{id}/events` | operador | Adicionar evento ao lote |
| GET | `/api/v1/batches/{id}/export` | viewer | Exportar lote (CSV) |

### Perfis de Levedura
| Método | Endpoint | Role mínimo | Descrição |
|---|---|---|---|
| GET | `/api/v1/yeast_profiles` | viewer | Listar perfis |
| POST | `/api/v1/yeast_profiles` | admin | Criar perfil |
| GET | `/api/v1/yeast_profiles/{id}` | viewer | Detalhe do perfil |
| PATCH | `/api/v1/yeast_profiles/{id}` | admin | Atualizar perfil |
| DELETE | `/api/v1/yeast_profiles/{id}` | admin | Deletar perfil |

### Documentação
| URL | Descrição |
|---|---|
| `/docs` | Swagger UI (interativo) |
| `/redoc` | ReDoc (leitura) |

---

## Sistema de Autenticação

### JWT com Rotação de Refresh Token

O sistema implementa autenticação stateful com dois tipos de token:

- **Access Token** — validade de 15 minutos, enviado no header `Authorization: Bearer <token>`
- **Refresh Token** — validade de 7 dias, usado para emitir novos pares sem re-login

Cada token carrega um `jti` (JWT ID) único. O refresh token é armazenado como hash SHA-256 no banco, garantindo que o token em si nunca seja armazenado em texto plano.

### Roles e Permissões

```
admin    → acesso total (leitura + escrita + configuração)
operador → leitura + envio de leituras + gestão de lotes
viewer   → apenas leitura (temperaturas, alertas, lotes)
```

### Senhas

Senhas são hashadas com `bcrypt` (work factor padrão). A versão `4.0.1` é fixada no `requirements.txt` para compatibilidade com `passlib`.

---

## WebSocket

O endpoint WebSocket permite que o frontend receba atualizações em tempo real sem polling.

**Endpoint:** `ws://localhost:8000/ws/tanks/{tank_id}`

**Autenticação:** token JWT passado via header `Authorization: Bearer <token>`

**Fluxo:**
1. Cliente conecta ao WebSocket da panela desejada
2. API registra o socket no hub de conexões daquela panela
3. Quando uma nova leitura chega via `POST /api/v1/readings`, ela é publicada no Redis (`tanks:{id}:readings`)
4. O subscriber Redis repassa a mensagem para todos os WebSockets conectados àquela panela

**Mensagem recebida:**
```json
{
  "tank_id": 3,
  "temperature": 14.7,
  "recorded_at": "2025-06-09T10:30:00Z"
}
```

Redis atua como intermediário, permitindo múltiplos workers Uvicorn sem perda de mensagens.

---

## Banco de Dados e Migrations

O projeto usa **TimescaleDB** (extensão PostgreSQL) para armazenar séries temporais de temperatura com queries até 100× mais rápidas que PostgreSQL puro.

A tabela `readings` é uma **hypertable** particionada automaticamente por tempo.

### Migrations com Alembic

```bash
# Aplicar todas as migrations
alembic upgrade head

# Ver histórico
alembic history

# Criar nova migration (após alterar models.py)
alembic revision --autogenerate -m "descricao da mudança"
```

As migrations ficam em `api/migrations/versions/` e são executadas automaticamente pelo `entrypoint.sh` quando o container sobe.

---

## Testes

A suite usa **pytest** com banco **SQLite em memória** — sem necessidade de PostgreSQL ou Redis reais no CI.

Redis é mockado com `AsyncMock` via `unittest.mock`.

### Rodar os testes

```bash
# Dentro de backend/
pip install -r requirements-dev.txt
python -m pytest tests/ -v

# Com relatório de cobertura
python -m pytest tests/ --cov=api --cov-report=term-missing -v

# Rodar apenas um arquivo de testes
python -m pytest tests/test_auth.py -v

# Rodar apenas uma classe de testes
python -m pytest tests/test_api.py::TestLogin -v
```

### Cobertura por módulo

| Módulo | Cobertura |
|---|---|
| `auth.py` | 100% |
| `database.py` | 100% |
| `models.py` | 100% |
| `schemas.py` | 100% |
| `main.py` | 81% |
| **Total** | **≥ 86%** |

Total: **132 testes** — execução em ~44 segundos.

---

## Lint e Qualidade de Código

O projeto usa **Ruff** para lint e formatação Python.

```bash
# Verificar erros de lint
python -m ruff check api/

# Corrigir automaticamente (quando possível)
python -m ruff check api/ --fix

# Formatação (estilo Black)
python -m ruff format api/
```

Configuração em `pyproject.toml` — regras habilitadas: `E`, `F`, `I` (isort).
