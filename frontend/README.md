# Frontend — EH Brewing Dashboard

Dashboard React para monitoramento em tempo real de temperatura das panelas de fermentação. Interface com WebSocket para atualização ao vivo, gráficos históricos, sistema de alertas e gestão de lotes.

---

## Sumário

- [Stack Tecnológico](#stack-tecnológico)
- [Estrutura de Pastas](#estrutura-de-pastas)
- [Como Rodar Localmente](#como-rodar-localmente)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Páginas](#páginas)
- [Componentes](#componentes)
- [Hooks Customizados](#hooks-customizados)
- [Serviços (API Client)](#serviços-api-client)
- [Gerenciamento de Estado](#gerenciamento-de-estado)
- [Tipagem TypeScript](#tipagem-typescript)

---

## Stack Tecnológico

| Tecnologia | Versão | Função |
|---|---|---|
| React | 19.2.6 | Biblioteca de UI |
| TypeScript | ~5.8 | Tipagem estática |
| Vite | ^6.3 | Bundler e dev server |
| React Router DOM | 7.15.1 | Roteamento SPA |
| TanStack React Query | 5.100.13 | Cache e fetching de dados |
| Axios | 1.16.1 | Cliente HTTP |
| Recharts | 3.8.1 | Gráficos de série temporal |
| Tailwind CSS | ^4.1 | Estilização utilitária |
| ESLint | ^9.25 | Linting TypeScript/React |

---

## Estrutura de Pastas

```
frontend/src/
├── main.tsx                    # Entry point — monta React no DOM
├── App.tsx                     # Componente raiz, define rotas
├── index.css                   # Estilos globais (Tailwind base)
│
├── pages/                      # Componentes de página completa
│   ├── Login.tsx               # Tela de login
│   ├── Dashboard.tsx           # Tela principal com cards das panelas
│   ├── AlertasPage.tsx         # Histórico e gestão de alertas
│   ├── HistoricoPage.tsx       # Gráficos históricos multi-panela
│   ├── BatchesPage.tsx         # Gestão de lotes de produção
│   └── ConfigPage.tsx          # Configurações (panelas, usuários, leveduras)
│
├── components/                 # Componentes reutilizáveis por domínio
│   ├── alerts/
│   │   └── AlertPanel.tsx      # Painel lateral de alertas ativos
│   ├── auth/
│   │   └── ProtectedRoute.tsx  # Guard de rota autenticada
│   ├── base/
│   │   ├── ErrorBanner.tsx     # Banner de erro genérico
│   │   └── LoadingSkeleton.tsx # Skeleton de carregamento
│   ├── batches/
│   │   └── BatchDetailModal.tsx # Modal de detalhes de lote
│   ├── chart/
│   │   ├── TankHistoryChart.tsx      # Gráfico de uma panela
│   │   └── MultiTankHistoryChart.tsx # Gráfico comparativo multi-panela
│   ├── control/
│   │   └── ETADisplay.tsx      # Display de estimativa de tempo
│   ├── layout/
│   │   ├── TopBar.tsx          # Barra superior (logo, notificações, usuário)
│   │   └── AlertBadge.tsx      # Badge de contagem de alertas
│   └── tanks/
│       ├── TankCard.tsx        # Card individual de panela
│       ├── TankConfigModal.tsx # Modal de configuração de panela
│       ├── TankGrid.tsx        # Grid com os 8 cards de panelas
│       └── TempBar.tsx         # Barra visual de temperatura (min/max/atual)
│
├── hooks/                      # Custom React hooks
│   ├── useWebSocket.ts         # WebSocket de uma panela específica
│   ├── useGenericWebSocket.ts  # WebSocket genérico reutilizável
│   ├── useTanks.ts             # CRUD e polling de panelas
│   ├── useTankReadings.ts      # Histórico de leituras por período
│   ├── useAlerts.ts            # Listagem e reconhecimento de alertas
│   └── useTankControl.ts       # Controle de aquecimento/resfriamento
│
├── services/                   # Funções de acesso à API (Axios)
│   ├── api.ts                  # Instância Axios com interceptors
│   ├── auth.ts                 # login, refresh, logout
│   ├── tanks.ts                # listagem e configuração de panelas
│   ├── readings.ts             # envio e histórico de leituras
│   ├── alerts.ts               # listagem e acknowledge de alertas
│   ├── batches.ts              # CRUD de lotes e eventos
│   ├── control.ts              # controle de panelas
│   └── users.ts                # CRUD de usuários
│
├── context/
│   └── AuthContext.tsx         # Context de autenticação (token, user, login/logout)
│
├── types/
│   └── index.ts                # Tipos TypeScript globais (Tank, Alert, Batch, etc.)
│
└── utils/
    ├── formatDateTime.ts       # Formata datas para exibição
    ├── formatTemp.ts           # Formata temperatura com casas decimais
    └── getTankStatus.ts        # Determina status da panela (ok/alerta/offline)
```

---

## Como Rodar Localmente

O frontend não roda via Docker — é executado diretamente com Node.js.

### Pré-requisitos

- Node.js 20+
- npm

### 1. Instalar dependências

```bash
cd frontend
npm install
```

### 2. Configurar variáveis de ambiente

Copie o arquivo de exemplo e ajuste se necessário:

```bash
cp .env.example .env
```

O `.env` padrão aponta para a API rodando localmente via Docker:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_WS_RECONNECT_MAX_MS=30000
```

### 3. Iniciar o servidor de desenvolvimento

```bash
npm run dev
```

O dashboard estará disponível em: **http://localhost:5173**

> A API precisa estar rodando (`docker compose up`) antes de acessar o dashboard.

### Outros comandos

```bash
# Build de produção
npm run build

# Preview do build de produção localmente
npm run preview

# Lint
npm run lint
```

---

## Variáveis de Ambiente

| Variável | Valor padrão | Descrição |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | URL base da API REST |
| `VITE_WS_URL` | `ws://localhost:8000` | URL base para conexões WebSocket |
| `VITE_WS_RECONNECT_MAX_MS` | `30000` | Tempo máximo de espera para reconexão WS (ms) |

---

## Páginas

### Login (`/`)
Tela de autenticação. Valida credenciais via `POST /auth/login` e armazena tokens no `AuthContext`. Redireciona para o Dashboard após login bem-sucedido.

### Dashboard (`/dashboard`)
Tela principal. Exibe o `TankGrid` com os 8 cards de panelas atualizados em tempo real via WebSocket. Inclui o `AlertPanel` lateral com alertas ativos. Cada card mostra temperatura atual, status (ok/alerta/offline) e faixa configurada.

### Alertas (`/alertas`)
Lista todos os alertas com filtros por status (`active`, `resolved`). Permite reconhecer alertas ativos. Exibe panela, temperatura que disparou, horário e status.

### Histórico (`/historico`)
Gráficos de série temporal com seleção de período (`6h`, `24h`, `7d`, `30d`). Suporta visualização de uma ou múltiplas panelas simultaneamente usando Recharts.

### Lotes (`/lotes`)
Gestão completa do ciclo de vida dos lotes: criar, ativar, adicionar eventos (medições de densidade, temperatura de pitching), concluir e exportar em CSV. Exibe ABV calculado automaticamente.

### Configurações (`/config`)
Painel administrativo (visível apenas para `admin`). Permite:
- Editar nome e faixa de temperatura das panelas
- Gerenciar usuários (criar, editar roles)
- Criar e editar perfis de levedura

---

## Componentes

### `TankCard`
Card individual de cada panela. Recebe os dados da panela e exibe:
- Nome e status visual (ícone colorido)
- Temperatura atual em destaque
- `TempBar` com indicador visual da posição dentro da faixa
- Timestamp da última leitura

Conecta-se ao WebSocket da panela via `useWebSocket` e atualiza sem re-render completo da página.

### `TankGrid`
Container que renderiza os 8 `TankCard`s em grid responsivo (4 colunas no desktop, 2 no tablet, 1 no mobile).

### `AlertPanel`
Painel lateral colapsável com alertas ativos. Badge no `TopBar` exibe a contagem. Cada item tem botão "Reconhecer" que chama `PATCH /api/v1/alerts/{id}/acknowledge`.

### `TankHistoryChart`
Gráfico de linha único usando Recharts. Exibe temperatura ao longo do tempo com linhas de referência `temp_min` e `temp_max` da panela. Responsivo.

### `MultiTankHistoryChart`
Versão do gráfico com múltiplas séries, uma cor por panela. Permite comparar temperaturas de diferentes panelas no mesmo período.

### `TempBar`
Barra horizontal visual que mostra a posição da temperatura atual dentro da faixa (min/max). Muda de cor conforme o status: verde (ok), amarelo (perto do limite), vermelho (fora do limite).

### `ProtectedRoute`
HOC de rota que verifica se o usuário está autenticado. Redireciona para `/` (login) se não houver token válido no contexto.

### `TopBar`
Barra superior com logo, nome do usuário logado, badge de alertas e botão de logout.

---

## Hooks Customizados

### `useWebSocket(tankId)`
Abre uma conexão WebSocket para `ws://localhost:8000/ws/tanks/{tankId}` com o JWT no header. Retorna a última mensagem recebida e o status da conexão. Implementa reconexão automática com backoff exponencial até `VITE_WS_RECONNECT_MAX_MS`.

### `useGenericWebSocket(url)`
Versão genérica de `useWebSocket` para outros endpoints WebSocket. Base reutilizável usada por hooks mais específicos.

### `useTanks()`
Busca a lista de panelas via `GET /api/v1/tanks` com React Query. Configura polling automático para manter dados atualizados como fallback ao WebSocket.

### `useTankReadings(tankId, period)`
Busca o histórico de leituras de uma panela. Refetch automático ao mudar o período (`6h`, `24h`, `7d`, `30d`).

### `useAlerts()`
Busca alertas ativos e expõe a função `acknowledge(alertId)` que chama o endpoint de reconhecimento e invalida o cache React Query automaticamente.

### `useTankControl(tankId)`
Hook para as funcionalidades de controle ativo (Roadmap V4). Encapsula as chamadas ao endpoint de controle de aquecimento/resfriamento.

---

## Serviços (API Client)

Todos os serviços usam uma instância Axios centralizada (`services/api.ts`) que:
- Define `baseURL` a partir de `VITE_API_URL`
- Adiciona automaticamente o header `Authorization: Bearer <token>` em todas as requisições (interceptor de request)
- Intercepta respostas `401` e tenta renovar o token via `POST /auth/refresh` antes de rejeitar (interceptor de response)
- Se o refresh falhar, redireciona para o login

Exemplo de uso de um serviço:

```typescript
// services/tanks.ts
import api from './api'
import { Tank } from '../types'

export const getTanks = (): Promise<Tank[]> =>
  api.get('/api/v1/tanks').then(r => r.data)

export const updateTankConfig = (id: number, data: Partial<Tank>): Promise<Tank> =>
  api.patch(`/api/v1/tanks/${id}/config`, data).then(r => r.data)
```

---

## Gerenciamento de Estado

O projeto usa três camadas de estado:

| Camada | Ferramenta | O que gerencia |
|---|---|---|
| Estado do servidor | React Query | Dados da API (tanks, alerts, batches) — cache, refetch, loading/error |
| Estado em tempo real | WebSocket + useState | Temperatura ao vivo (atualiza o TankCard sem React Query) |
| Estado global | React Context | Autenticação (token JWT, dados do usuário, funções login/logout) |

Não há Redux nem Zustand — o escopo do estado não justifica.

---

## Tipagem TypeScript

Todos os tipos principais estão centralizados em `src/types/index.ts`:

```typescript
type Tank = {
  id: number
  name: string
  temp_min: number
  temp_max: number
  current_temperature: number | null
  last_reading_at: string | null
}

type Alert = {
  id: number
  tank_id: number
  temperature: number
  fired_at: string
  resolved_at: string | null
  acknowledged: boolean
}

type Batch = {
  id: number
  name: string
  style: string
  status: 'planned' | 'active' | 'completed' | 'cancelled'
  original_gravity: number | null
  final_gravity: number | null
  abv: number | null
  events: BatchEvent[]
}
```

Os tipos espelham os schemas Pydantic do backend, garantindo contrato entre frontend e API.
