# EH Brewing — Documentação Técnica

> Plataforma de monitoramento e controle de temperatura para panelas de bebidas
> Projeto Integrador · 7°/8° Período · 2025/2026
> Versão 0.2.0

---

## 1. Visão Geral

A EH Brewing opera 8 panelas de armazenamento de bebidas prontas para fermentação. Hoje o controle de temperatura é feito localmente por controladores N321-NTC (Novus) instalados em cada panela — sem integração entre os equipamentos, sem histórico centralizado e sem visibilidade remota.

Este projeto entrega uma plataforma IoT que:

- Lê a temperatura de todas as 8 panelas em tempo real via CLP central
- Disponibiliza os dados via dashboard web com 4 telas (Painel, Histórico, Alertas, Config)
- Armazena histórico completo para rastreabilidade
- Dispara alertas quando temperaturas saem da faixa configurada
- Permite ao operador definir um setpoint por panela e acionar aquecimento ou resfriamento remotamente (Fase 2)
- Estima o tempo necessário para a temperatura atingir o setpoint desejado
- Rastreia lotes de fermentação com perfis de levedura e linha do tempo de eventos

### Contexto de entrega

O projeto é desenvolvido em ambiente local. A apresentação ao cliente será feita via Docker Compose na máquina do desenvolvedor. O CLP físico é simulado via script Python. Deploy em produção será avaliado após aprovação do cliente.

---

## 2. Arquitetura

```
[Panelas 1–8]
    ↓ Sensor NTC (paralelo ao N321 existente)
[CLP Central]
    ↓ HTTP POST / TCP-IP
    ↑ HTTP GET (consulta setpoint — Fase 2)
[Backend FastAPI]
    ↓ Persiste + publica via Redis Pub/Sub
[PostgreSQL + TimescaleDB]
    ↓ WebSocket
[Dashboard React — 4 telas]
```

### Componentes

| Componente | Tecnologia | Papel |
|---|---|---|
| Simulador de CLP | Python script | Gera leituras e responde a setpoints de controle |
| Backend | Python 3.12 + FastAPI | Recebe, valida, persiste e distribui leituras e comandos |
| Banco de dados | PostgreSQL + TimescaleDB | Série temporal de temperaturas e dados de lotes |
| Cache / Pub-Sub | Redis | Distribui leituras e eventos em tempo real |
| Frontend | React + Vite + TypeScript | Dashboard com 4 telas |
| Containerização | Docker + Docker Compose | Ambiente unificado para desenvolvimento e apresentação |

---

## 3. Hardware (Referência de Produção)

### Controlador existente por panela

**Novus N321-NTC** — controlador ON/OFF standalone com saída a relé (10A/16A). O sensor NTC é lido em paralelo pelo CLP; o N321 permanece intacto como segurança local.

### Arquitetura proposta para controle (Fase 2 em produção)

- **CLP central** com entradas analógicas NTC (8 canais) e saídas digitais para relé por panela
- Comunicação via Ethernet/TCP-IP
- Protocolo: HTTP POST para leituras + HTTP GET para consultar setpoints
- Controle ON/OFF: relé aciona aquecimento ou resfriamento conforme setpoint definido no dashboard
- O N321 permanece como failsafe local caso o software falhe

---

## 4. Fases de Entrega

### Fase 1 — Monitoramento ✅ Concluído

- Leitura de temperatura das 8 panelas em tempo real
- Dashboard com cards de status, gráfico histórico por panela
- Sistema de alertas: temperatura fora da faixa configurada
- Simulador de CLP

### Fase 2 — Controle Ativo 🔲 Em desenvolvimento

- Definição de setpoint de temperatura por panela via dashboard
- Acionamento de aquecimento ou resfriamento (relé ON/OFF)
- Simulador responde ao setpoint definido pelo usuário
- Estimativa de tempo para atingir a temperatura alvo (ETA)
- Pill de estado no card: "Resfriando ↓" / "Aquecendo ↑"

### Fase 3 — Telas Complementares 🔲 Pendente

- Tela Histórico: gráfico de múltiplas panelas simultâneas
- Tela Alertas: lista completa com filtros
- Tela Config: gestão de usuários e configuração em lote das panelas

### Fase 4 — Lotes e Leveduras 🔲 Pendente

- Rastreamento de lotes de fermentação associados às panelas
- Perfis de levedura com faixa de temperatura e atenuação
- Linha do tempo de eventos por lote (pitch, dry hop, cold crash…)
- Cálculo automático de ABV e atenuação aparente
- Exportação de lote em CSV

---

## 5. Stack Técnica

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Backend | Python 3.12 + FastAPI | Async nativo, ótimo para WebSocket e alta frequência de leituras |
| Banco | PostgreSQL + TimescaleDB | Consultas de série temporal 10–100× mais rápidas |
| Cache / Pub-Sub | Redis | Distribui leituras entre workers sem polling |
| Tempo real | WebSocket (FastAPI) | Atualização sem reload de página |
| Frontend | React + Vite + TypeScript | Componentização, tipagem, reatividade |
| Roteamento | React Router v6 | Navegação entre as 4 telas sem reload |
| Gráficos | Recharts | Biblioteca React-native para séries temporais |
| Estilização | Tailwind CSS | Utilitário, sem CSS customizado |
| Autenticação | JWT + OAuth2 (FastAPI) | Proteção de rotas e controle de acesso por role |
| Containerização | Docker + Docker Compose | Ambiente idêntico entre todos os membros do time |

---

## 6. Modelo de Dados

### Tabelas principais

```sql
-- Panelas cadastradas
CREATE TABLE tanks (
  id          SERIAL PRIMARY KEY,
  name        VARCHAR(100) NOT NULL,
  location    VARCHAR(100),
  temp_min    FLOAT NOT NULL,
  temp_max    FLOAT NOT NULL,
  status      VARCHAR(20) DEFAULT 'active'
);

-- Leituras de temperatura (hypertable TimescaleDB)
CREATE TABLE readings (
  id          BIGSERIAL,
  tank_id     INT REFERENCES tanks(id),
  temperature FLOAT NOT NULL,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
SELECT create_hypertable('readings', 'recorded_at');

-- Estado de controle por panela (Fase 2)
CREATE TABLE tank_control (
  id          SERIAL PRIMARY KEY,
  tank_id     INT REFERENCES tanks(id) UNIQUE,
  setpoint    FLOAT NOT NULL,
  mode        VARCHAR(20) DEFAULT 'idle',  -- cooling | heating | idle
  updated_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_by  INT REFERENCES users(id)
);

-- Alertas disparados
CREATE TABLE alerts (
  id              SERIAL PRIMARY KEY,
  tank_id         INT REFERENCES tanks(id),
  temperature     FLOAT NOT NULL,
  fired_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at     TIMESTAMPTZ,
  acknowledged_by INT REFERENCES users(id)
);

-- Usuários do sistema
CREATE TABLE users (
  id              SERIAL PRIMARY KEY,
  username        VARCHAR(100) UNIQUE NOT NULL,
  hashed_password TEXT NOT NULL,
  role            VARCHAR(20) DEFAULT 'viewer',
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Perfis de levedura
CREATE TABLE yeast_profiles (
  id                  SERIAL PRIMARY KEY,
  name                VARCHAR(100) UNIQUE NOT NULL,
  strain              VARCHAR(100),
  attenuation_min     FLOAT,
  attenuation_max     FLOAT,
  temperature_min_c   FLOAT,
  temperature_max_c   FLOAT,
  notes               TEXT,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Lotes de fermentação
CREATE TABLE batches (
  id                SERIAL PRIMARY KEY,
  name              VARCHAR(100) NOT NULL,
  style             VARCHAR(100),
  status            VARCHAR(20) DEFAULT 'planned',
  fermenter_id      INT REFERENCES tanks(id),
  original_gravity  FLOAT,
  final_gravity     FLOAT,
  volume_liters     FLOAT,
  started_at        TIMESTAMPTZ,
  ended_at          TIMESTAMPTZ,
  yeast_profile_id  INT REFERENCES yeast_profiles(id),
  notes             TEXT,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Eventos de lote
CREATE TABLE batch_events (
  id           SERIAL PRIMARY KEY,
  batch_id     INT REFERENCES batches(id) ON DELETE CASCADE,
  event_type   VARCHAR(50),
  description  TEXT,
  value        FLOAT,
  unit         VARCHAR(20),
  occurred_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 7. Endpoints da API

### Autenticação

| Método | Rota | Descrição |
|---|---|---|
| POST | `/register` | Cria usuário |
| POST | `/auth/login` | Login — retorna access + refresh token |
| POST | `/auth/refresh` | Renova token |
| POST | `/auth/logout` | Revoga refresh token |

### Core

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/v1/readings` | Recebe leitura do CLP/simulador |
| GET | `/api/v1/tanks` | Lista panelas com temperatura atual |
| GET | `/api/v1/tanks/{id}/readings` | Histórico (`?period=6h\|24h\|7d\|30d`) |
| GET | `/api/v1/tanks/{id}/readings/export` | Exporta CSV |
| GET | `/api/v1/tanks/{id}/status` | Status atual + alertas ativos |
| PATCH | `/api/v1/tanks/{id}/config` | Atualiza nome e faixas |

### Controle (Fase 2)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/tanks/{id}/control` | Retorna setpoint e modo |
| POST | `/api/v1/tanks/{id}/control` | Define setpoint `{ "setpoint": 8.0 }` |
| GET | `/api/v1/tanks/{id}/eta` | Estimativa de tempo para atingir setpoint |

### Alertas

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/alerts` | Lista com filtros |
| PATCH | `/api/v1/alerts/{id}/acknowledge` | Reconhece alerta |
| POST | `/api/v1/alerts/acknowledge-all` | Reconhece todos os ativos |

### Usuários

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/users` | Lista usuários (admin) |
| POST | `/api/v1/users` | Cria usuário (admin) |
| PATCH | `/api/v1/users/{id}` | Atualiza role (admin) |

### Lotes e Leveduras

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/v1/batches` | Cria lote |
| GET | `/api/v1/batches` | Lista com filtros |
| GET | `/api/v1/batches/{id}` | Detalhe + ABV calculado |
| PATCH | `/api/v1/batches/{id}` | Atualiza |
| PATCH | `/api/v1/batches/{id}/events` | Adiciona evento |
| GET | `/api/v1/batches/{id}/export` | Exporta CSV |
| POST | `/api/v1/yeast_profiles` | Cria perfil |
| GET | `/api/v1/yeast_profiles` | Lista perfis |
| PATCH | `/api/v1/yeast_profiles/{id}` | Atualiza |
| DELETE | `/api/v1/yeast_profiles/{id}` | Remove |

### WebSocket

| Protocolo | Rota | Descrição |
|---|---|---|
| WS | `/ws/tanks/{id}` | Stream de leituras por panela |
| WS | `/ws/alerts` | Stream de alertas |
| WS | `/ws/control` | Stream de mudanças de setpoint (Fase 2) |

---

## 8. Fluxo de uma Leitura

```
1. CLP (ou simulador) coleta temperatura a cada N segundos
2. HTTP POST → /api/v1/readings
3. FastAPI valida + persiste na hypertable
4. Motor de alertas verifica faixa configurada
5. Se temperatura fora da faixa → cria/atualiza alerta
6. Motor de controle verifica se setpoint foi atingido (±0,3°C) → atualiza mode para idle
7. Publica no Redis Pub/Sub da panela
8. WebSocket faz broadcast ao dashboard
9. Dashboard atualiza card, gráfico, alertas e ETA em tempo real
```

## 9. Fluxo de Controle (Fase 2)

```
1. Usuário define setpoint no modal do TankCard
2. Frontend POST /api/v1/tanks/{id}/control → { "setpoint": 8.0 }
3. Backend calcula mode: cooling / heating / idle
4. Persiste em tank_control + publica no Redis "control:events"
5. Simulador consulta GET /api/v1/tanks/{id}/control a cada ciclo
6. Simulador ajusta taxa de variação de temperatura conforme mode
7. Quando temperatura atinge setpoint ±0,3°C → simulador estabiliza
8. Backend detecta temperatura ≈ setpoint → atualiza mode para idle
9. Frontend recebe atualização via WS /ws/control → pill do card muda para "Estável"
```

---

## 10. Simulador de CLP

Localizado em `simulator/clp_simulator.py`.

### Comportamento

- Simula 8 panelas com temperaturas independentes
- Modelo de primeira ordem: `temp_nova = 0,95 × temp_atual + 0,05 × setpoint_efetivo + ruído`
- Consulta `GET /api/v1/tanks/{id}/control` a cada ciclo para obter setpoint atual
- Quando `mode = cooling`: aproxima temperatura do setpoint com taxa `--cooling-rate` (padrão 0,3°C/ciclo)
- Quando `mode = heating`: idem com `--heating-rate` (padrão 0,2°C/ciclo)
- Quando `mode = idle`: deriva natural com ruído gaussiano σ=0,3°C
- Quando temperatura ≈ setpoint (±0,3°C): ruído mínimo σ=0,05°C

### Execução

```bash
python simulator/clp_simulator.py                              # modo padrão
python simulator/clp_simulator.py --fault-tank 3 --fault-temp 28.0
python simulator/clp_simulator.py --cooling-rate 0.5 --heating-rate 0.3
python simulator/clp_simulator.py --interval 10 --api-url http://localhost:8000
```

---

## 11. Definition of Done (DoD)

Uma história é **PRONTA** quando:

- Código implementado e revisado via Pull Request (ao menos 1 aprovação)
- Testes unitários escritos — cobertura mínima de 60% para o módulo
- Sem erros de lint: Ruff (Python) e ESLint + Prettier (TypeScript/React)
- Funcionalidade demonstrável via Docker Compose local
- Documentação inline atualizada

---

## 12. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Prazo apertado | Alto | Simulador desacopla do hardware; fases bem definidas |
| Divergência de ambiente | Médio | Docker Compose garante ambiente idêntico |
| Cobertura insuficiente | Médio | DoD exige 60% por módulo antes do merge |
| WebSocket com muitas conexões | Médio | Redis Pub/Sub desacopla; 8 conexões já testadas |
| Simulador não refletir hardware real | Médio | Parâmetros configuráveis via CLI; fácil ajuste após instalação |

---

*EH Brewing — Documentação v0.2.0 · Projeto Integrador 7°/8° Período · 2026*
