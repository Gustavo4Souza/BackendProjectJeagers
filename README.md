# EH Brewing — Plataforma de Monitoramento de Temperatura

Sistema IoT de monitoramento em tempo real das 8 panelas de fermentação da EH Brewing. Leituras de temperatura a cada 5 segundos, dashboard React com WebSocket, sistema de alertas automáticos e controle de lotes.

---

## Sumário

- [Pré-requisitos](#pré-requisitos)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Como Rodar com Docker](#como-rodar-com-docker)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Comandos Docker Úteis](#comandos-docker-úteis)
- [Populando o Banco de Dados](#populando-o-banco-de-dados)
- [Simulador de CLP](#simulador-de-clp)
- [Lista de Testes para Validação](#lista-de-testes-para-validação)

---

## Pré-requisitos

Antes de começar, instale:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (inclui Docker e Docker Compose)
- Git

Verifique a instalação:

```bash
docker --version
docker compose version
```

---

## Estrutura do Projeto

```
BackendProjectJeagers/
├── docker-compose.yml          # Orquestração dos containers
├── backend/                    # API Python (FastAPI)
│   ├── api/                    # Código-fonte da aplicação
│   │   ├── main.py             # App FastAPI + endpoints + WebSocket
│   │   ├── models.py           # Modelos SQLAlchemy (ORM)
│   │   ├── schemas.py          # Schemas Pydantic (validação)
│   │   ├── auth.py             # Lógica JWT + hashing de senha
│   │   ├── database.py         # Conexão com banco de dados
│   │   ├── migrations/         # Migrations Alembic
│   │   └── scripts/            # Scripts utilitários (seed, etc.)
│   ├── db/
│   │   └── init-timescale.sql  # Inicialização do TimescaleDB
│   ├── tests/                  # Suite de testes (pytest)
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/                   # Dashboard React + TypeScript
│   ├── src/
│   │   ├── components/         # Componentes reutilizáveis
│   │   ├── pages/              # Páginas da aplicação
│   │   ├── hooks/              # Custom React hooks
│   │   ├── services/           # Clientes da API (Axios)
│   │   ├── context/            # React Context (AuthContext)
│   │   └── types/              # Tipos TypeScript
│   ├── package.json
│   └── vite.config.ts
└── simulator/
    └── clp_simulator.py        # Simulador de leituras do CLP
```

---

## Como Rodar com Docker

### 1. Clone o repositório

```bash
git clone https://github.com/Gustavo4Souza/BackendProjectJeagers.git
cd BackendProjectJeagers
```

### 2. Suba todos os serviços

```bash
docker compose up --build
```

Este comando:
- Constrói a imagem do backend (Python 3.11 + FastAPI)
- Sobe o banco de dados TimescaleDB (PostgreSQL 16)
- Sobe o Redis 7
- Inicia a API na porta `8000` com hot-reload ativado

> Na primeira execução, aguarde o banco de dados ficar saudável antes da API conectar. Isso é automático graças ao `depends_on` com health checks.

### 3. Acesse os serviços

| Serviço | URL |
|---|---|
| API (Swagger UI) | http://localhost:8000/docs |
| API (ReDoc) | http://localhost:8000/redoc |
| Health check | http://localhost:8000/health |
| TimescaleDB | `localhost:5432` |
| Redis | `localhost:6379` |

> O frontend **não roda via Docker** neste projeto. Para rodar o frontend, veja o [README do frontend](./frontend/README.md).

---

## Variáveis de Ambiente

O `docker-compose.yml` já define todas as variáveis necessárias para desenvolvimento local. Nenhuma configuração adicional é necessária para rodar localmente.

| Variável | Valor padrão (Docker) | Descrição |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://jeagers:jeagers@db:5432/jeagers` | URL de conexão com o banco |
| `REDIS_URL` | `redis://redis:6379/0` | URL de conexão com o Redis |
| `JWT_SECRET_KEY` | `dev-secret-change-me` | Chave secreta para assinar tokens JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Expiração do access token (minutos) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Expiração do refresh token (dias) |

> Em produção, substitua `JWT_SECRET_KEY` por um valor seguro gerado com `openssl rand -hex 32`.

---

## Comandos Docker Úteis

### Iniciar e parar

```bash
# Subir em background (modo detached)
docker compose up -d --build

# Subir exibindo logs no terminal
docker compose up --build

# Parar todos os containers (mantém os dados)
docker compose down

# Parar e remover volumes (APAGA todos os dados do banco)
docker compose down -v
```

### Logs

```bash
# Ver logs de todos os serviços
docker compose logs

# Ver logs apenas da API (com follow)
docker compose logs -f api

# Ver logs do banco de dados
docker compose logs -f db

# Ver logs do Redis
docker compose logs -f redis

# Ver as últimas 50 linhas de log da API
docker compose logs --tail=50 api
```

### Status e inspecção

```bash
# Ver status dos containers
docker compose ps

# Ver uso de recursos (CPU, memória)
docker stats

# Inspecionar um container específico
docker inspect jeagers-api
```

### Executar comandos dentro dos containers

```bash
# Abrir shell interativo no container da API
docker compose exec api bash

# Executar um comando Python dentro da API
docker compose exec api python -c "print('hello')"

# Acessar o banco de dados com psql
docker compose exec db psql -U jeagers -d jeagers

# Verificar conexão com o Redis
docker compose exec redis redis-cli ping
```

### Migrations do banco de dados

```bash
# Aplicar todas as migrations pendentes
docker compose exec api alembic upgrade head

# Ver o histórico de migrations
docker compose exec api alembic history

# Ver a migration atual aplicada
docker compose exec api alembic current

# Reverter a última migration
docker compose exec api alembic downgrade -1
```

### Reconstrução e limpeza

```bash
# Reconstruir apenas a imagem da API (sem cache)
docker compose build --no-cache api

# Remover containers parados, redes, imagens sem uso e cache de build
docker system prune

# Remover tudo, inclusive volumes (DESTRUTIVO)
docker system prune --volumes
```

---

## Populando o Banco de Dados

Após subir os containers, execute o script de seed para criar as 8 panelas e o usuário administrador:

```bash
docker compose exec api python scripts/seed_tanks.py --admin-password admin123
```

Isso cria:
- 8 panelas de fermentação com configurações padrão
- Usuário `admin` com senha `admin123` e role `admin`

### Criar usuários manualmente via API

Acesse http://localhost:8000/docs e use o endpoint `POST /register`:

```json
{
  "username": "operador1",
  "password": "senha123",
  "role": "operador"
}
```

Roles disponíveis: `admin`, `operador`, `viewer`

---

## Simulador de CLP

O simulador substitui o hardware físico durante desenvolvimento e demonstrações. Ele envia leituras de temperatura para a API a cada 5 segundos, simulando os controladores Novus N321-NTC.

**Pré-requisito:** Python 3.11+ instalado localmente (fora do Docker).

```bash
# Instalar dependência do simulador
pip install requests

# Modo normal — 8 panelas com temperatura realista (ruído gaussiano)
python simulator/clp_simulator.py

# Injetar falha: força panela 3 para 28°C (acima do limite, dispara alerta)
python simulator/clp_simulator.py --fault-tank 3 --fault-temp 28.0

# Rodar com intervalo personalizado (10 segundos por leitura)
python simulator/clp_simulator.py --interval 10

# Apontar para uma API remota
python simulator/clp_simulator.py --api-url https://seu-backend.railway.app
```

---

## Lista de Testes para Validação

Use esta lista para validar o funcionamento completo do sistema. Todos os testes devem ser executados com os containers rodando (`docker compose up -d`) e o banco populado (seed executado).

### Autenticação

- [ ] **Login válido** — `POST /auth/login` com `admin` / `admin123` retorna `access_token` e `refresh_token`
- [ ] **Login inválido** — senha errada retorna `401`
- [ ] **Refresh de token** — `POST /auth/refresh` com o refresh token retorna novos tokens
- [ ] **Logout** — `POST /auth/logout` revoga o refresh token; usar o token revogado retorna `401`
- [ ] **Rota protegida sem token** — `GET /api/v1/tanks` sem Authorization retorna `401`
- [ ] **Token inválido** — Bearer com string aleatória retorna `401`

### Panelas (Tanks)

- [ ] **Listar panelas** — `GET /api/v1/tanks` retorna lista com 8 panelas após o seed
- [ ] **Campos da panela** — resposta inclui `id`, `name`, `temp_min`, `temp_max`, `current_temperature`, `last_reading_at`
- [ ] **Status da panela** — `GET /api/v1/tanks/{id}/status` retorna `tank_status`
- [ ] **Status 404** — tanque inexistente retorna `404`
- [ ] **Admin edita config** — `PATCH /api/v1/tanks/{id}/config` com role `admin` retorna `200`
- [ ] **Viewer não pode editar** — mesmo endpoint com role `viewer` retorna `403`
- [ ] **Faixa inválida** — `temp_min > temp_max` retorna `400` ou `422`

### Leituras (Readings)

- [ ] **Operador envia leitura** — `POST /api/v1/readings` com `{"tank_id": 1, "temperature": 15.0}` retorna `201`
- [ ] **Admin envia leitura** — mesmo endpoint com role `admin` retorna `201`
- [ ] **Viewer não envia leitura** — role `viewer` retorna `403`
- [ ] **Panela inexistente** — `tank_id` inválido retorna `404`
- [ ] **Temperatura atualizada** — após enviar leitura, `GET /api/v1/tanks` mostra `current_temperature` atualizada
- [ ] **Leituras publicadas no Redis** — enviar leitura chama `redis.publish` (verificar nos logs da API)
- [ ] **Histórico de leituras** — `GET /api/v1/tanks/{id}/readings?period=24h` retorna lista
- [ ] **Períodos válidos** — aceita `6h`, `24h`, `7d`, `30d`
- [ ] **Período inválido** — `99h` retorna `422`

### Alertas

- [ ] **Alerta disparado** — enviar temperatura acima de `temp_max` cria alerta ativo
- [ ] **Alerta não duplicado** — duas leituras fora do limite mantêm apenas 1 alerta ativo
- [ ] **Alerta resolvido automaticamente** — leitura dentro do limite resolve alerta ativo
- [ ] **Listar alertas** — `GET /api/v1/alerts` retorna lista
- [ ] **Filtro por status** — `?status=active` e `?status=resolved` funcionam
- [ ] **Status inválido** — `?status=unknown` retorna `422`
- [ ] **Reconhecer alerta** — `PATCH /api/v1/alerts/{id}/acknowledge` retorna `200`
- [ ] **Reconhecer alerta inexistente** — retorna `404`

### Lotes (Batches)

- [ ] **Criar lote** — `POST /api/v1/batches` com operador retorna `201` e `status: planned`
- [ ] **Viewer não cria lote** — role `viewer` retorna `403`
- [ ] **Listar lotes** — `GET /api/v1/batches` retorna lista
- [ ] **Buscar lote por ID** — `GET /api/v1/batches/{id}` retorna detalhe
- [ ] **Lote 404** — ID inexistente retorna `404`
- [ ] **Atualizar lote** — `PATCH /api/v1/batches/{id}` com `{"status": "active"}` retorna `200`
- [ ] **Filtrar por status** — `?status=planned` retorna apenas lotes planejados
- [ ] **Adicionar evento** — `PATCH /api/v1/batches/{id}/events` com `gravity_reading` retorna `201`
- [ ] **Exportar CSV** — `GET /api/v1/batches/{id}/export?format=csv` retorna `Content-Type: text/csv`
- [ ] **Formato inválido** — `?format=pdf` retorna `400`
- [ ] **ABV calculado** — lote completo com `original_gravity` e `final_gravity` retorna `abv > 0`

### Perfis de Levedura (Yeast Profiles)

- [ ] **Listar perfis** — `GET /api/v1/yeast_profiles` retorna lista
- [ ] **Admin cria perfil** — `POST /api/v1/yeast_profiles` com `{"name": "WY1056"}` retorna `201`
- [ ] **Viewer não cria** — role `viewer` retorna `403`
- [ ] **Nome duplicado** — criar perfil com mesmo nome retorna `400`
- [ ] **Buscar por ID** — `GET /api/v1/yeast_profiles/{id}` retorna detalhe
- [ ] **ID inexistente** — retorna `404`
- [ ] **Atualizar perfil** — `PATCH /api/v1/yeast_profiles/{id}` retorna `200`
- [ ] **Deletar perfil** — `DELETE /api/v1/yeast_profiles/{id}` retorna `204`
- [ ] **Não deleta perfil vinculado a lote** — retorna `400`

### WebSocket

- [ ] **Conexão WebSocket** — conectar em `ws://localhost:8000/ws/tanks/{id}` estabelece conexão (status 101)
- [ ] **Mensagem recebida** — enviar leitura via API faz o WebSocket receber mensagem com `tank_id`, `temperature`, `recorded_at`
- [ ] **8 conexões simultâneas** — abrir 8 conexões (uma por panela) sem erro

### Documentação da API

- [ ] **Swagger UI** — http://localhost:8000/docs abre sem autenticação (200)
- [ ] **ReDoc** — http://localhost:8000/redoc abre sem autenticação (200)
- [ ] **Health check** — `GET /health` retorna `{"status": "ok"}` com campo `version`

### Controle de Acesso por Role

| Ação | viewer | operador | admin |
|---|:---:|:---:|:---:|
| Ver panelas, leituras, alertas | ✅ | ✅ | ✅ |
| Enviar leituras / criar lotes | ❌ | ✅ | ✅ |
| Configurar panelas / usuários | ❌ | ❌ | ✅ |

- [ ] **Todas as regras de role acima validadas** conforme tabela

---

## Executar os Testes Automatizados do Backend

Os testes rodam com SQLite em memória — não precisam do Docker.

```bash
# Entrar no container da API
docker compose exec api bash

# Instalar dependências de desenvolvimento (se necessário)
pip install -r /tmp/requirements-dev.txt

# Rodar os testes com relatório de cobertura
python -m pytest tests/ --cov=api --cov-report=term-missing -v
```

Ou localmente (fora do Docker), dentro de `backend/`:

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ --cov=api --cov-report=term-missing -v
```

Resultado esperado: **132 testes passando**, cobertura total **≥ 86%**.
