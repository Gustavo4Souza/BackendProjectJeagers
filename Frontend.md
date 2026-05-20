# EH Brewing — Frontend

> Dashboard web para monitoramento de temperatura das 8 panelas.
> Stack: React + Vite + TypeScript + Tailwind CSS + Recharts.
> Uma única tela principal (Painel) entrega todo o monitoramento necessário.

---

## Decisões de UI

- **Uma tela principal** — o Painel concentra tudo: cards, gráfico e alertas
- **Sem rotas de página** para o fluxo principal — navegação por estado interno (card selecionado, modal aberto)
- **Card selecionado** — clicar em uma panela atualiza o gráfico de histórico no rodapé
- **Modal de configuração** — abre ao clicar no ícone de engrenagem de cada card
- **Controle de temperatura** presente no modal mas desabilitado (Fase 2)
- **Tempo real via WebSocket** — temperatura e alertas atualizam sem recarregar a página
- **Tema claro/escuro** via variáveis CSS

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
│   │   └── TankHistoryChart.tsx
│   └── alerts/
│       └── AlertPanel.tsx
├── hooks/
│   ├── useTanks.ts
│   ├── useTankReadings.ts
│   ├── useWebSocket.ts
│   └── useAlerts.ts
├── services/
│   ├── api.ts
│   ├── tanks.ts
│   ├── readings.ts
│   └── alerts.ts
├── types/
│   └── index.ts
├── utils/
│   ├── formatTemp.ts
│   ├── getTankStatus.ts
│   └── formatDateTime.ts
└── pages/
    └── Dashboard.tsx
```

---

## Tipos principais

```typescript
// types/index.ts

export type TankStatus = 'normal' | 'warning' | 'alert' | 'offline'

export interface Tank {
  id: number
  name: string           // nome da bebida — ex: "Pilsen Lager"
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
```

---

## Componentes

---

### `Dashboard.tsx` — página principal

**Estado local:**
```typescript
const [selectedTankId, setSelectedTankId] = useState<number>(1)
const [configModalTankId, setConfigModalTankId] = useState<number | null>(null)
```

**Responsabilidades:**
- Renderiza `TopBar`, `TankGrid`, `TankHistoryChart`, `AlertPanel`
- Mantém `selectedTankId` — passado para `TankGrid` e `TankHistoryChart`
- Mantém `configModalTankId` — controla qual modal está aberto
- Ao montar, seleciona a panela 1 por padrão

**Layout:**
```
TopBar
──────────────────────────────
TankGrid (8 cards, 4 colunas)
──────────────────────────────
TankHistoryChart  |  AlertPanel
(2/3 da largura)  | (1/3)
```

---

### `TopBar.tsx`

**Props:** `alertCount: number`

**Renderiza:**
- Logo "EH Brewing" com "Brewing" em verde (#1D9E75)
- Navegação: Painel (ativo) · Histórico · Alertas · Config
- Badge de alertas ativos com ícone de sino
- Nome do usuário logado

**Notas:**
- Badge vermelho só aparece se `alertCount > 0`
- Links de navegação são decorativos na V1 — só "Painel" está implementado

---

### `TankGrid.tsx`

**Props:**
```typescript
interface TankGridProps {
  tanks: Tank[]
  selectedTankId: number
  onSelectTank: (id: number) => void
  onConfigTank: (id: number) => void
}
```

**Responsabilidades:**
- Grid 4×2 responsivo
- Passa `isSelected` e callbacks para cada `TankCard`

---

### `TankCard.tsx`

**Props:**
```typescript
interface TankCardProps {
  tank: Tank
  isSelected: boolean
  onSelect: () => void
  onConfig: () => void
}
```

**Responsabilidades:**
- Exibe número da panela (discreto, topo esquerdo), nome da bebida (destaque), temperatura atual, barra visual e status
- Borda colorida conforme status: verde / amarelo / vermelho / cinza (offline)
- Temperatura colorida quando fora da faixa
- Ícone de engrenagem no topo direito — chama `onConfig` ao clicar
- `onSelect` disparado ao clicar no card (qualquer área exceto a engrenagem)
- Card selecionado tem `outline: 2px solid #1D9E75`

**Lógica de status (`getTankStatus`):**
```typescript
// utils/getTankStatus.ts
export function getTankStatus(tank: Tank): TankStatus {
  if (!tank.current_temperature) return 'offline'
  // offline se última leitura há mais de 30s
  const lastReading = new Date(tank.last_reading_at!)
  if (Date.now() - lastReading.getTime() > 30_000) return 'offline'

  if (tank.current_temperature > tank.temp_max) return 'alert'
  if (tank.current_temperature < tank.temp_min) return 'alert'
  if (tank.current_temperature > tank.temp_max - 0.5) return 'warning'
  if (tank.current_temperature < tank.temp_min + 0.5) return 'warning'
  return 'normal'
}
```

**Cores por status:**
| Status | Dot | Borda card | Temperatura | Pill |
|---|---|---|---|---|
| normal | #1D9E75 | cinza padrão | padrão | verde |
| warning | #EF9F27 | #EF9F27 | #BA7517 | amarelo |
| alert | #D85A30 | #D85A30 | #D85A30 | vermelho |
| offline | cinza | cinza | cinza | cinza |

---

### `TempBar.tsx`

**Props:** `temperature: number`, `tempMin: number`, `tempMax: number`, `status: TankStatus`

**Responsabilidades:**
- Barra horizontal de 4px de altura
- Posição do preenchimento: `((temperature - tempMin) / (tempMax - tempMin)) * 100`
- Clamped entre 0% e 100% — não extrapola visualmente
- Cor segue o status: verde / amarelo / vermelho

---

### `TankConfigModal.tsx`

**Props:**
```typescript
interface TankConfigModalProps {
  tank: Tank
  onClose: () => void
  onSave: (update: { name: string; temp_min: number; temp_max: number }) => void
}
```

**Seções do modal:**

**1. Nome da bebida**
- Input de texto livre
- Placeholder: "Ex: Pilsen Lager, IPA Amaricana..."
- Máximo 50 caracteres

**2. Faixa de temperatura**
- Dois inputs numéricos: Temp. mínima / Temp. máxima
- Validação: `temp_min < temp_max`
- Mensagem de erro inline se inválido

**3. Controle de temperatura (Fase 2 — desabilitado)**
- Badge "em breve" ao lado do título da seção
- Campo de setpoint desabilitado (`disabled`)
- Botões "Resfriamento" e "Aquecimento" desabilitados
- Nota: "Disponível na Fase 2 — requer CLP instalado"
- Opacidade 0.4 em toda a seção

**Comportamento:**
- Salvar chama `PATCH /api/v1/tanks/{id}/config`
- Fecha modal após salvar com sucesso
- Exibe erro inline se a requisição falhar

**Endpoint:**
```
PATCH /api/v1/tanks/{id}/config
Body: { name, temp_min, temp_max }
```

---

### `TankHistoryChart.tsx`

**Props:**
```typescript
interface TankHistoryChartProps {
  tankId: number
  tankName: string
  tempMin: number
  tempMax: number
}
```

**Responsabilidades:**
- Busca histórico quando `tankId` muda (`useTankReadings`)
- Seletor de período: 6h · 24h · 7d · 30d (estado local)
- Gráfico de linha (Recharts `LineChart`) com:
  - Eixo X: timestamps formatados conforme período selecionado
  - Eixo Y: temperatura em °C
  - Linha principal: leituras (#1D9E75)
  - `ReferenceLine` em `tempMin` (azul tracejado)
  - `ReferenceLine` em `tempMax` (vermelho tracejado)
  - Tooltip customizado com temperatura e horário
- Título exibe: "Panela N · [nome da bebida]"
- Loading state durante fetch (skeleton ou spinner)

**Hook:**
```typescript
// hooks/useTankReadings.ts
export function useTankReadings(tankId: number, period: '6h' | '24h' | '7d' | '30d') {
  // React Query — refetch quando tankId ou period muda
  return useQuery({
    queryKey: ['readings', tankId, period],
    queryFn: () => readingsService.getByTank(tankId, period),
  })
}
```

**Endpoint:**
```
GET /api/v1/tanks/{id}/readings?period=6h
```

---

### `AlertPanel.tsx`

**Props:** `alerts: Alert[]`, `onAcknowledge: (alertId: number) => void`

**Responsabilidades:**
- Lista alertas ativos ordenados por `fired_at` desc
- Cada item exibe: ícone (acima/abaixo), nome da panela + bebida, temperatura, tempo relativo
- Botão "Reconhecer" em cada item — chama `PATCH /api/v1/alerts/{id}/acknowledge`
- Se sem alertas: estado vazio com ícone de check verde

**Endpoint:**
```
PATCH /api/v1/alerts/{id}/acknowledge
```

---

## Hooks

---

### `useTanks.ts`

```typescript
export function useTanks() {
  // React Query com refetch a cada 30s como fallback
  // Temperatura em tempo real vem pelo useWebSocket
  return useQuery({
    queryKey: ['tanks'],
    queryFn: tanksService.getAll,
    refetchInterval: 30_000,
  })
}
```

**Endpoint:** `GET /api/v1/tanks`

---

### `useWebSocket.ts`

```typescript
export function useWebSocket(tankId: number, onReading: (reading: Reading) => void) {
  // Conecta em WS /ws/tanks/{id}
  // Reconecta automaticamente com backoff exponencial (1s, 2s, 4s, max 30s)
  // Chama onReading a cada mensagem recebida
  // Desconecta no cleanup do useEffect
}
```

**Uso no Dashboard:**
- Um `useWebSocket` por panela (8 conexões simultâneas)
- Cada leitura recebida atualiza o estado local do `TankCard` correspondente via `queryClient.setQueryData`

---

### `useAlerts.ts`

```typescript
export function useAlerts() {
  // React Query — refetch a cada 10s
  // Novos alertas também chegam via WebSocket (broadcast global)
  return useQuery({
    queryKey: ['alerts'],
    queryFn: alertsService.getActive,
    refetchInterval: 10_000,
  })
}
```

**Endpoint:** `GET /api/v1/alerts?status=active`

---

## Services

```typescript
// services/api.ts — instância Axios centralizada
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 10_000,
})
// Interceptor: adiciona Authorization header se token presente
// Interceptor: em 401, redireciona para /login

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
}

// services/alerts.ts
export const alertsService = {
  getActive: () => api.get<Alert[]>('/api/v1/alerts', { params: { status: 'active' } }).then(r => r.data),
  acknowledge: (id: number) => api.patch(`/api/v1/alerts/${id}/acknowledge`).then(r => r.data),
}
```

---

## Utilitários

```typescript
// utils/formatTemp.ts
export const formatTemp = (temp: number | null): string =>
  temp === null ? '—' : `${temp.toFixed(1)}°C`

// utils/formatDateTime.ts
export const formatRelative = (iso: string): string => {
  // "há 5 min", "há 2h", "há 3 dias"
}
export const formatChartLabel = (iso: string, period: string): string => {
  // "14:30", "seg 14:30", "01/05"
}

// utils/getTankStatus.ts — ver TankCard acima
```

---

## Fluxo de dados — tempo real

```
WebSocket /ws/tanks/{1..8}
    ↓ mensagem: { tank_id, temperature, recorded_at }
useWebSocket (8 instâncias)
    ↓ onReading callback
queryClient.setQueryData(['tanks'])
    ↓ atualiza current_temperature do tank correspondente
TankCard re-renderiza com nova temperatura
    ↓ se tankId === selectedTankId
TankHistoryChart recebe nova leitura via queryClient.setQueryData(['readings', tankId, period])
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
- **Panela sem nome:** exibe "—" no lugar do nome; placeholder no modal sugere adicionar
- **Offline:** dot cinza + temperatura exibe "—" + pill "Offline" + card sem borda colorida
- **Múltiplos alertas:** AlertPanel mostra todos; badge no TopBar soma o total
- **Modal aberto:** fundo com overlay escurecido; fecha ao clicar fora ou em "Cancelar"
- **Erro de rede:** `ErrorBanner` no topo da página com mensagem e botão de retry