# TradeBot progress (`untilNow`)

Handoff for the **next agent chat**. Read at start; update at end.

## GitHub

| | |
| --- | --- |
| **Repo** | [github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) |
| **Remote** | `origin` → `https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git` |

## Done until now

| Area | Status |
| ---- | ------ |
| Phase 1 — scaffold, strategies, marketdata, backtest | **Done** |
| Phase 2 — strategy UX, custom upload, deploy review | **Done** |
| Phase 3 — MT5 agent, live worker, broker API | **Done** |
| Phase 4 — FX/stock downloads | **Done** |
| Polish A–E (rules, builder, HTF, seed) | **Done** |
| **F — Backtest restructure** | **Done** (this session) |

## Phase F (this session)

| Item | What |
| ---- | ---- |
| Modular engine | `data_handler`, `broker`, `portfolio`, `metrics`, `runner` facade |
| Timeframe-aware | M1 source → resample primary/HTF; TF metadata on metrics; form help |
| Data loading | Prefer `months/` over yearly; epoch-ms **or** ISO timestamps; date-filtered files |
| Speed | Threaded CSV load; parallel primary+HTF resample; indicator series cache; equity downsample |
| Cache | Pickle under `data/.cache/` (`TRADEBOT_BACKTEST_CACHE`); catalog slug LocMem cache |
| UI / Celery | `progress_pct` + `/backtest/<id>/status/` JSON + HTMX progress bar; Celery soft limits |

## Left to do

| Item | Notes |
| ---- | ----- |
| **Windows MT5 smoke** | Real agent demo: backtest → deploy (see `agent/README.md`) |
| Lot-sized backtest | Still all-in cash sizing vs live `lot_size` |
| Hedge / multi-position | Netting-style flip only |
| Tick-mode intrabar | Optional; SL-before-TP remains |
| Commit Phase F + builder UX | User has not requested commit yet |

## Strategy builder UX (this session)

Rule builder no longer pre-renders spare slots. Each section (**parameters / indicators / rules**) starts with **1 row**; **+ Add** uses HTMX (`strategies:builder_row`) to append a row; **−** removes a row in the DOM. Ceilings remain `MAX_PARAMS=24` / `MAX_INDICATORS=16` / `MAX_RULES=12`. Schema/runtime still unbounded.

## Run

```bash
cd tradeBot && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_library_strategies
python manage.py seed_rule_templates
python manage.py runserver
```

**Faster / non-blocking backtests (recommended for large M1 sets):**

```bash
export CELERY_TASK_ALWAYS_EAGER=False
export TRADEBOT_BACKTEST_LOAD_WORKERS=8
redis-server   # separate terminal
celery -A config worker -l info --concurrency=4
python manage.py runserver
```

Login is at `/login/`. After pull, always `migrate` (includes `backtest.0003_backtestrun_progress`).

## Tests run

```bash
python manage.py test apps.backtest apps.marketdata.tests.test_loader_catalog apps.strategies.tests.test_phase_c_htf
# 25 OK
```

## Last commit

- `aeae101` — docs: record Phase F commit hash in untilNow
- `4a6f7a0` — Raise rule-builder UI ceilings with dynamic spare slots.
- `53a0dab` — Add HTMX +/− rows to rule builder starting from one slot.
- `4cfb90d` — Phase F: modular backtest engine with TF-aware load, cache, and progress.


## Recommended next work

- Commit Phase F when ready.
- On Windows: MT5 demo smoke with HTF rules + library SL/TP.
- Optional: lot/risk sizing in `SimulatedBroker` to match live deployments.
