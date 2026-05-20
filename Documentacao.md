# EH Brewing — Documentação Técnica

> Plataforma de monitoramento de temperatura para panelas de bebidas  
> Projeto Integrador · 7°/8° Período · 2025

---

## 1. Visão Geral

A EH Brewing opera 8 panelas de armazenamento de bebidas prontas para fermentação. Hoje o controle de temperatura é feito localmente por controladores N321-NTC (Novus) instalados em cada panela — sem integração entre os equipamentos, sem histórico centralizado e sem visibilidade remota.

Este projeto entrega uma plataforma de monitoramento IoT que:
- Lê a temperatura de todas as 8 panelas em tempo real via CLP central
- Disponibiliza os dados via dashboard web responsivo
- Armazena histórico completo para rastreabilidade
- Dispara alertas quando temperaturas saem da faixa configurada

### Contexto de entrega

O projeto é desenvolvido em ambiente acadêmico. O CLP físico não será instalado durante o semestre — a integração com hardware é simulada via script Python que replica o comportamento de um CLP real enviando dados para a API.

---

## 2. Arquitetura

```
[Panelas 1–8]
    ↓ Sensor NTC (paralelo ao N321 existente)
[CLP Central]
    ↓ HTTP POST / TCP-IP (Wi-Fi ou Ethernet)
[Backend FastAPI]
    ↓ Persiste + publica via Redis Pub/Sub
[PostgreSQL + TimescaleDB]
    ↓ WebSocket
[Dashboard React]
```

### Componentes

| Componente | Tecnologia | Papel |
|---|---|---|
| Simulador de CLP | Python script | Gera leituras das 8 panelas e envia para a API |
| Backend | Python 3.11 + FastAPI | Recebe, valida, persiste e distribui as leituras |
| Banco de dados | PostgreSQL + TimescaleDB | Armazena série temporal de temperaturas |
| Cache / Pub-Sub | Redis | Distribui leituras em tempo real para WebSocket |
| Frontend | React + Vite + TypeScript | Dashboard web com atualização em tempo real |
| Containerização | Docker + Docker Compose | Ambiente unificado para desenvolvimento e produção |

---

## 3. Hardware (Referência de Produção)

### Controlador existente por panela

**Novus N321-NTC** — controlador ON/OFF standalone com saída a relé (10A/16A). Não possui interface de comunicação digital. O sistema **não interfere** no N321 — o sensor NTC é lido em paralelo pelo CLP.

### Arquitetura de hardware proposta (produção futura)

- **CLP central** com entradas analógicas para NTC (8 canais mínimo)
- Comunicação com backend via Ethernet/TCP-IP
- Protocolo: HTTP POST para `/api/v1/readings` a cada N segundos
- O N321 permanece intacto como controlador de segurança local

---

## 4. Fases de Entrega

### Fase 1 — Monitoramento (escopo do semestre)

- Leitura de temperatura das 8 panelas em tempo real
- Dashboard com cards de status por panela
- Gráfico histórico de temperatura por panela
- Sistema de alertas: temperatura fora da faixa configurada
- Simulador de CLP para desenvolvimento e testes

### Fase 2 — Controle Ativo (roadmap futuro)

- Acionamento de relé externo via CLP (ligar/desligar aquecimento e resfriamento)
- Controle de setpoint por panela via dashboard
- Lógica de segurança: N321 assume controle se o software falhar

---

## 5. Stack Técnica

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Async nativo, ótimo para WebSocket e alta frequência de leituras |
| Banco de Dados | PostgreSQL + TimescaleDB | Queries de série temporal 10–100× mais rápidas que PostgreSQL puro |
| Cache / Pub-Sub | Redis | Distribui leituras entre workers sem polling no banco |
| Tempo real | WebSocket (FastAPI) | Dashboard atualiza sem recarregar a página |
| Frontend | React + Vite + TypeScript | Componentização, tipagem e reatividade |
| Gráficos | Recharts | Biblioteca React-native para séries temporais |
| Estilização | Tailwind CSS | Utilitário, sem CSS customizado |
| Autenticação | JWT + OAuth2 (FastAPI) | Proteção de rotas e controle de acesso |
| Containerização | Docker + Docker Compose | Ambiente idêntico entre todos os membros do time |
| Deploy | Railway / Render + Vercel | Backend em nuvem gerenciada, frontend em CDN |
| CI/CD | GitHub Actions | Lint → testes → build → deploy automático |

---

## 6. Modelo de Dados

### Tabelas principais

```sql
-- Panelas cadastradas
CREATE TABLE tanks (
  id          SERIAL PRIMARY KEY,
  name        VARCHAR(100) NOT NULL,       -- "Panela 1", "Panela 2"...
  location    VARCHAR(100),
  temp_min    FLOAT NOT NULL,              -- Temperatura mínima aceitável (°C)
  temp_max    FLOAT NOT NULL,              -- Temperatura máxima aceitável (°C)
  status      VARCHAR(20) DEFAULT 'active' -- active | inactive | maintenance
);

-- Leituras de temperatura (hypertable TimescaleDB)
CREATE TABLE readings (
  id          BIGSERIAL,
  tank_id     INT REFERENCES tanks(id),
  temperature FLOAT NOT NULL,             -- Valor lido do NTC (°C)
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
SELECT create_hypertable('readings', 'recorded_at');

-- Alertas disparados
CREATE TABLE alerts (
  id           SERIAL PRIMARY KEY,
  tank_id      INT REFERENCES tanks(id),
  temperature  FLOAT NOT NULL,            -- Valor no momento do disparo
  fired_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at  TIMESTAMPTZ,
  acknowledged_by INT REFERENCES users(id)
);

-- Usuários do sistema
CREATE TABLE users (
  id              SERIAL PRIMARY KEY,
  name            VARCHAR(100) NOT NULL,
  email           VARCHAR(150) UNIQUE NOT NULL,
  role            VARCHAR(20) DEFAULT 'viewer', -- admin | operator | viewer
  hashed_password TEXT NOT NULL,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 7. Endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/v1/readings` | Recebe leitura do CLP (ou simulador) |
| `GET` | `/api/v1/tanks` | Lista todas as panelas com status atual |
| `GET` | `/api/v1/tanks/{id}/readings` | Histórico de leituras de uma panela (paginado) |
| `GET` | `/api/v1/tanks/{id}/status` | Status atual: temperatura, alertas ativos |
| `PATCH` | `/api/v1/tanks/{id}/config` | Atualiza faixa de temperatura aceitável |
| `GET` | `/api/v1/alerts` | Lista alertas com filtros |
| `PATCH` | `/api/v1/alerts/{id}/acknowledge` | Marca alerta como reconhecido |
| `WS` | `/ws/tanks/{id}` | WebSocket: stream de leituras em tempo real |
| `GET` | `/health` | Health check da API |

### Payload de leitura (CLP → API)

```json
POST /api/v1/readings
{
  "tank_id": 3,
  "temperature": 14.7,
  "recorded_at": "2025-05-15T10:30:00Z"
}
```

---

## 8. Fluxo de uma Leitura

```
1. CLP (ou simulador) coleta temperatura de cada panela a cada N segundos
2. HTTP POST → /api/v1/readings com payload JSON
3. FastAPI valida via Pydantic e persiste na hypertable TimescaleDB
4. FastAPI publica no canal Redis Pub/Sub da panela
5. WebSocket consumers assinantes fazem broadcast ao React
6. Dashboard atualiza cards e gráfico em tempo real
7. Motor de alertas verifica se a leitura viola a faixa configurada
8. Se alerta disparado → persiste na tabela alerts + badge no dashboard
```

---

## 9. Simulador de CLP

O simulador substitui o hardware durante desenvolvimento e testes. Localizado em `/simulator/clp_simulator.py`.

### Comportamento

- Simula 8 panelas com temperaturas independentes
- Cada panela tem setpoint configurável e oscilação realista (ruído gaussiano)
- Envia POST para a API a cada intervalo configurado (padrão: 5s)
- Suporta modo de injeção de falhas para testar alertas

### Execução

```bash
# Modo padrão — todas as panelas com temperatura normal
python simulator/clp_simulator.py

# Injetar falha de temperatura na panela 3
python simulator/clp_simulator.py --fault-tank 3 --fault-temp 28.0

# Configurar intervalo e endpoint
python simulator/clp_simulator.py --interval 10 --api-url http://localhost:8000
```

---

## 10. Definition of Done (DoD)

Uma história é considerada **PRONTA** somente quando:

- Código implementado e revisado via Pull Request (ao menos 1 aprovação)
- Testes unitários escritos — cobertura mínima de 60% para o módulo
- Sem erros de lint: Ruff (Python) e ESLint + Prettier (TypeScript/React)
- Funcionalidade demonstrável via Docker Compose local
- Documentação inline atualizada (docstrings, JSDoc ou README do módulo)
- Aceito pelo Product Owner na Sprint Review

---

## 11. Estrutura do Repositório

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
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/        # useWebSocket, useTanks...
│   │   ├── pages/
│   │   └── services/     # Chamadas à API
│   └── public/
├── simulator/
│   └── clp_simulator.py
├── docker-compose.yml
├── DOCUMENTACAO.md
├── ROADMAP.md
└── CLAUDE.md
```

---

## 12. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Prazo apertado no semestre | Alto | Simulador desacopla o desenvolvimento do hardware; fases bem definidas |
| Divergência de ambiente entre membros | Médio | Docker Compose garante ambiente idêntico para todos |
| Custo de cloud inesperado | Baixo | Railway/Render têm plano gratuito suficiente para o MVP |
| Cobertura de testes insuficiente | Médio | DoD exige 60% de cobertura por módulo antes do merge |
| Conflitos de merge frequentes | Baixo | Branches por feature + PR obrigatório |
| WebSocket com muitas conexões simultâneas | Médio | Redis Pub/Sub desacopla; testar com k6 no Sprint 5 |

---

*EH Brewing — Gerência de Dados · Documentação v2.0 · Projeto Integrador 7°/8° Período · 2025*