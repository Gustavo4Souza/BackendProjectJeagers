---
marp: true
theme: default
paginate: true
style: |
  section {
    font-family: 'Segoe UI', sans-serif;
    background: #0f172a;
    color: #e2e8f0;
  }
  h1 { color: #1D9E75; font-size: 2rem; }
  h2 { color: #1D9E75; border-bottom: 2px solid #1D9E75; padding-bottom: 8px; }
  h3 { color: #94a3b8; }
  code { background: #1e293b; padding: 2px 6px; border-radius: 4px; }
  pre { background: #1e293b; border-left: 4px solid #1D9E75; }
  table { width: 100%; }
  th { background: #1e293b; color: #1D9E75; }
  td { border-bottom: 1px solid #334155; }
  .green { color: #1D9E75; }
  .yellow { color: #EF9F27; }
  .red { color: #D85A30; }
  .badge {
    display: inline-block;
    background: #1D9E75;
    color: #0f172a;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: bold;
  }
---

<!-- Slide 1 — Capa -->

# EH Brewing
## Plataforma de Monitoramento de Temperatura

<br>

> Monitoramento IoT em tempo real das 8 panelas de fermentação

<br>

**Projeto Integrador · 7°/8° Período · 2025**
Gustavo Souza

---

<!-- Slide 2 — Contexto e Problema -->

## O Problema

A EH Brewing opera **8 panelas de armazenamento** com controle de temperatura individual via controladores **Novus N321-NTC**.

<br>

| Situação Atual | Impacto |
|---|---|
| Controle local — sem integração | Sem visibilidade centralizada |
| Sem histórico de temperatura | Sem rastreabilidade de processo |
| Monitoramento manual | Risco de produto fora de especificação |
| Alerta depende de operador no local | Resposta lenta a desvios |

<br>

> **Objetivo:** entregar visibilidade remota, histórico e alertas automáticos — sem interferir no N321 existente.

---

<!-- Slide 3 — Solução -->

## A Solução

```
[Panelas 1–8]  →  [Sensor NTC paralelo]  →  [CLP Central]
                                                  ↓
                                         HTTP POST a cada 5s
                                                  ↓
                                     [Backend FastAPI + TimescaleDB]
                                          ↓              ↓
                                    [Redis Pub/Sub]   [PostgreSQL]
                                          ↓
                                   [WebSocket]
                                          ↓
                                 [Dashboard React]
                              (cards · gráfico · alertas)
```

- **Fase 1 (atual):** monitoramento e alertas — leitura, histórico, dashboard
- **Fase 2 (roadmap):** controle ativo via CLP — ligar/desligar aquecimento

---

<!-- Slide 4 — Arquitetura Técnica -->

## Arquitetura Técnica

| Camada | Tecnologia | Motivo |
|---|---|---|
| Backend | Python 3.11 + **FastAPI** | Async nativo, WebSocket, OpenAPI automático |
| Banco | **PostgreSQL + TimescaleDB** | Queries de série temporal 10–100× mais rápidas |
| Cache | **Redis** Pub/Sub | Distribui leituras entre workers sem polling |
| Frontend | **React 19** + Vite + TypeScript | Componentização, tipagem, reatividade |
| Gráficos | **Recharts** | Série temporal nativa em React |
| Auth | **JWT** + roles + refresh revogável | Controle de acesso granular |
| Deploy | **Railway** + **Vercel** | HTTPS automático, zero config |
| CI/CD | **GitHub Actions** | Lint → test → build → deploy |

---

<!-- Slide 5 — Dashboard (Demo) -->

## Dashboard — Tela Principal

```
┌─────────────────────────── TopBar ─ EH Brewing ── 🔔 2 ─ Admin ──┐
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ Panela 1 │ │ Panela 2 │ │ Panela 3 │ │ Panela 4 │              │
│  │ Pilsen   │ │ IPA      │ │ Weiss    │ │ Stout    │              │
│  │ 14.2°C 🟢│ │ 12.8°C 🟢│ │ 28.1°C 🔴│ │ 15.0°C 🟢│              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ Panela 5 │ │ Panela 6 │ │ Panela 7 │ │ Panela 8 │              │
│  │ 13.5°C 🟢│ │ 14.9°C 🟡│ │  ——  ⬜  │ │ 11.2°C 🟢│              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
│                                                                     │
│  ┌──── Gráfico Panela 3 · Weiss ── [6h 24h 7d 30d] ────────────┐  │
│  │  ━━━ temperatura ── ╌╌╌ min ── ╌╌╌ max                       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                          │  ⚠ Alertas Ativos                      │
└─────────────────────────── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

> Temperatura atualizada em **tempo real** via WebSocket — 8 conexões simultâneas

---

<!-- Slide 6 — Fluxo de uma Leitura -->

## Fluxo de uma Leitura (5 segundos)

```
1.  CLP (ou simulador) lê temperatura de cada panela
         ↓
2.  POST /api/v1/readings  { tank_id: 3, temperature: 28.1 }
         ↓
3.  FastAPI valida (Pydantic v2) → persiste no TimescaleDB
         ↓
4.  Publica no canal Redis  tanks:3:readings
         ↓
5.  Motor de alertas verifica faixa configurada
    └→ temperatura > temp_max?  →  dispara Alert, persiste
         ↓
6.  WebSocket subscriber faz broadcast ao React
         ↓
7.  TankCard re-renderiza  |  AlertPanel exibe badge 🔴
         ↓
8.  Operador reconhece alerta → PATCH /api/v1/alerts/{id}/acknowledge
```

---

<!-- Slide 7 — Autenticação -->

## Autenticação

**Roles:** `admin` · `operator` · `viewer`

| Ação | viewer | operator | admin |
|---|:---:|:---:|:---:|
| Ver temperaturas e alertas | ✅ | ✅ | ✅ |
| Enviar leituras / criar lotes | — | ✅ | ✅ |
| Configurar panelas / usuários | — | — | ✅ |

<br>

**Tokens JWT com revogação por JTI:**
```
POST /auth/login   →  { access_token, refresh_token }
POST /auth/refresh →  rotação do refresh token
POST /auth/logout  →  revoga JTI no banco
```

> Refresh tokens são armazenados com hash — compromisso do token não expõe credenciais.

---

<!-- Slide 8 — Qualidade -->

## Qualidade

### Testes (pytest + pytest-cov)

| Módulo | Cobertura |
|---|---|
| auth.py | **100%** |
| database.py | **100%** |
| models.py | **100%** |
| schemas.py | **100%** |
| main.py | 81% |
| **Total** | **86%** |

132 testes · 44s de execução · SQLite em memória (sem PostgreSQL no CI)

### Lint
- **Ruff** (Python): zero erros
- **ESLint + TypeScript**: zero erros

### Carga
- **k6**: 8 conexões WebSocket simultâneas estáveis por 30s

---

<!-- Slide 9 — CI/CD -->

## Pipeline CI/CD

```
push / PR para main
│
├── 🐍 lint-backend   (Ruff)
├── 🟦 lint-frontend  (ESLint)
├── 🧪 test-backend   (pytest ≥ 60% cobertura)
└── 🏗  build-frontend (Vite)
         │
         └── apenas push para main
                  │
                  ├── 🚂 deploy-backend  → Railway
                  │        (entrypoint: alembic upgrade head + uvicorn)
                  └── ▲  deploy-frontend → Vercel
                             (dist prebuilt, HTTPS automático)
```

> Deploy bloqueado se qualquer job de lint, teste ou build falhar.

---

<!-- Slide 10 — Deploy -->

## Deploy em Produção

### Backend → Railway
- PostgreSQL gerenciado (TimescaleDB via extensão)
- Redis gerenciado
- HTTPS automático em `*.up.railway.app`
- Migrations rodadas no startup via `entrypoint.sh`

### Frontend → Vercel
- CDN global com HTTPS automático
- Preview deployments em cada PR
- SPA routing via `vercel.json` (React Router funciona em deep links)

<br>

```
https://eh-brewing-api.up.railway.app    ← API
https://eh-brewing.vercel.app            ← Dashboard
```

---

<!-- Slide 11 — Simulador de CLP -->

## Simulador de CLP

Substitui o hardware durante desenvolvimento e apresentação.

```bash
# Modo normal — 8 panelas com temperatura realista (ruído gaussiano)
python simulator/clp_simulator.py

# Injetar falha: força panela 3 para 28°C (acima do limite)
python simulator/clp_simulator.py --fault-tank 3 --fault-temp 28.0

# Apontar para produção
python simulator/clp_simulator.py --api-url https://eh-brewing-api.up.railway.app
```

- Cada panela tem **setpoint configurável** + **ruído gaussiano** para simular variação real
- Intervalo padrão: **5 segundos** por panela
- Reconexão automática se a API estiver indisponível

---

<!-- Slide 12 — Demo ao Vivo -->

## Demo ao Vivo

### Roteiro sugerido

1. **Login** — entrar como `admin` no dashboard
2. **Cards ao vivo** — mostrar 8 panelas com temperatura atualizando em tempo real
3. **Alerta** — rodar `--fault-tank 3 --fault-temp 28.0` → ver badge vermelho aparecer
4. **Reconhecer** — clicar "Reconhecer" no AlertPanel
5. **Gráfico** — clicar na Panela 1, mudar período para 24h
6. **Modal de config** — editar nome e faixa de temperatura de uma panela
7. **Swagger UI** — mostrar endpoints documentados em `/docs`
8. **GitHub Actions** — mostrar pipeline verde

<br>

> Todos os passos funcionam com o **simulador rodando localmente** apontando para produção.

---

<!-- Slide 13 — Roadmap V4 -->

## Roadmap V4 — Controle Ativo

> Dependente de verificação do modelo N321 instalado na cervejaria.

```
Se N321 com RS485:
  CLP lê temperatura E escreve setpoint via Modbus RTU
  → sem hardware adicional

Se N321 sem RS485:
  CLP aciona relé externo em paralelo para controle ON/OFF
```

**Novas funcionalidades planejadas:**
- `POST /api/v1/tanks/{id}/control` — ligar/desligar aquecimento e resfriamento
- Setpoint configurável por panela no dashboard (seção já presente, `disabled`)
- Failsafe: N321 assume controle se software ficar offline
- Log de auditoria de ações de controle

---

<!-- Slide 14 — Encerramento -->

# Obrigado

<br>

## EH Brewing · Plataforma de Monitoramento

<br>

| | |
|---|---|
| **Repositório** | github.com/Gustavo4Souza/BackendProjectJeagers |
| **API (produção)** | `https://seu-backend.up.railway.app/docs` |
| **Dashboard** | `https://seu-frontend.vercel.app` |

<br>

> *"Do sensor ao dashboard — temperatura de todas as panelas, em tempo real."*

---

<!-- Notas para o apresentador:
     - Renderizar com Marp (VS Code: extensão "Marp for VS Code", botão Open Preview)
     - Exportar para PDF: Ctrl+Shift+P → "Marp: Export Slide Deck" → PDF
     - Duração estimada: 15–20 minutos com demo ao vivo
-->
