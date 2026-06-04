# EH Brewing — Roadmap

> Plataforma de monitoramento e controle de temperatura para 8 panelas de bebidas.
> Stack: PostgreSQL + TimescaleDB + FastAPI + Redis + React (SPA).
> Fase 1 (monitoramento) concluída. Fase 2 (controle ativo) em desenvolvimento.
> Apresentação ao cliente: ambiente local via Docker Compose.

---

## Decisões de Arquitetura

- **Backend:** Python 3.12 + FastAPI, porta 8000
- **ORM:** SQLAlchemy 2.x (async) + Alembic para migrations
- **Banco:** PostgreSQL + TimescaleDB (hypertable para série temporal)
- **Cache / Pub-Sub:** Redis
- **Tempo real:** WebSocket (FastAPI + Redis Pub/Sub)
- **Frontend:** React + Vite + TypeScript, porta 5173
- **Gráficos:** Recharts
- **HTTP Client:** Axios
- **Estado de servidor:** React Query
- **Autenticação:** JWT + roles (admin / operator / viewer)
- **Simulador de CLP:** script Python que envia leituras das 8 panelas via HTTP POST e responde a comandos de controle
- **Hardware real (produção futura):** CLP central lendo NTC de cada panela → HTTP para API; relé ON/OFF por panela

---

## Decisões de UI

- **Quatro telas via TopBar:** Painel · Histórico · Alertas · Config
- **Painel (tela principal):** cards de 8 panelas + gráfico da panela selecionada + alertas ativos
- **Histórico:** gráfico sobreposto das 8 panelas com seletor de período
- **Alertas:** lista completa de alertas com filtros e ações
- **Config:** gestão de usuários e configurações do sistema
- **Card selecionado:** clicar numa panela atualiza o gráfico de histórico no rodapé
- **Modal de configuração:** abre ao clicar na engrenagem de cada card
- **Controle de temperatura:** habilitado no modal (Fase 2) — setpoint + estimativa de tempo

---

## Status Atual

| Módulo | Status |
|---|---|
| Backend base (FastAPI + DB + Redis + Docker) | ✅ Concluído |
| Simulador de CLP (leituras) | ✅ Concluído |
| API de panelas, leituras, alertas | ✅ Concluído |
| WebSocket tempo real | ✅ Concluído |
| Autenticação JWT | ✅ Concluído |
| Frontend — tela Painel | ✅ Concluído |
| Frontend — tela Histórico | ✅ Concluído |
| Frontend — tela Alertas | ✅ Concluído |
| Frontend — tela Config | ✅ Concluído |
| Controle de temperatura (backend + simulador) | ✅ Concluído |
| Previsão de tempo de estabilização (ETA) | ✅ Concluído |
| Lotes (Batches) | ✅ Concluído |
| Perfis de Levedura | ✅ Concluído |

---

## V1 — Backend: Base da API ✅ Concluído

### Fase 1 — Setup e Schema do Banco ✅
- [X] Setup Python + FastAPI + CORS + dotenv (pydantic-settings)
- [X] Configurar SQLAlchemy async + PostgreSQL + TimescaleDB
- [X] Schema completo: `tanks`, `readings`, `alerts`, `users`, `refresh_tokens`, `batches`, `yeast_profiles`, `batch_events`
- [X] Hypertable TimescaleDB na tabela `readings`
- [X] Migrations com Alembic
- [X] Docker Compose funcional: FastAPI + PostgreSQL/TimescaleDB + Redis
- [X] Health check: `GET /health`

### Fase 2 — Simulador de CLP ✅
- [X] Script `simulator/clp_simulator.py` simulando 8 panelas
- [X] Temperatura realista: setpoint por panela + ruído gaussiano
- [X] Envio de `POST /api/v1/readings` a cada 5s
- [X] Modo de injeção de falhas: `--fault-tank 3 --fault-temp 28.0`
- [X] Reconexão automática se API estiver indisponível

### Fase 3 — Leituras e Tanques ✅
- [X] `POST /api/v1/readings`
- [X] `GET /api/v1/tanks`
- [X] `GET /api/v1/tanks/{id}/readings?period=6h|24h|7d|30d`
- [X] `GET /api/v1/tanks/{id}/status`
- [X] `PATCH /api/v1/tanks/{id}/config`
- [X] Seed: 8 panelas com faixas padrão

### Fase 4 — Alertas ✅
- [X] Motor de alertas por leitura recebida
- [X] `GET /api/v1/alerts?status=active`
- [X] `PATCH /api/v1/alerts/{id}/acknowledge`
- [X] Resolução automática ao retornar à faixa

### Fase 5 — Tempo Real (WebSocket) ✅
- [X] Redis Pub/Sub por panela
- [X] `WS /ws/tanks/{id}` e `WS /ws/alerts`
- [X] Suporte a múltiplas conexões simultâneas via `FermenterWebSocketHub`

### Fase 6 — Autenticação ✅
- [X] Tabela `users` (admin / operador / viewer) e `refresh_tokens`
- [X] `POST /auth/login`, `/auth/refresh`, `/auth/logout`
- [X] Middleware HTTP protegendo todas as rotas
- [X] Permissões por role via `require_roles()`
- [X] Seed de usuário admin

---

## V2 — Frontend: Painel de Monitoramento

### Fase 1 — Setup e Infraestrutura ✅ Concluído
- [X] React + Vite + TypeScript + Tailwind CSS
- [X] Axios centralizado + React Query configurado
- [X] Services tipados: `tanks.ts`, `readings.ts`, `alerts.ts`
- [X] Tipos globais: `Tank`, `Reading`, `Alert`, `TankStatus`
- [X] Utilitários: `formatTemp`, `formatDateTime`, `getTankStatus`
- [X] Variáveis de ambiente: `VITE_API_URL`, `VITE_WS_URL`

### Fase 2 — Hook de WebSocket ✅ Concluído
- [X] `useWebSocket(tankId, onReading)` com backoff exponencial
- [X] `onReading` atualiza `queryClient.setQueryData(['tanks'])`

### Fase 3 — Cards das 8 Panelas ✅ Concluído
- [X] `TankGrid.tsx` — grid 4×2 responsivo
- [X] `TankCard.tsx` — número + nome + temperatura atual
- [X] `TempBar.tsx` — barra colorida na faixa
- [X] Semáforo: verde / amarelo / vermelho / cinza
- [X] Card selecionado com outline verde
- [X] Estado offline: dot cinza + "—" + pill "Offline"

### Fase 4 — Gráfico de Histórico ✅ Concluído
- [X] `TankHistoryChart.tsx` — Recharts `LineChart`
- [X] Seletor de período: 6h · 24h · 7d · 30d
- [X] `ReferenceLine` em `temp_min` e `temp_max`
- [X] Tooltip com temperatura e horário

### Fase 5 — Painel de Alertas e Modal ✅ Concluído
- [X] `AlertPanel.tsx` com botão "Reconhecer" por alerta
- [X] Badge de alertas ativos no `TopBar`
- [X] `TankConfigModal.tsx` — nome, `temp_min`, `temp_max`
- [X] Seção de controle (Fase 2) presente, desabilitada com badge "em breve"

### Fase 6 — Autenticação no Frontend ✅ Concluído
- [X] Página de login com JWT
- [X] Proteção de rotas + interceptors Axios
- [X] Refresh token automático

---

## V3 — Controle de Temperatura ✅ Concluído

**Objetivo:** usuário define setpoint por panela; simulador responde ao comando e ajusta temperatura conforme o controle. Previsão de tempo de estabilização exibida no modal.

### Fase 1 — Backend: Controle e Previsão ✅

- [X] Tabela `tank_control`: `tank_id`, `setpoint`, `mode` (`cooling`|`heating`|`idle`), `updated_at`, `updated_by`
- [X] `POST /api/v1/tanks/{id}/control` — define setpoint e modo (admin / operador)
  - Body: `{ "setpoint": 8.0 }`
  - Lógica: se `setpoint < temp_atual` → mode `cooling`; se `setpoint > temp_atual` → mode `heating`; se igual → `idle`
- [X] `GET /api/v1/tanks/{id}/control` — retorna estado de controle atual
- [X] `GET /api/v1/tanks/{id}/eta` — retorna estimativa de tempo para atingir setpoint
  - Cálculo: taxa de variação °C/min nas últimas 6h × distância ao setpoint
  - Retorna: `{ "eta_minutes": 47, "rate_per_minute": -0.25, "current_temp": 14.2, "setpoint": 2.0, "sufficient_data": true }`
- [X] Publicar mudança de controle no Redis → WebSocket `/ws/control`
- [X] Auto-update de mode para `idle` quando leitura chega dentro de ±0,3°C do setpoint
- [X] Migration `003_tank_control.py`
- [X] Seed padrão: todas as panelas com `mode = idle` via `seed_tanks.py`

### Fase 2 — Simulador: Resposta ao Controle ✅

- [X] Simulador consulta `GET /api/v1/tanks/{id}/control` a cada ciclo
- [X] Quando `mode = cooling`: temperatura converge para setpoint com taxa `--cooling-rate` (padrão 0.3°C/ciclo)
- [X] Quando `mode = heating`: temperatura sobe em direção ao setpoint com taxa `--heating-rate` (padrão 0.2°C/ciclo)
- [X] Quando `mode = idle`: comportamento atual (deriva natural com ruído gaussiano)
- [X] Quando temperatura atinge setpoint (±0.3°C): ruído mínimo (σ=0.05°C)
- [X] Parâmetros CLI adicionais: `--cooling-rate`, `--heating-rate`

### Fase 3 — Frontend: Controle e ETA no Modal ✅

- [X] `TankConfigModal.tsx`: seção de controle habilitada
  - Input de setpoint (numérico, step 0.5)
  - Botão "Aplicar setpoint" — chama `POST /api/v1/tanks/{id}/control`
  - Pill do modo atual: "↓ Resfriando" (azul) / "↑ Aquecendo" (laranja) / "✓ Estável" (verde)
- [X] Componente `ETADisplay.tsx` dentro do modal
- [X] `TankCard.tsx`: pill "↓ Resfriando" ou "↑ Aquecendo" quando em modo ativo
- [X] Hook `useTankControl(tankId)` + `useTankETA(tankId)` + `useSetControl` + `useControlWebSocket`
- [X] Service `control.ts`: `getControl`, `setControl`, `getETA`
- [X] WebSocket `/ws/control` integrado ao Dashboard via `ControlWebSocketConnector`
- [X] Tipos `TankControl`, `ETAResult`, `ControlMode` adicionados a `types/index.ts`

---

## V4 — Telas Pendentes do TopBar ✅ Concluído

**Objetivo:** completar as 4 telas do TopBar para apresentação completa ao cliente.

### Tela: Histórico ✅

- [X] Rota `/historico` no React Router
- [X] Seletor de panelas (checkbox múltiplo) — até 4 panelas simultâneas
- [X] Gráfico `MultiTankHistoryChart` com Recharts: linhas coloridas por panela, legenda
- [X] Seletor de período: 6h · 24h · 7d · 30d
- [X] Exportar CSV: `GET /api/v1/tanks/{id}/readings/export?period=`

### Tela: Alertas ✅

- [X] Rota `/alertas`
- [X] `AlertasPage.tsx` — lista completa (ativos e histórico)
- [X] Filtros: por panela, por status (ativo / resolvido), por período
- [X] Ordenação por `fired_at` desc
- [X] Botão "Reconhecer todos" para alertas não reconhecidos
- [X] Indicador visual: badge por status (Ativo / Reconhecido / Resolvido)
- [X] Backend enriquecido: `tank_name` e `alert_type` incluídos na resposta de alertas
- [X] `POST /api/v1/alerts/acknowledge-all`
- [X] Filtro por período na `GET /api/v1/alerts`

### Tela: Config ✅

- [X] Rota `/config`
- [X] Seção "Panelas": editar nome e faixas de todas as 8 panelas em tabela única (edição inline por linha)
- [X] Seção "Usuários": listar, criar, editar role, remover (somente admin)
  - `GET /api/v1/users`, `POST /api/v1/users`, `PATCH /api/v1/users/{id}`, `DELETE /api/v1/users/{id}`
- [X] Seção "Sistema": status da API, versão, informações de infraestrutura
- [X] TopBar com NavLinks funcionais para todas as telas (React Router `NavLink`)

---

## V5 — Lotes e Perfis de Levedura ✅ Concluído

**Objetivo:** rastrear lotes de fermentação associados às panelas, com perfis de levedura e registro de eventos.

### Fase 1 — Backend: Lotes ✅

- [X] `POST /api/v1/batches` — criar lote (admin, operador)
- [X] `GET /api/v1/batches` — listar com filtros: `?status=`, `?style=`
- [X] `GET /api/v1/batches/{id}` — detalhe com ABV e atenuação calculados
  - ABV = (OG − FG) × 131,25
  - Atenuação Aparente = ((OG − FG) / (OG − 1)) × 100%
- [X] `PATCH /api/v1/batches/{id}` — atualizar lote
- [X] `PATCH /api/v1/batches/{id}/events` — adicionar evento (pitch, dry hop, cold crash…)
- [X] `GET /api/v1/batches/{id}/export` — exportar lote em CSV

### Fase 2 — Backend: Perfis de Levedura ✅

- [X] `POST /api/v1/yeast_profiles` — criar perfil (admin)
- [X] `GET /api/v1/yeast_profiles` — listar
- [X] `GET /api/v1/yeast_profiles/{id}` — detalhe
- [X] `PATCH /api/v1/yeast_profiles/{id}` — atualizar (admin)
- [X] `DELETE /api/v1/yeast_profiles/{id}` — remover (falha se vinculado a lotes)

### Fase 3 — Frontend: Lotes ✅

- [X] Rota `/lotes` no React Router
- [X] `BatchesPage.tsx` — grid de cards com filtro por status (planned/active/completed/cancelled)
- [X] `BatchCard.tsx` — nome, estilo, panela associada, datas, OG/FG embutidos
- [X] `BatchDetailModal.tsx` — detalhe completo: info, ABV, atenuação, edição inline, export CSV
- [X] Linha do tempo de eventos com `AddEventForm` embutida no modal
- [X] Formulário de criação: nome, estilo, panela, OG, volume, levedura, notas
- [X] Formulário de edição inline: todos os campos + status
- [X] TopBar atualizado com link "Lotes"
- [X] `services/batches.ts` + tipos `Batch`, `BatchDetail`, `BatchEvent` em `types/index.ts`

### Fase 4 — Frontend: Perfis de Levedura ✅

- [X] Seção "Leveduras" na tela Config (nova entrada na sidebar)
- [X] Tabela de perfis com atributos: nome, cepa, faixa de temperatura, atenuação
- [X] Modal de criação/edição (campos: nome, cepa, temp min/max, atenuação min/max, notas)
- [X] Botão "Remover" com confirmação — bloqueado pelo backend se perfil ligado a lotes
- [X] `yeastProfilesService` em `services/batches.ts`
- [X] Tipo `YeastProfile` em `types/index.ts`

---

## Fora do Escopo Atual

- Deploy em produção (Railway / Vercel / CI-CD) — avaliar após apresentação ao cliente
- Controle PID (Fase 2 usa relé ON/OFF simples)
- App mobile nativo
- Integração com PDV ou sistema de estoque
- Controle de insumos
