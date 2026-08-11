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
| **Automated smoke (HTF + library SL/TP → LiveWorker)** | **Done** (on `main`) |

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
python manage.py test apps.backtest apps.marketdata.tests.test_loader_catalog
python manage.py test apps.strategies.tests.test_library_sl_tp apps.strategies.tests.test_live_worker_sl_tp_smoke
```

## Last commits (this branch tip)

- `838bea1` — H&S detector harness + Django strategy wiring
- `fc2eec1` — H&S curriculum pack + spec
- `d76bd77` — G4: Windows smoke docs + Phase G closeout
- `fc05b20` — LiveWorker library SL/TP smoke path (from `main`)

## H&S curriculum (side track)

| Agent | Status | Path |
| ----- | ------ | ---- |
| 1 — diagnosis + spec | Done | `hs-curriculum/` |
| 2 — labels + harness | Done | `hs-data/` (harness, schema, synthetic) |
| **3 — detector + Plan 1** | **Done** | `hs-data/detector/`, `docs/HS-ELEMENTS.md`, `docs/HS-FAILURES.md` |

**Plan 1 deliverables:** element/failure docs; FX bar export (`bars/export_bars.py`); filled label corpus generator (`labels/generate_corpus.py` — 52 true + 32 hard neg); Python detector + CLI; harness E5 premature entry + TP2 at k×H.

**Validation loop:**

```bash
cd hs-data
python bars/export_bars.py --out-dir bars
python labels/generate_corpus.py
python -m synthetic.generate_synthetic --out synthetic/out
python -m detector.run --bars bars/EURUSD_H1_corpus.csv --symbol EURUSD --timeframe H1 --out reports/corpus_detections.json
python -m harness.evaluate --bars-dir bars --labels labels/filled --detections reports/corpus_detections.json --out reports/run_corpus
```

Corpus gates: recall/precision 1.0, E5 premature 0.0. TP1 hit rate on auto-corpus remains low — re-measure on hand labels over real `bars/*.csv`.

Smoke: `cd hs-data && python -m unittest harness.tests.test_harness_smoke -v` (2 OK).

## Recommended next work

1. **Hand-label** 50+ true H&S on real yfinance/MT5 bars in `labels/filled/`; re-run detector + harness for production R2/T2 calibration.
2. On Windows: run **both** smoke sections in `agent/README.md` (HTF deploy + library SL/TP) and paste evidence into the next handoff.
3. Merge PR #7; then optional product work (hedge/multi-position, walk-forward UI) only if explicitly requested.
