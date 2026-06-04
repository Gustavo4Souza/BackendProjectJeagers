# Especificação Técnica — EH Brewing

**Projeto:** Plataforma de monitoramento e controle de temperatura para panelas de armazenamento
**Versão:** 0.2.0
**Fase atual:** Fase 1 concluída (monitoramento) · Fase 2 em desenvolvimento (controle ativo)
**Data:** 2026-06-01
**Ambiente:** Desenvolvimento local via Docker Compose — apresentação ao cliente em ambiente local

---

## 1. Visão Geral

Sistema web para monitoramento e controle em tempo real da temperatura de 8 panelas de armazenamento de bebidas da EH Brewing. Leituras chegam via CLP (simulado em desenvolvimento) e são exibidas em dashboard com alertas automáticos. Na Fase 2, o usuário poderá definir setpoints de temperatura por panela e o sistema aciona o equipamento (aquecimento ou resfriamento) via relé ON/OFF.

---

## 2. Arquitetura Geral

```
CLP / Simulador
      ↓  POST /api/v1/readings
      ↑  GET  /api/v1/tanks/{id}/control   (simulador consulta setpoint)
   FastAPI (Backend)
      ↓  INSERT → PostgreSQL / TimescaleDB
      ↓  PUBLISH → Redis Pub/Sub
   WebSocket Hub
      ↓  ws://
   Frontend React (Dashboard — 4 telas)
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
| Roteamento | React Router v6 |
| Conteinerização | Docker + Docker Compose |

---

## 4. Estrutura de Arquivos

```
eh-brewing/
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
│       │       ├── 001_initial_schema.py
│       │       ├── 002_hypertable.py
│       │       └── 003_tank_control.py   # Fase 2
│       └── scripts/
│           └── seed_tanks.py
├── simulator/
│   └── clp_simulator.py
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── layout/         # TopBar, AlertBadge
│       │   ├── tanks/          # TankCard, TankGrid, TempBar, TankConfigModal
│       │   ├── chart/          # TankHistoryChart, MultiTankHistoryChart
│       │   ├── alerts/         # AlertPanel, AlertsPage
│       │   ├── batches/        # BatchCard, BatchDetailModal
│       │   └── control/        # ETADisplay (Fase 2)
│       ├── hooks/
│       ├── pages/              # Dashboard, HistoricoPage, AlertasPage, ConfigPage, BatchesPage
│       ├── services/           # api.ts, tanks.ts, readings.ts, alerts.ts, control.ts, batches.ts
│       ├── types/
│       └── utils/
├── docker-compose.yml
├── CLAUDE.md
├── DOCUMENTACAO.md
├── ET.md
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
| token_jti | String | único |
| username | String | |
| role | String | |
| expires_at | DateTime | |
| revoked_at | DateTime | nullable |
| created_at | DateTime | |

#### `tanks`
| Campo | Tipo | Observação |
|---|---|---|
| id | Integer PK | |
| name | String | nome da bebida — ex: "Pilsen Lager" |
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
| temperature | Float | temperatura no disparo |
| fired_at | DateTime | |
| resolved_at | DateTime | nullable |
| acknowledged_by | FK → users | nullable |

#### `tank_control` — Fase 2
| Campo | Tipo | Observação |
|---|---|---|
| id | Integer PK | |
| tank_id | FK → tanks | único por panela |
| setpoint | Float | temperatura alvo (°C) |
| mode | String | `cooling` \| `heating` \| `idle` |
| updated_at | DateTime | |
| updated_by | FK → users | nullable |

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
| event_type | String | pitch, dry hop, cold crash, etc. |
| description | Text | |
| value | Float | nullable |
| unit | String | nullable |
| occurred_at | DateTime | |

### 5.2 Relacionamentos

```
User (1) ──── (N) Alert (acknowledged_by)
User (1) ──── (N) RefreshToken
User (1) ──── (N) TankControl (updated_by)
Tank (1) ──── (N) Reading
Tank (1) ──── (N) Alert
Tank (1) ──── (1) TankControl
YeastProfile (1) ──── (N) Batch
Batch (1) ──── (N) BatchEvent  [cascade delete]
```

### 5.3 TimescaleDB

A tabela `readings` é hypertable particionada por `recorded_at`. Permite consultas de séries temporais eficientes e compressão de dados históricos.

---

## 6. API REST

### 6.1 Autenticação

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/register` | público | Cria usuário (role padrão: viewer) |
| POST | `/auth/login` | público | Retorna access token + refresh token |
| POST | `/auth/refresh` | público | Rotaciona refresh token |
| POST | `/auth/logout` | público | Revoga refresh token |

### 6.2 Health Check

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/health` | público | `{"status": "ok", "version": "0.2.0"}` |

### 6.3 Panelas

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/api/v1/tanks` | todos | Lista 8 panelas com temperatura e status |
| GET | `/api/v1/tanks/{id}/readings` | todos | Histórico por período |
| GET | `/api/v1/tanks/{id}/readings/export` | todos | Exportar CSV |
| GET | `/api/v1/tanks/{id}/status` | todos | Temperatura atual + alertas ativos |
| PATCH | `/api/v1/tanks/{id}/config` | admin | Atualiza nome, temp_min, temp_max |

### 6.4 Leituras

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/api/v1/readings` | admin, operador | Recebe leitura do CLP/simulador |

### 6.5 Controle de Temperatura — Fase 2

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/api/v1/tanks/{id}/control` | todos | Retorna setpoint e modo atual |
| POST | `/api/v1/tanks/{id}/control` | admin, operador | Define setpoint (determina modo automaticamente) |
| GET | `/api/v1/tanks/{id}/eta` | todos | Estimativa de tempo para atingir setpoint |

**Payload POST /control:**
```json
{ "setpoint": 8.0 }
```

**Resposta GET /eta:**
```json
{
  "eta_minutes": 47,
  "rate_per_minute": -0.25,
  "current_temp": 14.2,
  "setpoint": 2.0,
  "sufficient_data": true
}
```

**Cálculo de ETA:** média da taxa de variação °C/min nas últimas 6h de leituras × distância ao setpoint. Retorna `sufficient_data: false` se houver menos de 10 leituras históricas.

### 6.6 Alertas

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/api/v1/alerts` | todos | Lista alertas com filtros |
| PATCH | `/api/v1/alerts/{id}/acknowledge` | todos | Reconhece alerta |
| POST | `/api/v1/alerts/acknowledge-all` | todos | Reconhece todos os ativos |

### 6.7 Usuários

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/api/v1/users` | admin | Lista usuários |
| POST | `/api/v1/users` | admin | Cria usuário |
| PATCH | `/api/v1/users/{id}` | admin | Atualiza role ou status |

### 6.8 Lotes

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/api/v1/batches` | admin, operador | Cria lote |
| GET | `/api/v1/batches` | todos | Lista com filtros |
| GET | `/api/v1/batches/{id}` | todos | Detalhe com ABV e atenuação |
| PATCH | `/api/v1/batches/{id}` | admin, operador | Atualiza |
| PATCH | `/api/v1/batches/{id}/events` | admin, operador | Adiciona evento |
| GET | `/api/v1/batches/{id}/export` | todos | Exporta CSV |

### 6.9 Perfis de Levedura

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/api/v1/yeast_profiles` | admin | Cria perfil |
| GET | `/api/v1/yeast_profiles` | todos | Lista |
| GET | `/api/v1/yeast_profiles/{id}` | todos | Detalhe |
| PATCH | `/api/v1/yeast_profiles/{id}` | admin | Atualiza |
| DELETE | `/api/v1/yeast_profiles/{id}` | admin | Remove (falha se vinculado a lote ativo) |

### 6.10 WebSocket

| Protocolo | Rota | Descrição |
|---|---|---|
| WS | `/ws/tanks/{id}` | Stream de leituras por panela |
| WS | `/ws/alerts` | Stream de alertas |
| WS | `/ws/control` | Stream de mudanças de setpoint (Fase 2) |

Todos exigem token JWT válido. Implementados via Redis Pub/Sub.

---

## 7. Autenticação e Autorização

### 7.1 JWT

- **Algoritmo:** HS256
- **Access token:** 15 minutos
- **Refresh token:** 7 dias com rotação

### 7.2 Controle de Acesso por Role

| Role | Permissões |
|---|---|
| `admin` | Acesso total, gestão de usuários, configuração de panelas |
| `operador` | Leitura + envio de leituras + controle de setpoint + gestão de lotes |
| `viewer` | Somente leitura |

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
- Temperatura fora da faixa → cria alerta ativo + publica no Redis
- Temperatura dentro da faixa + alerta ativo → resolve alerta + publica no Redis

### 8.3 Lógica de Controle (Fase 2) — Relé ON/OFF

Quando o usuário define um setpoint via `POST /api/v1/tanks/{id}/control`:

```
setpoint < temp_atual  →  mode = "cooling"  (acionar resfriamento)
setpoint > temp_atual  →  mode = "heating"  (acionar aquecimento)
setpoint = temp_atual  →  mode = "idle"     (sem ação)
```

O modo é recalculado automaticamente a cada leitura recebida: quando a temperatura atinge o setpoint (±0,3°C tolerância), o modo muda para `idle`.

### 8.4 Cálculo de ETA

```python
# Pega as últimas 6h de leituras
leituras = últimas 6h de readings para a panela
# Calcula taxa média de variação
deltas = [leituras[i].temperature - leituras[i-1].temperature for i em range(1, len(leituras))]
taxa_por_leitura = mean(deltas)  # °C por ciclo de leitura (5s)
taxa_por_minuto = taxa_por_leitura * (60 / intervalo_simulador)
# Distância ao setpoint
distancia = abs(temp_atual - setpoint)
# ETA
eta_minutes = distancia / abs(taxa_por_minuto)  se taxa != 0
```

Retorna `sufficient_data: false` se houver menos de 10 leituras no período.

### 8.5 Métricas de Fermentação

```
ABV = (OG - FG) × 131,25
Atenuação Aparente = ((OG - FG) / (OG - 1)) × 100%
```

Calculados dinamicamente em `GET /api/v1/batches/{id}` quando OG e FG estão presentes.

---

## 9. Simulador de CLP

Arquivo: `simulator/clp_simulator.py`

### Modelo de temperatura

```
temp_nova = 0,95 × temp_atual + 0,05 × setpoint_efetivo + ruído(σ=0,3°C)
```

- **Modo idle (padrão):** `setpoint_efetivo` = setpoint original da panela (deriva natural)
- **Modo cooling:** `setpoint_efetivo` = setpoint definido pelo usuário; taxa de aproximação acelerada via parâmetro `--cooling-rate` (padrão 0.3°C/ciclo adicional)
- **Modo heating:** idem com `--heating-rate` (padrão 0.2°C/ciclo adicional)
- **Estabilizado (±0,3°C do setpoint):** ruído mínimo (σ=0,05°C)

### Ciclo do simulador

```
1. Para cada panela:
   a. GET /api/v1/tanks/{id}/control  → obtém setpoint e mode
   b. Calcula nova temperatura conforme modelo
   c. POST /api/v1/readings
2. Aguarda intervalo (padrão 5s)
3. Repete
```

### Setpoints padrão

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

### Parâmetros CLI

```bash
python simulator/clp_simulator.py                              # padrão
python simulator/clp_simulator.py --fault-tank 3 --fault-temp 28.0
python simulator/clp_simulator.py --api-url http://outro-host:8000
python simulator/clp_simulator.py --cooling-rate 0.5          # resfriamento mais agressivo
python simulator/clp_simulator.py --heating-rate 0.3
python simulator/clp_simulator.py --interval 10               # ciclo de 10s
```

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
| `DATABASE_URL` | `postgresql+psycopg2://jeagers:jeagers@db:5432/jeagers` | Banco |
| `REDIS_URL` | `redis://redis:6379/0` | Redis |
| `JWT_SECRET_KEY` | `dev-secret-change-me` | **Trocar em produção** |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | |
| `VITE_API_URL` | `http://localhost:8000` | URL da API para o frontend |
| `VITE_WS_URL` | `ws://localhost:8000` | WebSocket para o frontend |

---

## 12. Comandos Principais

```bash
# Subir ambiente
docker compose up -d

# Popular banco (8 panelas + admin + controles padrão)
docker compose exec api python scripts/seed_tanks.py

# Rodar migrations
docker compose exec api alembic upgrade head

# Rodar simulador (modo básico)
python simulator/clp_simulator.py

# Rodar simulador com controle ativo
python simulator/clp_simulator.py --cooling-rate 0.4 --heating-rate 0.25

# Logs
docker compose logs -f api

# Frontend
cd frontend && npm install && npm run dev   # porta 5173
```

---

## 13. Fora do Escopo Atual

- Deploy em produção — avaliar após apresentação ao cliente
- Controle PID (sistema usa relé ON/OFF simples)
- App mobile nativo
- Integração com PDV ou sistema de estoque
