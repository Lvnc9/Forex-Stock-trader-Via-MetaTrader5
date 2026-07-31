# TradeBot progress (`untilNow`)

Handoff for the **next agent chat**. Read at start; update at end.

## GitHub

| | |
| --- | --- |
| **Repo** | [github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) |
| **Remote** | `origin` → `https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git` |
| **Branch** | `cursor/smoke-library-sltp-live-864d` → merge to `main` |
| **Main tip** | PRs **#1–#5** already merged |

## Done until now

| Area | Status |
| ---- | ------ |
| Phase 1 — scaffold, strategies, marketdata, backtest | **Done** |
| Phase 2 — strategy UX, custom upload, deploy review | **Done** |
| Phase 3 — MT5 agent, live worker, broker API | **Done** |
| Phase 4 — FX/stock downloads | **Done** |
| Polish slices 0–7 | **Done** |
| Phases **A–E** (rules, builder, HTF, seed) | **Done** (on `main`) |
| **Library SL/TP knobs** | **Done** (on `main`) |
| **Automated smoke (HTF + library SL/TP → LiveWorker)** | **Done** (this branch) |

## This session — smoke path (no Windows MT5 in CI)

| Item | What |
| ---- | ---- |
| LiveWorker SL/TP | `test_live_worker_sl_tp_smoke` — adapter receives `stop_loss` / `take_profit` |
| Docs | `agent/README.md` — library SL/TP Windows smoke steps + offline test command |
| Suite | Full `python manage.py test` green |

Real demo-terminal confirmation still needs a human on Windows (steps in `agent/README.md`).

## Left to do (optional)

| Item | Notes |
| ---- | ----- |
| **Human Windows MT5 smoke** | Follow both smoke sections in `agent/README.md` on a demo account |
| Hedge / multi-position MT5 | Not supported (v1 is netting-style flip) |
| Deeper nested exprs | Builder supports one-level pct_offset/arith only |
| Huge CSV / Parquet cache | Still a known risk for very large M1 sets |
| Tick-mode intrabar | Optional later; SL-before-TP rule remains |

## Run

```bash
cd tradeBot && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_library_strategies
python manage.py seed_rule_templates
python manage.py runserver
```

## Last commit

- (this branch) LiveWorker library SL/TP smoke + agent README steps

## Recommended next work

- On a Windows host with demo MT5: run both smoke sections in `agent/README.md`.
- Do **not** start hedge-mode, Parquet cache, or deeper nested expression UI unless explicitly requested.
