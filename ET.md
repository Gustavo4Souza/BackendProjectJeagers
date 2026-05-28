# Especificação Técnica — EH Brewing

**Projeto:** Plataforma de monitoramento de temperatura para panelas de armazenamento  
**Versão:** 0.1.0  
**Fase atual:** Fase 1 — Monitoramento (sem controle ativo de temperatura)  
**Data:** 2026-05-26

---

## 1. Visão Geral

Sistema web para monitoramento em tempo real da temperatura de 8 panelas de armazenamento de bebidas da EH Brewing. Leituras chegam via CLP (simulado em desenvolvimento) e são exibidas em dashboard com alertas automáticos.

---

## 2. Arquitetura Geral

```
CLP / Simulador
      ↓  POST /api/v1/readings
   FastAPI (Backend)
      ↓  INSERT → PostgreSQL / TimescaleDB
      ↓  PUBLISH → Redis Pub/Sub
   WebSocket Hub
      ↓  ws://
   Frontend React (Dashboard)
```

---

## 3. Stack de Tecnologia

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12 + FastAPI (async) |
| Banco de dados | PostgreSQL 16 + TimescaleDB |
| Cache / Pub/Sub | Redis 7 |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Validação | Pydantic v2 |
| Autenticação | JWT (HS256) + bcrypt |
| Servidor ASGI | Uvicorn |
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS |
| Gráficos | Recharts |
| HTTP client | Axios + React Query |
| Conteinerização | Docker + Docker Compose |

---

## 4. Estrutura de Arquivos

```
BackendProjectJeagers/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── api/
│       ├── main.py             # Aplicação FastAPI, rotas e WebSocket
│       ├── models.py           # Modelos ORM SQLAlchemy
│       ├── schemas.py          # Schemas Pydantic
│       ├── auth.py             # Geração e validação de tokens JWT
│       ├── database.py         # Conexão com banco de dados
│       ├── alembic.ini
│       ├── migrations/
│       │   └── versions/
│       │       ├── 001_initial_schema.py   # Cria todas as tabelas
│       │       └── 002_hypertable.py       # Converte readings para hypertable
│       └── scripts/
│           └── seed_tanks.py   # Seed: 8 panelas + usuário admin
├── simulator/
│   └── clp_simulator.py        # Simulador de CLP para desenvolvimento
├── frontend/
│   └── src/
│       ├── components/         # TankCard, TankGrid, AlertPanel, etc.
│       ├── hooks/              # useWebSocket, useTanks, useAlerts
│       ├── pages/              # Dashboard.tsx (tela única)
│       ├── services/           # api.ts, tanks.ts, readings.ts, alerts.ts
│       ├── types/
│       └── utils/              # getTankStatus, formatTemp
├── docker-compose.yml
├── CLAUDE.md
├── DOCUMENTACAO.md
├── FRONTEND.md
└── ROADMAP.md
```

---

## 5. Banco de Dados

### 5.1 Modelos / Tabelas

#### `users`
| Campo | Tipo | Observação |
|---|---|---|
| id | Integer PK | |
| username | String | único |
| password | String | hash bcrypt |
| role | String | `admin` \| `operador` \| `viewer` |

#### `refresh_tokens`
| Campo | Tipo | Observação |
|---|---|---|
| id | Integer PK | |
| token_jti | String | único — ID do token JWT |
| username | String | |
| role | String | |
| expires_at | DateTime | |
| revoked_at | DateTime | nullable — preenchido no logout/refresh |
| created_at | DateTime | |

#### `tanks`
| Campo | Tipo | Observação |
|---|---|---|
| id | Integer PK | |
| name | String | |
| location | String | |
| temp_min | Float | limite mínimo para alertas |
| temp_max | Float | limite máximo para alertas |
| status | String | `active` (padrão) |

#### `readings` — Hypertable TimescaleDB
| Campo | Tipo | Observação |
|---|---|---|
| id | BigInteger PK | |
| tank_id | FK → tanks | |
| temperature | Float | |
| recorded_at | DateTime | particionamento temporal |

#### `alerts`
| Campo | Tipo | Observação |
|---|---|---|
| id | Integer PK | |
| tank_id | FK → tanks | |
| temperature | Float | temperatura no momento do disparo |
| fired_at | DateTime | |
| resolved_at | DateTime | nullable |
| acknowledged_by | FK → users | nullable |

#### `yeast_profiles`
| Campo | Tipo | Observação |
|---|---|---|
| id | Integer PK | |
| name | String | único |
| strain | String | |
| attenuation_min / max | Float | % |
| temperature_min_c / max_c | Float | °C |
| notes | Text | |
| created_at / updated_at | DateTime | |

#### `batches`
| Campo | Tipo | Observação |
|---|---|---|
| id | Integer PK | |
| name | String | |
| style | String | |
| status | String | `planned` \| `active` \| `completed` \| `cancelled` |
| fermenter_id | Integer | ID da panela associada |
| original_gravity | Float | nullable |
| final_gravity | Float | nullable |
| volume_liters | Float | nullable |
| started_at / ended_at | DateTime | nullable |
| yeast_profile_id | FK → yeast_profiles | nullable |
| notes | Text | |
| created_at / updated_at | DateTime | |

#### `batch_events`
| Campo | Tipo | Observação |
|---|---|---|
| id | Integer PK | |
| batch_id | FK → batches | cascade delete |
| event_type | String | ex: pitch, dry hop, cold crash |
| description | Text | |
| value | Float | nullable |
| unit | String | nullable |
| occurred_at | DateTime | |

### 5.2 Relacionamentos

```
User (1) ──── (N) Alert (acknowledged_by)
User (1) ──── (N) RefreshToken
Tank (1) ──── (N) Reading
Tank (1) ──── (N) Alert
YeastProfile (1) ──── (N) Batch
Batch (1) ──── (N) BatchEvent  [cascade delete]
```

### 5.3 TimescaleDB

A tabela `readings` é convertida para **hypertable** particionada por `recorded_at` (migration 002). Isso permite:
- Consultas de séries temporais eficientes por período
- Compressão automática de dados históricos

---

## 6. API REST

### 6.1 Autenticação

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/register` | público | Cria usuário (role padrão: viewer) |
| POST | `/auth/login` | público | Retorna access token + refresh token |
| POST | `/auth/refresh` | público | Troca refresh token por novo par; revoga o anterior |
| POST | `/auth/logout` | público | Revoga o refresh token |

### 6.2 Health Check

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/health` | público | `{"status": "ok", "version": "0.1.0"}` |

### 6.3 Panelas (Tanks)

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/api/v1/tanks` | todos | Lista 8 panelas com temperatura atual e status |
| GET | `/api/v1/tanks/{id}/readings` | todos | Histórico por período (`?period=6h\|24h\|7d\|30d`) |
| GET | `/api/v1/tanks/{id}/status` | todos | Temperatura atual + alertas ativos |
| PATCH | `/api/v1/tanks/{id}/config` | admin | Atualiza nome, temp_min, temp_max |

### 6.4 Leituras

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/api/v1/readings` | admin, operador | Recebe leitura do CLP/simulador |

Payload:
```json
{
  "tank_id": 3,
  "temperature": 14.7,
  "recorded_at": "2025-05-15T10:30:00Z"
}
```

### 6.5 Alertas

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/api/v1/alerts` | todos | Lista alertas (filtros: `?status=active`, `?tank_id=`) |
| PATCH | `/api/v1/alerts/{id}/acknowledge` | todos | Reconhece alerta |

### 6.6 Lotes (Batches)

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/api/v1/batches` | admin, operador | Cria lote |
| GET | `/api/v1/batches` | todos | Lista com filtros (status, style, datas) |
| GET | `/api/v1/batches/{id}` | todos | Detalhe com ABV e atenuação calculados |
| PATCH | `/api/v1/batches/{id}` | admin, operador | Atualiza lote |
| PATCH | `/api/v1/batches/{id}/events` | admin, operador | Adiciona evento ao lote |
| GET | `/api/v1/batches/{id}/export` | todos | Exporta lote em CSV |

### 6.7 Perfis de Levedura

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/api/v1/yeast_profiles` | admin | Cria perfil |
| GET | `/api/v1/yeast_profiles` | todos | Lista perfis |
| GET | `/api/v1/yeast_profiles/{id}` | todos | Detalhe |
| PATCH | `/api/v1/yeast_profiles/{id}` | admin | Atualiza |
| DELETE | `/api/v1/yeast_profiles/{id}` | admin | Remove (falha se vinculado a lotes) |

### 6.8 WebSocket

| Protocolo | Rota | Descrição |
|---|---|---|
| WS | `/ws/tanks/{id}` | Stream de leituras em tempo real por panela |
| WS | `/ws/alerts` | Stream de alertas em tempo real |

Ambos exigem token JWT válido. Implementados via Redis Pub/Sub.

---

## 7. Autenticação e Autorização

### 7.1 JWT

- **Algoritmo:** HS256
- **Access token:** 15 minutos (configurável via env)
- **Refresh token:** 7 dias (configurável via env)
- **Payload:** `{sub, role, type, jti, exp}`

### 7.2 Middleware

O middleware de autenticação intercepta todas as rotas exceto as públicas (`/health`, `/docs`, `/register`, `/login`, `/auth/*`). Extrai o `Bearer token` do header, decodifica e popula `request.state.user`.

### 7.3 Controle de Acesso por Role

| Role | Permissões |
|---|---|
| `admin` | Acesso total |
| `operador` | Leitura + envio de leituras + gestão de lotes |
| `viewer` | Somente leitura |

### 7.4 Senhas

Armazenadas como hash bcrypt (12 rounds). Nunca armazenadas ou logadas em texto puro.

---

## 8. Lógica de Negócio

### 8.1 Status da Panela

```
offline  → sem leitura há 30s+
alert    → temperatura > temp_max  ou  < temp_min
warning  → temperatura dentro de 0,5°C do limite
normal   → dentro da faixa com folga
```

### 8.2 Disparo e Resolução de Alertas

A cada leitura recebida:
- Se temperatura fora da faixa → cria alerta ativo + publica no Redis
- Se temperatura dentro da faixa e há alerta ativo → resolve alerta + publica no Redis

### 8.3 Cálculo de Métricas de Fermentação

```
ABV = (OG - FG) × 131,25
Atenuação Aparente = ((OG - FG) / (OG - 1)) × 100%
```

Calculados dinamicamente na rota `GET /api/v1/batches/{id}` quando OG e FG estão presentes.

### 8.4 Fluxo de Dados em Tempo Real

```
POST /api/v1/readings
  → Salva no banco
  → Dispara/resolve alertas
  → Publica no Redis "tanks:{id}:readings"
  → WebSocket Hub transmite para clientes conectados
  → Frontend atualiza TankCard e gráfico
```

---

## 9. Simulador de CLP

Arquivo: `simulator/clp_simulator.py`

Simula 8 panelas com temperatura dinâmica usando modelo de primeira ordem:

```
temp_nova = 0,95 × temp_atual + 0,05 × setpoint + ruído(σ=0,3°C)
```

**Temperaturas de referência padrão:**

| Panela | Setpoint (°C) |
|---|---|
| 1 | 15,0 |
| 2 | 12,0 |
| 3 | 18,0 |
| 4 | 14,0 |
| 5 | 16,0 |
| 6 | 13,0 |
| 7 | 17,0 |
| 8 | 15,5 |

**Uso:**
```bash
python simulator/clp_simulator.py                          # padrão
python simulator/clp_simulator.py --fault-tank 3 --fault-temp 28.0   # falha na panela 3
python simulator/clp_simulator.py --api-url http://outro-host:8000
```

Implementa reautenticação automática (401) e backoff exponencial em erros (1s → 30s max).

---

## 10. Infraestrutura (Docker Compose)

| Serviço | Imagem | Porta | Descrição |
|---|---|---|---|
| `api` | build local (Python 3.12-slim) | 8000 | FastAPI com hot reload |
| `db` | timescale/timescaledb:latest-pg16 | 5432 | PostgreSQL + TimescaleDB |
| `redis` | redis:7-alpine | 6379 | Cache e Pub/Sub |

Volumes persistentes: `timescale_data`, `redis_data`

O serviço `api` aguarda `db` e `redis` estarem saudáveis (healthcheck) antes de iniciar.

---

## 11. Variáveis de Ambiente

| Variável | Valor padrão (dev) | Descrição |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://jeagers:jeagers@db:5432/jeagers` | Conexão com banco |
| `REDIS_URL` | `redis://redis:6379/0` | Conexão com Redis |
| `JWT_SECRET_KEY` | `dev-secret-change-me` | **Trocar em produção** |
| `JWT_ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Validade do access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Validade do refresh token |
| `VITE_API_URL` | `http://localhost:8000` | URL da API para o frontend |
| `VITE_WS_URL` | `ws://localhost:8000` | URL WebSocket para o frontend |

---

## 12. Comandos Principais

```bash
# Subir ambiente
docker compose up -d

# Popular banco (8 panelas + admin)
docker compose exec api python scripts/seed_tanks.py

# Rodar migrations
docker compose exec api alembic upgrade head

# Rodar simulador
python simulator/clp_simulator.py

# Logs
docker compose logs -f api

# Frontend
cd frontend && npm install && npm run dev   # porta 5173
```

---

## 13. Fora do Escopo (Fase 2)

- Controle ativo de temperatura (ligar/desligar aquecimento ou resfriamento)
- Múltiplas páginas/rotas além do dashboard
- App mobile nativo
- Integração com PDV ou sistema de estoque
