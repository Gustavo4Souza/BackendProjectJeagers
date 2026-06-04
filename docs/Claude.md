# CLAUDE.md — EH Brewing

Instruções para o Claude Code trabalhar neste repositório.

---

## Contexto do Projeto

Plataforma de monitoramento e controle de temperatura para 8 panelas de armazenamento de bebidas da EH Brewing. O sistema lê temperatura via CLP central (simulado durante desenvolvimento) e exibe em dashboard web em tempo real.

**Versão atual:** 0.2.0
**Fase 1 (monitoramento):** ✅ Concluído
**Fase 2 (controle ativo):** 🔲 Em desenvolvimento
**Ambiente:** local via Docker Compose — sem deploy em produção por ora

---

## O que já está pronto

- Backend FastAPI completo: leituras, panelas, alertas, autenticação JWT
- WebSocket tempo real (leituras e alertas) via Redis Pub/Sub
- Simulador de CLP em Python (8 panelas, ruído gaussiano, injeção de falhas)
- Frontend — tela **Painel**: 8 cards, gráfico histórico, painel de alertas, modal de configuração
- Autenticação frontend com JWT, interceptors Axios, refresh token

## O que está pendente

- **Controle de temperatura** (Fase 2): setpoint por panela, modo cooling/heating/idle, ETA
- **Telas do TopBar:** Histórico, Alertas, Config
- **Lotes e Leveduras:** batches, yeast_profiles, batch_events, frontend completo
- **Simulador:** resposta ao setpoint de controle

---

## Estrutura do Repositório

```
eh-brewing/
├── backend/
│   ├── api/
│   │   ├── main.py             # Rotas FastAPI + WebSocket
│   │   ├── models.py           # Modelos SQLAlchemy
│   │   ├── schemas.py          # Schemas Pydantic
│   │   ├── auth.py             # JWT
│   │   ├── database.py         # Conexão DB
│   │   ├── migrations/versions/
│   │   └── scripts/seed_tanks.py
│   └── Dockerfile
├── simulator/
│   └── clp_simulator.py
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── layout/         # TopBar, AlertBadge
│       │   ├── tanks/          # TankGrid, TankCard, TempBar, TankConfigModal
│       │   ├── chart/          # TankHistoryChart, MultiTankHistoryChart
│       │   ├── alerts/         # AlertPanel
│       │   ├── control/        # ETADisplay (Fase 2)
│       │   └── batches/        # BatchCard, BatchDetailModal
│       ├── hooks/
│       ├── pages/              # Dashboard, HistoricoPage, AlertasPage, ConfigPage, BatchesPage
│       ├── services/           # api.ts, tanks.ts, readings.ts, alerts.ts, control.ts, batches.ts
│       ├── types/index.ts
│       └── utils/
├── docker-compose.yml
├── DOCUMENTACAO.md
├── ET.md
├── FRONTEND.md
├── ROADMAP.md
└── CLAUDE.md
```

---

## Backend

### Stack
- Python 3.12 + FastAPI (async)
- SQLAlchemy 2.x (async) + Alembic para migrations
- PostgreSQL + TimescaleDB (hypertable `readings`)
- Redis para Pub/Sub
- Pydantic v2

### Convenções
- Lógica de negócio em `services/` — rotas finas
- Schemas Pydantic separados dos modelos ORM
- `async/await` em toda a aplicação
- Variáveis de ambiente via `pydantic-settings` — nunca hardcodar secrets
- Migrations sempre via Alembic

### Endpoints principais

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/v1/readings` | Recebe leitura do CLP/simulador |
| GET | `/api/v1/tanks` | Lista panelas com temperatura atual |
| GET | `/api/v1/tanks/{id}/readings` | Histórico `?period=6h\|24h\|7d\|30d` |
| GET | `/api/v1/tanks/{id}/status` | Temperatura atual + alertas ativos |
| PATCH | `/api/v1/tanks/{id}/config` | Atualiza nome, temp_min, temp_max |
| GET | `/api/v1/tanks/{id}/control` | Retorna setpoint e mode (Fase 2) |
| POST | `/api/v1/tanks/{id}/control` | Define setpoint (Fase 2) |
| GET | `/api/v1/tanks/{id}/eta` | ETA para atingir setpoint (Fase 2) |
| GET | `/api/v1/alerts` | Lista alertas |
| PATCH | `/api/v1/alerts/{id}/acknowledge` | Reconhece alerta |
| POST | `/api/v1/alerts/acknowledge-all` | Reconhece todos |
| GET | `/api/v1/users` | Lista usuários (admin) |
| POST | `/api/v1/users` | Cria usuário (admin) |
| POST | `/api/v1/batches` | Cria lote |
| GET | `/api/v1/batches` | Lista lotes |
| GET | `/api/v1/batches/{id}` | Detalhe + ABV |
| POST | `/api/v1/yeast_profiles` | Cria perfil de levedura |
| GET | `/api/v1/yeast_profiles` | Lista perfis |
| WS | `/ws/tanks/{id}` | Stream de leituras |
| WS | `/ws/alerts` | Stream de alertas |
| WS | `/ws/control` | Stream de mudanças de controle (Fase 2) |

### Payload de leitura

```json
POST /api/v1/readings
{ "tank_id": 3, "temperature": 14.7, "recorded_at": "2025-05-15T10:30:00Z" }
```

### Payload de controle

```json
POST /api/v1/tanks/{id}/control
{ "setpoint": 8.0 }
```

### Lógica de controle

```
setpoint < temp_atual  →  mode = "cooling"
setpoint > temp_atual  →  mode = "heating"
setpoint ≈ temp_atual (±0.3°C)  →  mode = "idle"
```

### Cálculo de ETA

```python
# Taxa média de variação nas últimas 6h
taxa = mean([r[i].temp - r[i-1].temp for i in range(1, n)]) * (60 / intervalo_s)
eta_minutes = abs(temp_atual - setpoint) / abs(taxa)
# Mínimo de 10 leituras para retornar sufficient_data: true
```

### Comandos úteis

```bash
docker compose up -d
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_tanks.py
docker compose exec api pytest --cov=app --cov-report=term-missing
docker compose exec api ruff check api/
docker compose exec api ruff format api/
```

---

## Frontend

### Stack
- React 18 + Vite + TypeScript
- Tailwind CSS
- Recharts
- React Query
- Axios
- React Router v6
- Sem biblioteca de estado global

### Roteamento

```
/            → Dashboard (Painel)
/historico   → HistoricoPage
/alertas     → AlertasPage
/config      → ConfigPage
/lotes       → BatchesPage
```

### Estado do Dashboard
```typescript
const [selectedTankId, setSelectedTankId] = useState<number>(1)
const [configModalTankId, setConfigModalTankId] = useState<number | null>(null)
```

### Fluxo de dados em tempo real

```
WebSocket /ws/tanks/{1..8}  →  useWebSocket  →  queryClient.setQueryData(['tanks'])
WebSocket /ws/alerts         →  useAlerts    →  queryClient.invalidateQueries(['alerts'])
WebSocket /ws/control        →  useTankControl → queryClient.setQueryData(['control', id])
```

### Status de temperatura

```typescript
type TankStatus = 'normal' | 'warning' | 'alert' | 'offline'
// offline   → sem leitura há 30s+
// alert     → acima de temp_max ou abaixo de temp_min
// warning   → dentro de 0.5°C do limite
// normal    → dentro da faixa com folga
```

### Cores

| Status | Dot | Borda | Temperatura | Pill |
|---|---|---|---|---|
| normal | #1D9E75 | padrão | padrão | verde |
| warning | #EF9F27 | #EF9F27 | #BA7517 | amarelo |
| alert | #D85A30 | #D85A30 | #D85A30 | vermelho |
| offline | cinza | padrão | "—" | cinza |

### Comandos úteis

```bash
cd frontend && npm install
npm run dev       # porta 5173
npm run build
npm run lint
```

---

## Simulador de CLP

```bash
# Modo básico
python simulator/clp_simulator.py

# Injetar falha na panela 3
python simulator/clp_simulator.py --fault-tank 3 --fault-temp 28.0

# Com parâmetros de controle (Fase 2)
python simulator/clp_simulator.py --cooling-rate 0.4 --heating-rate 0.25

# Configurar endpoint
python simulator/clp_simulator.py --api-url http://localhost:8000 --interval 5
```

### Comportamento de controle (Fase 2)

O simulador consulta `GET /api/v1/tanks/{id}/control` a cada ciclo:
- `mode = idle` → deriva natural (comportamento atual)
- `mode = cooling` → temperatura converge para setpoint com taxa `--cooling-rate`
- `mode = heating` → temperatura sobe em direção ao setpoint com taxa `--heating-rate`
- Temperatura ≈ setpoint (±0.3°C) → ruído mínimo, modo estabilizado

---

## Docker Compose

```bash
docker compose up -d           # sobe tudo
docker compose logs -f api     # logs do backend
docker compose down            # para tudo
docker compose up -d --build   # rebuild após mudanças no Dockerfile
```

Serviços: `api` (8000) · `db` (5432) · `redis` (6379)

---

## Regras — O que NUNCA fazer

### Backend
- Nunca commitar `.env` ou arquivos com secrets
- Nunca usar `CREATE TABLE` manual — sempre Alembic
- Nunca fazer lógica de negócio dentro das rotas FastAPI
- Nunca bloquear o event loop com código síncrono
- Nunca alterar a tabela `readings` fora de uma migration

### Frontend
- Nunca usar `any` no TypeScript
- Nunca fazer `fetch` diretamente nos componentes — sempre via services
- Nunca duplicar lógica de status — usar `getTankStatus` de `utils/`
- Nunca hardcodar cores — usar as constantes de `getTankStatus`
- Nunca criar rotas de página fora do React Router (`/historico`, `/alertas`, `/config`, `/lotes`)

---

## Fora do Escopo Atual

- Deploy em produção — avaliar após aprovação do cliente
- Controle PID — sistema usa relé ON/OFF simples
- App mobile nativo
- Integração com PDV ou sistema de estoque

---

## Configuração de Ambiente

Copiar `.env.example` para `.env`:

```env
DATABASE_URL=postgresql+psycopg2://jeagers:jeagers@db:5432/jeagers
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=gerar-com-openssl-rand-hex-32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

---

## Referências

- Documentação técnica completa: `DOCUMENTACAO.md`
- Roadmap de desenvolvimento: `ROADMAP.md`
- Especificação de frontend: `FRONTEND.md`
- Especificação técnica detalhada: `ET.md`
- Controlador nas panelas: [Novus N321](https://www.pidbrasil.com.br/controlador-de-temperatura-n321-ntc.html)
