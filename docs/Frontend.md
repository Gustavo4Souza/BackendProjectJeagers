# EH Brewing — Frontend

> Dashboard web para monitoramento e controle de temperatura das 8 panelas.
> Stack: React 18 + Vite + TypeScript + Tailwind CSS + Recharts + React Router v6.
> Quatro telas via TopBar: Painel · Histórico · Alertas · Config.

---

## Decisões de UI

- **Quatro telas** acessíveis via TopBar: Painel, Histórico, Alertas e Config
- **Painel (tela principal):** cards das 8 panelas + gráfico da panela selecionada + alertas ativos
- **Navegação por React Router v6** — sem reload de página
- **Card selecionado** — clicar em uma panela atualiza o gráfico de histórico no rodapé
- **Modal de configuração** — abre ao clicar na engrenagem de cada card
- **Controle de temperatura habilitado** no modal (Fase 2): setpoint + ETA
- **Tempo real via WebSocket** — temperatura, alertas e controle atualizam sem recarregar

---

## Estrutura de Arquivos

```
frontend/src/
├── components/
│   ├── layout/
│   │   ├── TopBar.tsx
│   │   └── AlertBadge.tsx
│   ├── tanks/
│   │   ├── TankGrid.tsx
│   │   ├── TankCard.tsx
│   │   ├── TempBar.tsx
│   │   └── TankConfigModal.tsx
│   ├── chart/
│   │   ├── TankHistoryChart.tsx       # gráfico de uma panela (Painel)
│   │   └── MultiTankHistoryChart.tsx  # gráfico de múltiplas panelas (Histórico)
│   ├── alerts/
│   │   └── AlertPanel.tsx
│   ├── control/
│   │   └── ETADisplay.tsx             # Fase 2
│   └── batches/
│       ├── BatchCard.tsx
│       └── BatchDetailModal.tsx
├── hooks/
│   ├── useTanks.ts
│   ├── useTankReadings.ts
│   ├── useWebSocket.ts
│   ├── useAlerts.ts
│   └── useTankControl.ts              # Fase 2
├── services/
│   ├── api.ts
│   ├── tanks.ts
│   ├── readings.ts
│   ├── alerts.ts
│   ├── control.ts                     # Fase 2
│   └── batches.ts
├── types/
│   └── index.ts
├── utils/
│   ├── formatTemp.ts
│   ├── getTankStatus.ts
│   └── formatDateTime.ts
└── pages/
    ├── Dashboard.tsx                  # ✅ Concluído
    ├── HistoricoPage.tsx              # 🔲 Pendente
    ├── AlertasPage.tsx                # 🔲 Pendente
    ├── ConfigPage.tsx                 # 🔲 Pendente
    └── BatchesPage.tsx                # 🔲 Pendente
```

---

## Tipos principais

```typescript
// types/index.ts

export type TankStatus = 'normal' | 'warning' | 'alert' | 'offline'
export type ControlMode = 'cooling' | 'heating' | 'idle'

export interface Tank {
  id: number
  name: string
  location: string
  temp_min: number
  temp_max: number
  status: 'active' | 'inactive' | 'maintenance'
  current_temperature: number | null
  last_reading_at: string | null
}

export interface Reading {
  id: number
  tank_id: number
  temperature: number
  recorded_at: string
}

export interface Alert {
  id: number
  tank_id: number
  tank_name: string
  temperature: number
  type: 'above_max' | 'below_min'
  fired_at: string
  resolved_at: string | null
  acknowledged_by: number | null
}

export interface TankControl {
  tank_id: number
  setpoint: number
  mode: ControlMode
  updated_at: string
  updated_by: number | null
}

export interface ETAResult {
  eta_minutes: number | null
  rate_per_minute: number | null
  current_temp: number
  setpoint: number
  sufficient_data: boolean
}

export interface YeastProfile {
  id: number
  name: string
  strain: string
  attenuation_min: number
  attenuation_max: number
  temperature_min_c: number
  temperature_max_c: number
  notes: string
}

export interface Batch {
  id: number
  name: string
  style: string
  status: 'planned' | 'active' | 'completed' | 'cancelled'
  fermenter_id: number
  original_gravity: number | null
  final_gravity: number | null
  volume_liters: number | null
  started_at: string | null
  ended_at: string | null
  yeast_profile_id: number | null
  notes: string
  abv: number | null          // calculado pelo backend
  attenuation: number | null  // calculado pelo backend
}

export interface BatchEvent {
  id: number
  batch_id: number
  event_type: string
  description: string
  value: number | null
  unit: string | null
  occurred_at: string
}
```

---

## Roteamento

```tsx
// App.tsx
<BrowserRouter>
  <TopBar />
  <Routes>
    <Route path="/"          element={<Dashboard />} />
    <Route path="/historico" element={<HistoricoPage />} />
    <Route path="/alertas"   element={<AlertasPage />} />
    <Route path="/config"    element={<ConfigPage />} />
    <Route path="/lotes"     element={<BatchesPage />} />
  </Routes>
</BrowserRouter>
```

---

## Componentes — Tela Painel ✅

---

### `Dashboard.tsx` — página principal ✅

**Estado local:**
```typescript
const [selectedTankId, setSelectedTankId] = useState<number>(1)
const [configModalTankId, setConfigModalTankId] = useState<number | null>(null)
```

**Layout:**
```
TopBar
──────────────────────────────────────
TankGrid (8 cards, 4 colunas)
──────────────────────────────────────
TankHistoryChart  |  AlertPanel
(2/3 da largura)  |  (1/3)
```

---

### `TopBar.tsx` ✅

**Props:** `alertCount: number`

**Renderiza:**
- Logo "EH Brewing" — "Brewing" em verde (#1D9E75)
- Navegação: Painel · Histórico · Alertas · Config — links ativos via React Router `NavLink`
- Badge de alertas com ícone de sino
- Nome do usuário logado + botão Sair

---

### `TankGrid.tsx` ✅

Grid 4×2 responsivo. Passa `isSelected` e callbacks para cada `TankCard`.

---

### `TankCard.tsx` ✅

Exibe número da panela, nome da bebida, temperatura atual, barra visual, status e pill de modo de controle.

**Pill de controle (Fase 2):** exibir "↓ Resfriando" ou "↑ Aquecendo" quando `mode !== 'idle'`.

**Cores por status:**
| Status | Dot | Borda card | Temperatura | Pill |
|---|---|---|---|---|
| normal | #1D9E75 | cinza padrão | padrão | verde |
| warning | #EF9F27 | #EF9F27 | #BA7517 | amarelo |
| alert | #D85A30 | #D85A30 | #D85A30 | vermelho |
| offline | cinza | cinza | "—" | cinza |

---

### `TempBar.tsx` ✅

Barra horizontal 4px. Posição: `((temperature - tempMin) / (tempMax - tempMin)) * 100`, clamped 0–100%.

---

### `TankConfigModal.tsx` ✅ (seção de controle pendente)

**Seções:**

**1. Nome da bebida** ✅
- Input texto livre, máx 50 chars

**2. Faixa de temperatura** ✅
- temp_min e temp_max com validação `temp_min < temp_max`

**3. Controle de temperatura** 🔲 Fase 2
- **Remover** `disabled` e badge "em breve"
- Input de setpoint (numérico, step 0.5, com label "Temperatura alvo (°C)")
- Botão "Aplicar setpoint" → `POST /api/v1/tanks/{id}/control`
- Pill de modo atual: "Resfriando ↓" (azul), "Aquecendo ↑" (laranja), "Estável ✓" (verde), "Inativo" (cinza)
- Componente `ETADisplay` logo abaixo do botão

**Endpoint config:**
```
PATCH /api/v1/tanks/{id}/config  →  { name, temp_min, temp_max }
```

**Endpoint controle:**
```
POST /api/v1/tanks/{id}/control  →  { setpoint }
```

---

### `ETADisplay.tsx` 🔲 Fase 2

**Props:** `tankId: number`, `setpoint: number`

**Renderiza:**
- "Estimativa: ~47 min para atingir 2,0°C" — em destaque
- "Taxa atual: −0,25°C/min" — secundário
- "—" se `sufficient_data: false` ou sem setpoint definido
- Atualiza a cada nova leitura via WebSocket

**Hook:** `useTankETA(tankId)` — React Query com refetch a cada 30s

---

### `TankHistoryChart.tsx` ✅

Recharts `LineChart`. Seletor 6h · 24h · 7d · 30d. `ReferenceLine` em `temp_min` e `temp_max`. Tooltip customizado.

---

### `AlertPanel.tsx` ✅

Lista alertas ativos ordenados por `fired_at` desc. Botão "Reconhecer" por item. Estado vazio com check verde.

---

## Componentes — Tela Histórico 🔲

### `HistoricoPage.tsx`

**Estado local:**
```typescript
const [selectedTankIds, setSelectedTankIds] = useState<number[]>([1])
const [period, setPeriod] = useState<'6h' | '24h' | '7d' | '30d'>('24h')
```

**Layout:**
```
Seletor de panelas (checkboxes, até 4 simultâneas)
Seletor de período: 6h · 24h · 7d · 30d
MultiTankHistoryChart (largura total)
```

---

### `MultiTankHistoryChart.tsx` 🔲

**Props:** `tankIds: number[]`, `period: string`

**Renderiza:**
- Recharts `LineChart` com uma linha por panela selecionada
- Cores distintas por panela (paleta fixa de 8 cores)
- Legenda com nome de cada panela
- Eixo X: timestamps formatados por período
- Eixo Y: temperatura em °C
- Tooltip mostrando todas as temperaturas no ponto hovado

**Hook:** `useMultiTankReadings(tankIds, period)` — React Query paralelo

---

## Componentes — Tela Alertas 🔲

### `AlertasPage.tsx`

**Estado local:**
```typescript
const [filters, setFilters] = useState({
  status: 'active' | 'resolved' | 'all',
  tankId: number | null,
  period: '24h' | '7d' | '30d' | 'all'
})
```

**Layout:**
```
Filtros: Status · Panela · Período
Botão "Reconhecer todos" (visível apenas se houver ativos)
Lista de alertas (AlertsTable)
```

**Colunas da tabela:**
- Panela / nome da bebida
- Temperatura no disparo
- Tipo (Acima do máx / Abaixo do mín)
- Horário de disparo
- Horário de resolução
- Status (badge: Ativo / Resolvido / Reconhecido)
- Ação (botão "Reconhecer" se ativo)

**Endpoints:**
```
GET /api/v1/alerts?status=active&tank_id=&period=
POST /api/v1/alerts/acknowledge-all
```

---

## Componentes — Tela Config 🔲

### `ConfigPage.tsx`

Três seções em abas ou acordeão:

**Seção "Panelas"**
- Tabela editável com as 8 panelas: nome, temp_min, temp_max
- Salvar linha por linha (sem abrir modal)
- `PATCH /api/v1/tanks/{id}/config`

**Seção "Usuários"** (somente admin)
- Tabela: username, role, status
- Botão "Novo usuário" → modal com username, senha, role
- Ação "Alterar role" inline (dropdown)
- `GET /api/v1/users`, `POST /api/v1/users`, `PATCH /api/v1/users/{id}`

**Seção "Sistema"**
- Informações: versão da API, status do banco, status do Redis
- `GET /health`

---

## Componentes — Lotes e Leveduras 🔲

### `BatchesPage.tsx`

**Layout:**
```
Botão "Novo Lote"
Filtros: Status · Estilo · Panela
Grid de BatchCards
```

---

### `BatchCard.tsx`

**Props:** `batch: Batch`, `onClick: () => void`

**Renderiza:**
- Nome do lote + estilo
- Panela associada (nome)
- Status em pill colorida
- ABV calculado (se disponível)
- Datas de início e fim
- Clique abre `BatchDetailModal`

---

### `BatchDetailModal.tsx`

**Props:** `batch: Batch`, `events: BatchEvent[]`, `onClose: () => void`

**Seções:**
- Dados gerais: OG, FG, volume, levedura
- Métricas calculadas: ABV e atenuação aparente
- Linha do tempo de eventos (ordem cronológica)
- Formulário inline "Adicionar evento"
- Botão "Exportar CSV"

---

## Hooks

```typescript
// useTanks.ts — React Query, refetch a cada 30s
export function useTanks() { ... }

// useWebSocket.ts — reconexão com backoff 1s→2s→4s→max 30s
export function useWebSocket(tankId: number, onReading: (r: Reading) => void) { ... }

// useTankReadings.ts
export function useTankReadings(tankId: number, period: '6h'|'24h'|'7d'|'30d') { ... }

// useAlerts.ts — refetch a cada 10s
export function useAlerts(filters?: AlertFilters) { ... }

// useTankControl.ts — Fase 2, refetch a cada 10s
export function useTankControl(tankId: number) {
  return useQuery({
    queryKey: ['control', tankId],
    queryFn: () => controlService.getControl(tankId),
    refetchInterval: 10_000,
  })
}

// useTankETA.ts — Fase 2
export function useTankETA(tankId: number) {
  return useQuery({
    queryKey: ['eta', tankId],
    queryFn: () => controlService.getETA(tankId),
    refetchInterval: 30_000,
  })
}
```

---

## Services

```typescript
// services/api.ts — instância Axios centralizada
// Interceptor: Authorization header
// Interceptor: 401 → limpa token + redireciona /login

// services/tanks.ts
export const tanksService = {
  getAll: () => api.get<Tank[]>('/api/v1/tanks').then(r => r.data),
  updateConfig: (id: number, data: Partial<Tank>) =>
    api.patch(`/api/v1/tanks/${id}/config`, data).then(r => r.data),
}

// services/readings.ts
export const readingsService = {
  getByTank: (id: number, period: string) =>
    api.get<Reading[]>(`/api/v1/tanks/${id}/readings`, { params: { period } }).then(r => r.data),
  exportCSV: (id: number, period: string) =>
    api.get(`/api/v1/tanks/${id}/readings/export`, { params: { period }, responseType: 'blob' }).then(r => r.data),
}

// services/alerts.ts
export const alertsService = {
  getAll: (filters?: AlertFilters) =>
    api.get<Alert[]>('/api/v1/alerts', { params: filters }).then(r => r.data),
  getActive: () => alertsService.getAll({ status: 'active' }),
  acknowledge: (id: number) => api.patch(`/api/v1/alerts/${id}/acknowledge`).then(r => r.data),
  acknowledgeAll: () => api.post('/api/v1/alerts/acknowledge-all').then(r => r.data),
}

// services/control.ts — Fase 2
export const controlService = {
  getControl: (id: number) =>
    api.get<TankControl>(`/api/v1/tanks/${id}/control`).then(r => r.data),
  setControl: (id: number, setpoint: number) =>
    api.post<TankControl>(`/api/v1/tanks/${id}/control`, { setpoint }).then(r => r.data),
  getETA: (id: number) =>
    api.get<ETAResult>(`/api/v1/tanks/${id}/eta`).then(r => r.data),
}

// services/batches.ts
export const batchesService = {
  getAll: (filters?: BatchFilters) =>
    api.get<Batch[]>('/api/v1/batches', { params: filters }).then(r => r.data),
  getById: (id: number) =>
    api.get<Batch>(`/api/v1/batches/${id}`).then(r => r.data),
  create: (data: Partial<Batch>) =>
    api.post<Batch>('/api/v1/batches', data).then(r => r.data),
  update: (id: number, data: Partial<Batch>) =>
    api.patch<Batch>(`/api/v1/batches/${id}`, data).then(r => r.data),
  addEvent: (id: number, event: Partial<BatchEvent>) =>
    api.patch(`/api/v1/batches/${id}/events`, event).then(r => r.data),
  exportCSV: (id: number) =>
    api.get(`/api/v1/batches/${id}/export`, { responseType: 'blob' }).then(r => r.data),
}
```

---

## Utilitários

```typescript
// formatTemp.ts
export const formatTemp = (temp: number | null): string =>
  temp === null ? '—' : `${temp.toFixed(1)}°C`

// formatDateTime.ts
export const formatRelative = (iso: string): string => { /* "há 5 min", "há 2h" */ }
export const formatChartLabel = (iso: string, period: string): string => { /* "14:30", "seg", "01/05" */ }
export const formatETA = (minutes: number | null): string => {
  if (!minutes) return '—'
  if (minutes < 60) return `~${Math.round(minutes)} min`
  return `~${Math.round(minutes / 60)}h ${Math.round(minutes % 60)}min`
}

// getTankStatus.ts — não duplicar esta lógica em outros lugares
export function getTankStatus(tank: Tank): TankStatus { ... }
```

---

## Fluxo de dados — tempo real

```
WebSocket /ws/tanks/{1..8}   (8 conexões simultâneas)
    ↓ { tank_id, temperature, recorded_at }
useWebSocket → queryClient.setQueryData(['tanks'])
    ↓ TankCard re-renderiza

WebSocket /ws/alerts
    ↓ novo alerta ou resolução
useAlerts → queryClient.invalidateQueries(['alerts'])
    ↓ AlertPanel + badge TopBar atualizam

WebSocket /ws/control          (Fase 2)
    ↓ mudança de setpoint / mode
useTankControl → queryClient.setQueryData(['control', tankId])
    ↓ pill do TankCard + ETADisplay atualizam
```

---

## Variáveis de ambiente

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_WS_RECONNECT_MAX_MS=30000
```

---

## Comportamentos importantes

- **Card selecionado:** outline verde + gráfico atualiza para aquela panela
- **Offline:** dot cinza + "—" + pill "Offline" se sem leitura há 30s+
- **Controle ativo:** pill "↓ Resfriando" ou "↑ Aquecendo" no card + no modal
- **ETA insuficiente:** exibe "—" se < 10 leituras históricas
- **Múltiplos alertas:** AlertPanel mostra todos; badge TopBar soma o total
- **Modal:** overlay escurecido; fecha ao clicar fora ou em "Cancelar"
- **Erro de rede:** `ErrorBanner` no topo com mensagem e botão retry
- **Histórico múltiplo:** máximo 4 panelas simultâneas no MultiTankHistoryChart
