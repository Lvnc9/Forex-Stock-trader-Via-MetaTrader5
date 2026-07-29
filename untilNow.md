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
- Agent prompts: [docs/WORKFLOW.md](./docs/WORKFLOW.md)
- Data downloads: [docs/DATA.md](./docs/DATA.md)
- Conventions: [AGENTS.md](./AGENTS.md)

## Phase status (2026-07-29)

| Phase | Status |
| ----- | ------ |
| 1 — Backtest foundation | **Done** |
| 2 — Strategy UX + deploy review | **Done** |
| 3 — MT5 agent + live (v1) | **Done** |
| 4 — Data & stocks breadth | **Done** |
| Post–Phase 3 polish slices 0–7 | **Done** |

## Polish slices completed this session

| Slice | What |
| ----- | ---- |
| 0 | Fixed `agent/mt5_adapter.py` SyntaxError (`self.timeframe_constant`) |
| 1 | Windows Service / NSSM docs + `agent/scripts/install-service-nssm.ps1` |
| 2 | Live confirm even if agent offline; API hides unconfirmed live armed deps |
| 3 | Non-admin Symbol map CRUD at `/data/symbols/` + deploy form map fill |
| 4a | `download_bars` (dukascopy-node FX majors) |
| 4b | `download_stocks` (yfinance) + [docs/DATA.md](./docs/DATA.md) |
| 5 | `DeploymentEvent` audit log on arm/pause/stop + agent errors |
| 6 | Live/backtest flip + SL/TP via `position_intent` + adapter |
| 7 | Celery tasks (eager by default) + HTMX refresh on pending backtests |

## Run

```bash
cd tradeBot && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Async backtests (optional): set `CELERY_TASK_ALWAYS_EAGER=False` and `celery -A config worker -l info` with Redis.

Agent (Windows): see [agent/README.md](./agent/README.md).

## Last commit

- `d707feb` — Complete polish slices 0–7

## Recommended next work

- Smoke-test Windows agent + demo MT5 after Slice 0 fix
- Library strategies that emit SL/TP levels
- Hedge-mode / multi-position MT5 accounts if needed
