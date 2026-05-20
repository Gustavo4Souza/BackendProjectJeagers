# CLAUDE.md — EH Brewing

Instruções para o Claude Code trabalhar neste repositório.

---

## Contexto do Projeto

Plataforma de monitoramento de temperatura para 8 panelas de armazenamento de bebidas da EH Brewing. O sistema lê temperatura via CLP central (simulado durante desenvolvimento) e exibe em dashboard web em tempo real.

**Fase atual:** Fase 1 — Monitoramento (sem controle ativo de temperatura)

---

## Estrutura do Repositório

```
eh-brewing/
├── backend/
│   ├── app/
│   │   ├── api/          # Rotas FastAPI
│   │   ├── models/       # Modelos SQLAlchemy
│   │   ├── schemas/      # Schemas Pydantic
│   │   ├── services/     # Lógica de negócio
│   │   └── websocket/    # Handlers WebSocket
│   ├── migrations/       # Alembic migrations
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── layout/   # TopBar, AlertBadge
│       │   ├── tanks/    # TankGrid, TankCard, TempBar, TankConfigModal
│       │   ├── chart/    # TankHistoryChart
│       │   └── alerts/   # AlertPanel
│       ├── hooks/        # useTanks, useTankReadings, useWebSocket, useAlerts
│       ├── pages/        # Dashboard.tsx (tela única)
│       ├── services/     # api.ts, tanks.ts, readings.ts, alerts.ts
│       ├── types/        # index.ts
│       └── utils/        # formatTemp, getTankStatus, formatDateTime
├── simulator/
│   └── clp_simulator.py
├── docker-compose.yml
├── DOCUMENTACAO.md
├── ROADMAP.md
├── FRONTEND.md
└── CLAUDE.md
```

---

## Backend

### Stack
- Python 3.11 + FastAPI (async)
- SQLAlchemy 2.x (async) + Alembic para migrations
- PostgreSQL + TimescaleDB (hypertable `readings`)
- Redis para Pub/Sub
- Pydantic v2 para validação

### Convenções

- Toda lógica de negócio fica em `backend/app/services/` — as rotas são finas
- Schemas Pydantic ficam em `backend/app/schemas/` — separados dos modelos ORM
- Usar `async/await` em toda a aplicação — sem código síncrono bloqueante
- Variáveis de ambiente via `pydantic-settings` — nunca hardcodar secrets
- Migrations sempre via Alembic — nunca `CREATE TABLE` manual em produção

### Endpoints definidos

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/readings` | Recebe leitura do CLP/simulador |
| `GET` | `/api/v1/tanks` | Lista 8 panelas com `current_temperature` e `last_reading_at` |
| `GET` | `/api/v1/tanks/{id}/readings` | Histórico com `?period=6h\|24h\|7d\|30d` |
| `GET` | `/api/v1/tanks/{id}/status` | Temperatura atual + alertas ativos |
| `PATCH` | `/api/v1/tanks/{id}/config` | Atualiza `name`, `temp_min`, `temp_max` |
| `GET` | `/api/v1/alerts` | Lista alertas com `?status=active` |
| `PATCH` | `/api/v1/alerts/{id}/acknowledge` | Reconhece alerta |
| `POST` | `/api/v1/auth/login` | Login JWT |
| `POST` | `/api/v1/auth/refresh` | Refresh token |
| `WS` | `/ws/tanks/{id}` | Stream de leituras em tempo real |

### Payload de leitura (CLP/simulador → API)

```json
POST /api/v1/readings
{
  "tank_id": 3,
  "temperature": 14.7,
  "recorded_at": "2025-05-15T10:30:00Z"
}
```

### Comandos úteis

```bash
docker compose up -d
docker compose exec backend alembic revision --autogenerate -m "descricao"
docker compose exec backend alembic upgrade head
docker compose exec backend pytest --cov=app --cov-report=term-missing
docker compose exec backend ruff check app/
docker compose exec backend ruff format app/
```

---

## Frontend

### Stack
- React 18 + Vite + TypeScript
- Tailwind CSS (sem CSS customizado — apenas utilitários)
- Recharts para gráfico de série temporal
- React Query para estado de servidor
- Axios para HTTP
- **Sem biblioteca de estado global** — estado local + React Query é suficiente

### Arquitetura de tela

**Uma única tela principal (`Dashboard.tsx`).** Não há roteamento entre páginas para o fluxo principal.

Estado do Dashboard:
```typescript
const [selectedTankId, setSelectedTankId] = useState<number>(1)
const [configModalTankId, setConfigModalTankId] = useState<number | null>(null)
```

### Fluxo de dados

```
WebSocket /ws/tanks/{1..8}  (8 conexões simultâneas)
    ↓ nova leitura
useWebSocket → queryClient.setQueryData(['tanks'])
    ↓
TankCard re-renderiza com temperatura atualizada
    ↓ se tank === selectedTankId
TankHistoryChart atualiza gráfico
```

### Comportamentos críticos

- **Card selecionado:** clicar em qualquer área do card (exceto engrenagem) define `selectedTankId` e atualiza o gráfico
- **Gráfico:** recarrega via React Query quando `selectedTankId` ou período muda
- **Offline:** panela sem leitura há mais de 30s → dot cinza, temperatura "—", pill "Offline"
- **Modal:** engrenagem → abre `TankConfigModal` com campos de nome e faixa de temperatura
- **Controle (Fase 2):** seção presente no modal, `disabled` + opacidade 0.4 + badge "em breve"
- **Reconexão WebSocket:** backoff exponencial — 1s, 2s, 4s, máximo 30s

### Status de temperatura

```typescript
// utils/getTankStatus.ts
type TankStatus = 'normal' | 'warning' | 'alert' | 'offline'

// offline   → sem leitura há 30s+
// alert     → acima de temp_max ou abaixo de temp_min
// warning   → dentro de 0.5°C do limite (acima ou abaixo)
// normal    → dentro da faixa com folga
```

### Cores

| Status | Dot | Borda card | Temperatura | Pill |
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

### Referência completa de componentes

Ver `FRONTEND.md` para especificação detalhada de cada componente, props, hooks e services.

---

## Simulador de CLP

```bash
python simulator/clp_simulator.py                          # padrão: 8 panelas, 5s
python simulator/clp_simulator.py --fault-tank 3 --fault-temp 28.0
python simulator/clp_simulator.py --api-url https://eh-brewing-api.railway.app
```

Rodar o simulador é obrigatório para ver dados no dashboard durante desenvolvimento.

---

## Docker Compose

```bash
docker compose up -d           # sobe tudo
docker compose logs -f backend # logs do backend
docker compose down            # para tudo
docker compose up -d --build   # rebuild após mudanças no Dockerfile
```

Serviços: `backend` (8000) · `db` (5432) · `redis` (6379) · `frontend` (5173)

---

## Regras — O que NUNCA fazer

### Backend
- Nunca commitar `.env` ou qualquer arquivo com secrets
- Nunca usar `CREATE TABLE` manual — sempre Alembic
- Nunca fazer lógica de negócio dentro das rotas FastAPI
- Nunca bloquear o event loop com código síncrono
- Nunca alterar a tabela `readings` fora de uma migration — é hypertable TimescaleDB

### Frontend
- Nunca usar `any` no TypeScript
- Nunca fazer `fetch` diretamente nos componentes — sempre via services
- Nunca duplicar lógica de status — usar `getTankStatus` de `utils/`
- Nunca hardcodar cores — usar as constantes definidas em `getTankStatus`
- Nunca habilitar a seção de controle de temperatura no modal — é Fase 2

---

## Fora do escopo — não implementar

- Controle ativo de temperatura (ligar/desligar aquecimento ou resfriamento)
- Múltiplas páginas/rotas além do Painel
- App mobile nativo
- Integração com PDV ou sistema de vendas
- Controle de estoque de insumos

---

## Configuração de Ambiente

Copiar `.env.example` para `.env`:

```env
# Backend
DATABASE_URL=postgresql+asyncpg://eh_user:eh_pass@db:5432/eh_brewing
REDIS_URL=redis://redis:6379
SECRET_KEY=gerar-com-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Frontend
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# Simulador
SIMULATOR_API_URL=http://localhost:8000
SIMULATOR_INTERVAL_SECONDS=5
```

---

## Referências

- Documentação técnica completa: `DOCUMENTACAO.md`
- Roadmap de desenvolvimento: `ROADMAP.md`
- Especificação de frontend: `FRONTEND.md`
- Controlador nas panelas: [Novus N321](https://www.pidbrasil.com.br/controlador-de-temperatura-n321-ntc.html)