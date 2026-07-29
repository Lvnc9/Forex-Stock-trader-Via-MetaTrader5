# TradeBot progress (`untilNow`)

Handoff file for the **next agent chat**. Update at the end of every session.

## Plan reference

- Full spec: [PLAN.md](./PLAN.md)

## Current state (last updated: 2026-07-29)

| Area | Status |
| ---- | ------ |
| Phase 1a (scaffold + auth + UI shell) | **Done** |
| Phase 1b (strategies + marketdata) | **Done** |
| Phase 1c (backtest + results UI) | **Done** |
| Phase 2+ (strategy UX, MT5, …) | Not started |

## Phase 1 checklist (PLAN)

| Item | Status |
| ---- | ------ |
| Django + auth + shell | ✓ |
| BaseStrategy, indicators, library strategies | ✓ |
| Market data catalog + M1 loader | ✓ |
| BacktestRunner + BacktestRun + results UI | ✓ |

## Completed this session (Phase 1c)

- **`BacktestRun`** model (strategy FK, slug, TF, dates, spread/commission, metrics JSON, equity curve, trades)
- **`BacktestRunner`**: bar loop with SL/TP; intrabar rule **`stop_loss_before_take_profit`**
- **`execute_backtest`** / **`enqueue_backtest`** (sync; Celery stub in `tasks.py`)
- **UI**: `/backtest/` list, `/backtest/new/` form, detail with **win rate %**, PF, drawdown, **Chart.js** equity curve
- Dashboard shows last completed backtest win rate
- Tests: `apps/backtest/tests/test_runner.py`

## How to run

```bash
cd tradeBot
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_library_strategies
python manage.py runserver
```

- http://127.0.0.1:8000/backtest/new/ — pick strategy, `data/` slug, date range, timeframe
- Large date ranges on M1 can take time (sync run); Celery optional later

## Last commit

- `0bc54d9` — Phase 1c: backtest runner, BacktestRun model, and results UI

## Next session (Phase 2 or Phase 3 slice)

New chat with `@PLAN.md`, `@untilNow.md`.

Suggested: **Phase 2** — per-strategy parameter forms, backtest history polish, custom Python upload validation — **or** jump to **Phase 3** MT5 agent API + Broker UI per PLAN.

## Decisions / notes

- Position sizing: deploy full cash notional per entry (`units = cash / entry_price`); compounding simplified.
- Library strategies do not set SL/TP on signals yet; intrabar rule applies when signals include `stop_loss` / `take_profit`.
- Backtests run synchronously on form submit (no Redis required for Phase 1).
