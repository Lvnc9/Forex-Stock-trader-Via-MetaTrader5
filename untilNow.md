# TradeBot progress (`untilNow`)

Handoff file for the **next agent chat**. Update at the end of every session.

## GitHub repository

| | |
| --- | --- |
| **Display name** | Forex-Stock trader Via MetaTrader5 |
| **Repo** | [github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) |
| **Remote** | `origin` → `https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git` |
| **Default branch** | `main` |

## Plan reference

- [PLAN.md](./PLAN.md)

## Current state (last updated: 2026-07-29)

| Area | Status |
| ---- | ------ |
| Phase 1 (backtest foundation) | **Done** |
| Phase 2 (strategy UX + deploy review) | **Done** |
| Phase 3 (MT5 agent + broker) | **In progress** — API + Broker UI + stub agent; live worker TBD |

## Completed this session

- **Deploy review:** `/live/deploy/` → `/live/<id>/review/` (params, last backtest link, live-account confirm)
- **Broker:** `TradingAgent` + token (hashed), `/broker/` UI, one-time token display
- **Agent API:** `POST /api/agent/heartbeat`, `POST /api/agent/sync`, `GET /api/agent/deployments` (Bearer token)
- **Live trading:** `Deployment` model (draft/armed/paused/stopped), list + pause/stop
- **Navbar:** MT5 connected + Demo/Live from agent heartbeat
- **Windows stub:** `agent/` poll client (`python -m agent` from repo root + `agent.env`)

## How to run

```bash
cd tradeBot && source venv/bin/activate
python manage.py migrate
python manage.py runserver
```

**Try agent stub (second terminal):**

```bash
# agent.env: WEBAPP_URL=http://127.0.0.1:8000  AGENT_TOKEN=<from /broker/>
pip install -r agent/requirements.txt
python -m agent
```

## URLs

| Path | Purpose |
| ---- | ------- |
| `/broker/` | Create agents, copy token |
| `/live/` | Deployments |
| `/live/deploy/` | New deployment → review |
| `/api/agent/*` | Windows agent (no session auth) |

## Last commit

- `062d213` — Phase 2–3: deploy review, broker UI, agent API, stub agent

## Next session

- **Phase 3 continuation:** `LiveWorker` on agent (bars + `SignalEngine` + MT5 orders), deployment sync UI, positions table from agent sync payload
- **Not in Django:** `MetaTrader5` import stays in `agent/` only

## Decisions / notes

- Agent tokens stored as SHA-256 hash; plain token shown once at creation.
- Online = heartbeat within `AGENT_HEARTBEAT_TTL_SECONDS` (90s default).
