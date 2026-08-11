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
| **H&S failure / bust trading** | **Done** | Failure-only strategy + spec + harness gates + image research pack |

## H&S failure (this session)

Product rule: **positions only on head-and-shoulders failure** (Bulkowski bust), never classic neckline reversal.

| Deliverable | Path |
| ----------- | ---- |
| Distill + rules | [`docs/HS-FAILURE-TRADE.md`](docs/HS-FAILURE-TRADE.md) |
| Spec `failure` block | [`hs-curriculum/hs-spec.v1.json`](hs-curriculum/hs-spec.v1.json) |
| Bust watcher | [`apps/strategies/patterns/head_shoulders/failure.py`](apps/strategies/patterns/head_shoulders/failure.py) |
| Library strategy | slug `head_and_shoulders_failure` |
| Image research tools | [`hs-data/images/`](hs-data/images/) (Pillow render/rank/download; bulk PNGs gitignored) |
| Harness failure gates | `compute_failure_gates` in [`hs-data/harness/metrics.py`](hs-data/harness/metrics.py) |

**v1 entry:** after classic confirm, if adverse **close** ≤ `max_bust_atr×ATR` and price **closes beyond head** → enter opposite of classic (failed top → long).

```bash
python manage.py seed_library_strategies   # picks up head_and_shoulders_failure
python manage.py test apps.strategies.tests.test_head_shoulders_failure
# Detector export (failure mode):
cd hs-data && PYTHONPATH=..:. python -m detector.run --bars ... --trade-mode failure --out reports/fail.json
```

## Left to do (optional)

| Item | Notes |
| ---- | ----- |
| **Human Windows MT5 smoke** | Follow both smoke sections in `agent/README.md` on a demo account; record evidence before claiming pass |
| **H&S failure gold labels** | Hand-label ≥40 true failures + ≥40 hard negs on real FX H1/H4; run harness failure gates (precision ≥0.45, recall ≥0.55) |
| **H&S classic hand-label calibration** | Still useful for structure recall; classic strategy remains in registry but product default is failure-only |
| Hedge / multi-position MT5 | Not supported (v1 is netting-style flip) |
| Deeper nested exprs | Builder supports one-level pct_offset/arith only |
| Tick-mode intrabar | Optional later; SL-before-TP rule remains |
| Walk-forward UI | Not started |

## Run

```bash
cd tradeBot && source venv/bin/activate
pip install -r requirements.txt   # includes pyarrow, Pillow
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

Login is at `/login/`.

## Tests run

```bash
python manage.py test apps.strategies.tests.test_head_shoulders_failure apps.strategies.tests.test_head_shoulders
```

(13 OK — failure watcher, failure strategy long-on-busted-top, classic H&S regression.)

## Recommended next work

1. Seed strategies, backtest **`head_and_shoulders_failure`** on **XAUUSD H1** (short range) — confirm only failure entries (long after failed tops / short after failed inverses).
2. Hand-label failure gold set on real FX bars (`hs-data/images/LABELING_FAILURE.md`); calibrate `max_bust_atr`.
3. Windows MT5 smoke when ready.
