# TradeBot progress (`untilNow`)

Handoff for the **next agent chat**. Read at start; update at end.

## GitHub

| | |
| --- | --- |
| **Repo** | [github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) |
| **Remote** | `origin` → `https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git` |
| **Branch** | `main` |

## Plan & workflow

- Architecture: [PLAN.md](./PLAN.md)
- Agent prompts & multi-agent playbook: [docs/WORKFLOW.md](./docs/WORKFLOW.md)
- Conventions: [AGENTS.md](./AGENTS.md)

## Phase status (2026-07-29)

| Phase | Status |
| ----- | ------ |
| 1 — Backtest foundation | **Done** |
| 2 — Strategy UX + deploy review | **Done** |
| 3 — MT5 agent + live (v1) | **Done** |
| 4 — Data & stocks breadth | **Not started** |
| Post–Phase 3 polish | Backlog in PLAN.md |

## What exists (quick map)

| Path | Role |
| ---- | ---- |
| `apps/strategies/` | `BaseStrategy`, library, custom upload, loader |
| `apps/marketdata/` | Catalog, M1 loader, `SymbolMap` (admin today) |
| `apps/backtest/` | Runner, results UI, compare (sync runs; Celery stub) |
| `apps/trading/` | Deployments, deploy review, live dashboard |
| `apps/brokers/` | Agents, token API, `/api/agent/*` |
| `agent/` | Poll client, `LiveWorker`, `mt5_adapter` (Windows + MT5) |

## Run

**Web (Mac/Linux/Windows):**

```bash
cd tradeBot && source venv/bin/activate
python manage.py migrate
python manage.py seed_library_strategies   # first time
python manage.py runserver
```

**Tests:**

```bash
python manage.py test
```

**Agent (Windows + MT5, repo root):**

```bash
pip install -r requirements.txt -r agent/requirements.txt
cp agent.env.example agent.env   # WEBAPP_URL + AGENT_TOKEN from /broker/
python -m agent
```

Mac dev: agent runs heartbeat-only without MetaTrader5.

## Key URLs

| Path | Purpose |
| ---- | ------- |
| `/strategies/` | Parameters, custom Python |
| `/data/` | CSV catalog |
| `/backtest/` | Run, compare, metrics |
| `/live/deploy/` | New deployment → review |
| `/live/` | Deployments, positions, sync |
| `/broker/` | Create agent, token (once) |
| `/api/agent/*` | Agent Bearer auth |

## Last commit

- `4ca3309` — Phase 3: LiveWorker, MT5 adapter, and live trading sync UI

## Recommended next work (pick one per chat)

1. **Phase 4a** — `download_bars` management command (FX majors, Dukascopy pattern in PLAN).
2. **Polish A** — Symbol map UI (non-admin) + deploy validation.
3. **Polish B** — Live/backtest parity (SL/TP, position rules) in `agent/` + docs.
4. **Polish C** — Celery + HTMX progress for long backtests.
5. **Polish D** — Windows Service doc / script for `python -m agent`.

Copy a starter prompt from [docs/WORKFLOW.md](./docs/WORKFLOW.md).

## Decisions (do not undo without reason)

- Agent tokens: SHA-256 hash; plain token shown once at creation.
- Online agent: heartbeat within `AGENT_HEARTBEAT_TTL_SECONDS` (default 90s).
- `MetaTrader5` import **only** under `agent/`, never in Django apps.
- Market CSVs under `data/` — not in git (see `.gitignore`).
