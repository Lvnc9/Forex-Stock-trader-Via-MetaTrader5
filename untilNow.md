# TradeBot progress (`untilNow`)

Handoff for the **next agent chat**. Read at start; update at end.

## GitHub

| | |
| --- | --- |
| **Repo** | [github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) |
| **Remote** | `origin` → `https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git` |
| **Branch** | `main` (PRs **#1–#5** merged; smoke path on `main` via #6 commits) |

## Done until now

| Area | Status |
| ---- | ------ |
| Phase 1 — scaffold, strategies, marketdata, backtest | **Done** |
| Phase 2 — strategy UX, custom upload, deploy review | **Done** |
| Phase 3 — MT5 agent, live worker, broker API | **Done** |
| Phase 4 — FX/stock downloads | **Done** |
| Polish slices 0–7 | **Done** |
| Phases **A–E** (rules, builder, HTF, seed) | **Done** |
| **Library SL/TP knobs** | **Done** |
| **Automated smoke (HTF + library SL/TP → LiveWorker)** | **Done** (on `main`) |

## Smoke path (CI / no Windows MT5)

| Item | What |
| ---- | ---- |
| LiveWorker SL/TP | `test_live_worker_sl_tp_smoke` — adapter receives `stop_loss` / `take_profit` |
| Docs | `agent/README.md` — library SL/TP Windows smoke steps + offline test command |
| Suite | Full `python manage.py test` **65/65** green |

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

## Last commit on main

- `fc05b20` — Add LiveWorker library SL/TP smoke path and docs
- `0d4d220` — docs: record smoke-path commit hash in untilNow

## Recommended next work

- On a Windows host with demo MT5: run both smoke sections in `agent/README.md` (HTF rules + library SL/TP).
- Do **not** start hedge-mode, Parquet cache, or deeper nested expression UI unless explicitly requested.
