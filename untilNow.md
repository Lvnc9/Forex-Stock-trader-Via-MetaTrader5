# TradeBot progress (`untilNow`)

Handoff for the **next agent chat**. Read at start; update at end.

## GitHub

| | |
| --- | --- |
| **Repo** | [github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) |
| **Remote** | `origin` → `https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git` |
| **Branch** | `cursor/htf-bars-engine-unification-48fe` (Phase C) → merge to `main` |

## Plan & workflow

- Architecture: [PLAN.md](./PLAN.md)
- Agent prompts: [docs/WORKFLOW.md](./docs/WORKFLOW.md)
- Data downloads: [docs/DATA.md](./docs/DATA.md)
- Conventions: [AGENTS.md](./AGENTS.md)

## Phase status (2026-07-31)

| Phase | Status |
| ----- | ------ |
| 1 — Backtest foundation | **Done** |
| 2 — Strategy UX + deploy review | **Done** |
| 3 — MT5 agent + live (v1) | **Done** |
| 4 — Data & stocks breadth | **Done** |
| Post–Phase 3 polish slices 0–7 | **Done** |
| **C — HTF bars + engine unification** | **Done (this branch)** |
| A/B — Rules engine + builder UI | **Not in repo** (prior chat verified locally but never committed) |

## Phase C (this session)

| Item | What |
| ---- | ---- |
| SignalEngine | Shared `build_context` + `on_latest_bar`; HTF window via `htf_bars.loc[:ts]` |
| BacktestRunner | Uses `SignalEngine.run` for signals (no duplicate on_bar loop); accepts `htf_bars` |
| Loader | `prepare_primary_and_htf` + `apps/marketdata/timeframes.py` helpers |
| Models | Optional `htf_timeframe` on `BacktestRun` and `Deployment` (+ migrations) |
| UI / API | Backtest + deploy forms; agent deployments JSON includes `htf_timeframe` |
| LiveWorker | Fetches HTF rates when set; evaluates via `SignalEngine.on_latest_bar` |
| Context | `BarContext.htf_indicators` helper |
| Tests | `apps/strategies/tests/test_phase_c_htf.py` — full suite **36/36** green |

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

- Phase C: HTF bars + SignalEngine/BacktestRunner unification (this branch)

## Recommended next work

- Re-land **Phase A/B** (rules engine + rule builder UI) if still desired — prior work was never pushed to git.
- Optional: library strategy that actually consumes `ctx.htf_bars` / `ctx.htf_indicators`.
- Builder expression picker for `pct_offset` / nested arithmetic (scope limit from Phase B notes).
- Smoke-test Windows agent with an HTF deployment (`htf_timeframe` in API payload).
