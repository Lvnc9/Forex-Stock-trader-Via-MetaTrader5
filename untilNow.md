# TradeBot progress (`untilNow`)

Handoff for the **next agent chat**. Read at start; update at end.

## GitHub

| | |
| --- | --- |
| **Repo** | [github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) |
| **Remote** | `origin` → `https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git` |
| **Branch** | `cursor/phase-f-backtest-restructure-864d` (PR #7 → `main`; #1–#6 already on `main`) |

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
| **G4 — Ops handoff docs** | **Done** (checklist only; human smoke not executed here) |
| **Library SL/TP knobs** | **Done** (on `main`) |
| **B0 — Backtest UX pre-fill** | **Done** | `?strategy=` pre-fill, detail KPIs, `docs/backtestVars.md` |
| **Backtest results experience** | **Done** | Full `/backtest/<pk>/` page: identity, progress, balances, chart, trades |
| **Stuck backtest fix** | **Done** | H&S `prepare()` once; max-bars / timeout / orphan cleanup |

## Phase G (this branch)

| Item | What |
| ---- | ---- |
| G1 sizing | `SimulatedBroker` `all_in` / `fixed_lots`; `BacktestRun.lot_size` + `contract_size`; migration `0004` |
| G2 sweeps | `apps/backtest/sweep.py` + `run_jobs_multiprocess`; UI `/backtest/sweep/`; `run_param_sweep` command; Celery `backtest.sweep` |
| G3 cache | `loader.py` Parquet via `pyarrow`; legacy `.pkl` migrates once then deleted |
| G4 docs | Expanded Windows demo smoke checklist in `agent/README.md` |

## Smoke path (CI / no Windows MT5)

| Item | What |
| ---- | ---- |
| LiveWorker SL/TP | `test_live_worker_sl_tp_smoke` — adapter receives `stop_loss` / `take_profit` |
| Docs | `agent/README.md` — HTF deploy + library SL/TP Windows smoke steps + offline test command |
| Suite | Full `python manage.py test` green on `main` (65+ tests) |

## Left to do (optional)

| Item | Notes |
| ---- | ----- |
| **Human Windows MT5 smoke** | Follow both smoke sections in `agent/README.md` on a demo account; record evidence before claiming pass |
| **H&S hand-label calibration** | 50+ true H&S on real FX bars; re-run detector + harness for R2/T2 gates |
| Hedge / multi-position MT5 | Not supported (v1 is netting-style flip) |
| Deeper nested exprs | Builder supports one-level pct_offset/arith only |
| Tick-mode intrabar | Optional later; SL-before-TP rule remains |
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
python manage.py fail_orphaned_backtests --all-stuck   # clear hung runs
python manage.py test apps.backtest apps.strategies.tests.test_head_shoulders
```

(36 OK — H&S prepare once, max-bars guard, orphan cleanup, create→detail.)

## Stuck backtest fix (this session)

Root cause: Head & shoulders called `detect_on_bars` on **every** bar over ~1.4M XAUUSD M1 bars → never finished; detail stayed `running` with empty metrics.

Fixes:
- `BaseStrategy.prepare()` + `SignalEngine` calls it once
- H&S detects once in `prepare`, O(1) lookup in `on_bar`
- `MAX_BACKTEST_BARS=150_000` fail-fast; 15m timeout; orphan cleanup
- `python manage.py fail_orphaned_backtests --all-stuck`

**Use H1/H4 for H&S**, not multi-year M1.

## Recommended next work

1. Restart `runserver`, run H&S on **XAUUSD H1** (short range) → confirm `/backtest/<pk>/` shows balances + chart.
2. Optional live progress: Redis + Celery with `CELERY_TASK_ALWAYS_EAGER=False`.
3. Windows MT5 smoke when ready.
