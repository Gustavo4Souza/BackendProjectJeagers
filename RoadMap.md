# EH Brewing — Roadmap

> Plataforma de monitoramento de temperatura para 8 panelas de bebidas.
> Stack: PostgreSQL + TimescaleDB + FastAPI + Redis + React (SPA).
> Sem controle ativo na Fase 1 — somente leitura e monitoramento.

---

## Decisões de Arquitetura

- **Backend:** Python 3.11 + FastAPI, porta 8000
- **ORM:** SQLAlchemy 2.x (async) + Alembic para migrations
- **Banco:** PostgreSQL + TimescaleDB (hypertable para série temporal)
- **Cache / Pub-Sub:** Redis
- **Tempo real:** WebSocket (FastAPI + Redis Pub/Sub)
- **Frontend:** React + Vite + TypeScript, porta 5173
- **Gráficos:** Recharts
- **HTTP Client:** Axios
- **Estado de servidor:** React Query
- **Autenticação:** JWT + roles (admin / operator / viewer)
- **Simulador de CLP:** script Python que envia leituras das 8 panelas via HTTP POST
- **Hardware real (produção futura):** CLP central lendo PT100 de cada panela → HTTP para API

---

## Decisões de UI

- **Uma tela principal (Painel)** — concentra cards, gráfico e alertas
- **Card selecionado** — clicar em uma panela atualiza o gráfico de histórico no rodapé
- **Modal de configuração** — abre ao clicar na engrenagem de cada card
- **Controle de temperatura** presente no modal mas desabilitado (Fase 2)

---

## Versões e Fases

---

### V1 — Backend: Base da API

**Objetivo:** API funcional recebendo leituras do simulador, persistindo no banco e distribuindo via WebSocket.

---

#### Fase 1 — Setup e Schema do Banco

- [X] Setup Python + FastAPI + CORS + dotenv (pydantic-settings)
- [X] Configurar SQLAlchemy async + PostgreSQL + TimescaleDB
- [X] Schema completo: `tanks`, `readings`, `alerts`, `users`
- [X] Hypertable TimescaleDB na tabela `readings` (particionada por `recorded_at`)
- [X] Migrations com Alembic: init → hypertable → constraints
- [X] Docker Compose funcional: FastAPI + PostgreSQL/TimescaleDB + Redis
- [X] Error handler middleware centralizado
- [X] Health check: `GET /health` retorna status 200 com versão

**Entregável:** banco criado, migrations rodando, Docker Compose sobe sem erro.

---

#### Fase 2 — Simulador de CLP

- [X] Script `simulator/clp_simulator.py` simulando 8 panelas
- [X] Temperatura realista por panela: setpoint configurável + ruído gaussiano
- [X] Envio de `POST /api/v1/readings` a cada N segundos (padrão: 5s)
- [X] Modo de injeção de falhas: `--fault-tank 3 --fault-temp 28.0`
- [X] Parâmetros via CLI: `--api-url`, `--interval`, `--fault-tank`, `--fault-temp`
- [X] Reconexão automática se API estiver indisponível

**Entregável:** simulador rodando e gravando leituras das 8 panelas no banco em tempo real.

---

#### Fase 3 — Leituras e Tanques

- [X] `POST /api/v1/readings` — recebe leitura do CLP/simulador com validação Pydantic
- [X] `GET /api/v1/tanks` — lista as 8 panelas com `current_temperature` e `last_reading_at`
- [X] `GET /api/v1/tanks/{id}/readings?period=6h|24h|7d|30d` — histórico paginado
- [X] `GET /api/v1/tanks/{id}/status` — temperatura atual + alertas ativos da panela
- [X] `PATCH /api/v1/tanks/{id}/config` — atualiza `name`, `temp_min` e `temp_max`
- [X] Seed inicial: cadastro das 8 panelas com número, localização e faixas padrão

**Entregável:** CRUD de leituras e tanques funcionando, seed populando as 8 panelas.

---

#### Fase 4 — Alertas

- [X] Motor de alertas: verifica faixa configurada a cada leitura recebida
- [X] `GET /api/v1/alerts?status=active` — lista alertas ativos
- [X] `PATCH /api/v1/alerts/{id}/acknowledge` — marca alerta como reconhecido
- [X] Persistência na tabela `alerts` com `fired_at` e `resolved_at`
- [X] Resolução automática quando temperatura volta à faixa normal

**Entregável:** alertas disparando, persistindo e sendo reconhecidos corretamente.

---

#### Fase 5 — Tempo Real (WebSocket)

- [X] Redis Pub/Sub: backend publica cada leitura no canal da panela (`tanks:{id}:readings`)
- [X] `WS /ws/tanks/{id}` — stream de leituras em tempo real por panela
- [X] Broadcast de alertas disparados via WebSocket — canal `alerts:events`, endpoint `WS /ws/alerts`
- [X] Suporte a múltiplas conexões WebSocket simultâneas — implementado via `FermenterWebSocketHub`

**Entregável:** leituras e alertas chegando ao frontend em tempo real sem polling.

---

#### Fase 6 — Autenticação

- [X] Tabela `users` com roles: admin / operador / viewer
- [X] Tabela `refresh_tokens` com revogação por JTI (além do escopo original)
- [X] `POST /auth/login` — retorna access token + refresh token (JWT)
- [X] `POST /auth/refresh` — renova access token com rotação de refresh token
- [X] `POST /auth/logout` — revoga refresh token (além do escopo original)
- [X] Middleware HTTP protegendo todas as rotas (exceto `/health`, `/docs`, `/login`, `/register`, `/auth/*`)
- [X] Permissões por role via `require_roles()`: viewer só lê, operador cria leituras/lotes, admin configura tudo
- [X] Seed de usuário admin padrão para primeiro acesso — `scripts/seed_tanks.py --admin-password <senha>`

**Entregável:** todas as rotas protegidas, login funcionando com refresh token.

---

### V2 — Frontend: Painel de Monitoramento

**Objetivo:** dashboard de tela única com monitoramento em tempo real das 8 panelas.
**Referência completa:** ver `FRONTEND.md`

---

#### Fase 1 — Setup e Infraestrutura

- [ ] Setup React + Vite + TypeScript + Tailwind CSS
- [ ] Instância Axios centralizada em `services/api.ts` com interceptors de auth
- [ ] Services tipados: `tanks.ts`, `readings.ts`, `alerts.ts`
- [ ] React Query configurado: `QueryClient` com defaults de retry e stale time
- [ ] Tipos globais em `types/index.ts`: `Tank`, `Reading`, `Alert`, `TankStatus`
- [ ] Utilitários: `formatTemp`, `formatDateTime`, `formatRelative`, `getTankStatus`
- [ ] Componentes base: `ErrorBanner`, `LoadingSkeleton`
- [ ] Variáveis de ambiente: `VITE_API_URL`, `VITE_WS_URL`

**Entregável:** app compila, Axios conecta na API, tipos definidos.

---

#### Fase 2 — Hook de WebSocket

- [ ] `useWebSocket(tankId, onReading)` — conecta em `WS /ws/tanks/{id}`
- [ ] Reconexão automática com backoff exponencial (1s → 2s → 4s → máx 30s)
- [ ] Desconecta no cleanup do `useEffect`
- [ ] `onReading` atualiza `queryClient.setQueryData(['tanks'])` com nova temperatura

**Entregável:** temperatura de cada panela atualizando em tempo real no estado do React Query.

---

#### Fase 3 — Cards das 8 Panelas

- [ ] `TankGrid.tsx` — grid 4×2 responsivo
- [ ] `TankCard.tsx` — número da panela (discreto) + nome da bebida + temperatura atual
- [ ] `TempBar.tsx` — barra colorida mostrando posição da temperatura na faixa
- [ ] Semáforo visual: verde / amarelo / vermelho / cinza (offline) com dot e borda
- [ ] Card selecionado: `outline: 2px solid #1D9E75`
- [ ] `onSelect` ao clicar no card — atualiza `selectedTankId` no Dashboard
- [ ] Ícone de engrenagem no topo direito — abre modal de configuração
- [ ] Estado offline: dot cinza + temperatura "—" + pill "Offline" se sem leitura há 30s+

**Entregável:** 8 cards renderizando com temperatura ao vivo e semáforo correto.

---

#### Fase 4 — Gráfico de Histórico

- [ ] `TankHistoryChart.tsx` — Recharts `LineChart` com dados da panela selecionada
- [ ] Título dinâmico: "Panela N · [nome da bebida]"
- [ ] Seletor de período: 6h · 24h · 7d · 30d (estado local do componente)
- [ ] `ReferenceLine` tracejada em `temp_min` (azul) e `temp_max` (vermelho)
- [ ] Tooltip customizado com temperatura e horário formatado
- [ ] Gráfico recarrega quando `selectedTankId` muda
- [ ] Loading skeleton enquanto faz fetch

**Entregável:** clicar em um card atualiza o gráfico para aquela panela com histórico correto.

---

#### Fase 5 — Painel de Alertas e Modal

- [ ] `AlertPanel.tsx` — lista de alertas ativos com botão "Reconhecer" por item
- [ ] Badge no `TopBar` com contagem de alertas ativos
- [ ] Alertas chegam em tempo real via WebSocket (broadcast global)
- [ ] `TankConfigModal.tsx` — editar nome da bebida, `temp_min` e `temp_max`
- [ ] Validação inline no modal: `temp_min < temp_max`
- [ ] Seção de controle (Fase 2) presente no modal, opacidade 0.4, `disabled`, badge "em breve"
- [ ] Salvar chama `PATCH /api/v1/tanks/{id}/config` e fecha modal

**Entregável:** alertas reconhecíveis em tempo real + modal de configuração funcionando.

---

#### Fase 6 — Autenticação no Frontend

- [ ] Página de login com JWT — redireciona para Painel após autenticação
- [ ] Proteção de rotas: redireciona para `/login` se sem token
- [ ] Interceptor Axios: `Authorization: Bearer <token>` em todas as requisições
- [ ] Interceptor Axios: em 401, limpa token e redireciona para `/login`
- [ ] Refresh token automático antes de expirar

**Entregável:** login funcionando, rotas protegidas, token renovado automaticamente.

---

### V3 — Qualidade e Deploy

**Objetivo:** sistema estável em produção com URL pública, pronto para apresentação.

---

#### Fase 1 — Testes e Qualidade

- [ ] Testes unitários no backend: cobertura mínima 60% por módulo (pytest + pytest-cov)
- [ ] Testes de integração: simulador → API → banco → WebSocket
- [ ] Lint sem erros: Ruff (Python) + ESLint + Prettier (TypeScript/React)
- [ ] Testes de carga com k6: 8 conexões WebSocket simultâneas estáveis

**Entregável:** pipeline de qualidade verde, cobertura ≥ 60%.

---

#### Fase 2 — CI/CD e Deploy

- [ ] GitHub Actions: lint → testes → build → deploy no merge para `main`
- [ ] Deploy do backend no Railway ou Render (banco gerenciado em nuvem)
- [ ] Deploy do frontend na Vercel com preview por branch
- [ ] Variáveis de ambiente via secrets — nenhum secret commitado no repositório
- [ ] HTTPS com certificado SSL automático nas plataformas cloud
- [ ] Simulador apontando para o endpoint de produção

---

#### Fase 3 — Documentação e Apresentação

- [ ] README completo com diagrama de arquitetura e guia de setup local
- [ ] Guia de onboarding: como rodar com Docker Compose em 3 comandos
- [ ] Slides de apresentação com demo ao vivo do sistema em produção

**Entregável:** sistema acessível via URL pública — pronto para apresentação final.

---

## Roadmap Futuro — V4 Controle Ativo

> Dependente de verificação do modelo N321 instalado (com ou sem RS485) e aprovação da cervejaria.

- [ ] Se N321 **com RS485**: CLP lê temperatura E escreve setpoint via Modbus RTU → sem hardware adicional
- [ ] Se N321 **sem RS485**: CLP aciona relé externo em paralelo para controle ON/OFF
- [ ] `POST /api/v1/tanks/{id}/control` — ligar/desligar aquecimento e resfriamento
- [ ] Lógica de segurança: timeout de software aciona failsafe no N321
- [ ] Logs de auditoria: quem ligou/desligou e quando
- [ ] Habilitar seção de controle no modal: remover `disabled` e badge "em breve"