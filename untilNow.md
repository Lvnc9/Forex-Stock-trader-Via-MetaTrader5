# TradeBot progress (`untilNow`)

Handoff for the **next agent chat**. Read at start; update at end.

## GitHub

| | |
| --- | --- |
| **Repo** | [github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) |
| **Remote** | `origin` → `https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git` |
| **Branch** | `cursor/phase-f-backtest-restructure-864d` |

## Done until now

| Area | Status |
| ---- | ------ |
| Phase 1 — scaffold, strategies, marketdata, backtest | **Done** |
| Phase 2 — strategy UX, custom upload, deploy review | **Done** |
| Phase 3 — MT5 agent, live worker, broker API | **Done** |
| Phase 4 — FX/stock downloads | **Done** |
| Polish A–E (rules, builder, HTF, seed) | **Done** |
| **F — Backtest restructure** | **Done** |
| **G1 — Live/backtest sizing parity** | **Done** |
| **G2 — Multicore param sweeps** | **Done** |
| **G3 — Parquet bar cache** | **Done** |
| **G4 — Ops handoff docs** | **Done** (checklist only; smoke not executed here) |

## Phase G (this session)

| Item | What |
| ---- | ---- |
| G1 sizing | `SimulatedBroker` `all_in` / `fixed_lots`; `BacktestRun.lot_size` + `contract_size`; migration `0004` |
| G2 sweeps | `apps/backtest/sweep.py` + `run_jobs_multiprocess`; UI `/backtest/sweep/`; `run_param_sweep` command; Celery `backtest.sweep` |
| G3 cache | `loader.py` Parquet via `pyarrow`; legacy `.pkl` migrates once then deleted |
| G4 docs | Expanded Windows demo smoke checklist in `agent/README.md` |

## Left to do (optional — not this pass)

| Item | Notes |
| ---- | ----- |
| **Windows MT5 demo smoke** | Follow `agent/README.md` checklist; record evidence before claiming pass |
| Hedge / multi-position | Still netting-style flip only |
| Tick-mode intrabar | Optional; SL-before-TP remains |
| Walk-forward UI | Not started |

## Run

```bash
cd tradeBot && source venv/bin/activate
pip install -r requirements.txt   # includes pyarrow
python manage.py migrate          # through backtest.0005_parameter_overrides
python manage.py seed_library_strategies
python manage.py seed_rule_templates
python manage.py runserver
```

**Faster / non-blocking backtests:**

```bash
export CELERY_TASK_ALWAYS_EAGER=False
export TRADEBOT_BACKTEST_LOAD_WORKERS=8
redis-server
celery -A config worker -l info --concurrency=4
python manage.py runserver
```

**Param sweep (CLI):**

```bash
python manage.py run_param_sweep \
  --strategy <slug> --catalog <slug> \
  --start YYYY-MM-DD --end YYYY-MM-DD \
  --param fast_period --values 5,10,15 --sync
```

Login is at `/login/`.

## Tests run

```bash
python manage.py test apps.backtest apps.marketdata.tests.test_loader_catalog
# 20 OK (this session)
```

## Last commits (this branch tip)

- `82b8f25` — G3: Parquet bar cache via pyarrow
- `d8419ea` — G2: multiprocess parameter sweeps
- `3fcab11` — G1: fixed-lots sizing parity
- `4cfb90d` — Phase F: modular backtest engine (earlier on branch)

## Recommended next work

1. On Windows: run the **MT5 demo smoke** in `agent/README.md` and paste evidence into the next handoff.
2. Only then optional product work: hedge/multi-position, tick-mode intrabar, or walk-forward UI.
