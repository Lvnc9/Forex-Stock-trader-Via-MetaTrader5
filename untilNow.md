# TradeBot progress (`untilNow`)

Handoff for the **next agent chat**. Read at start; update at end.

## GitHub

| | |
| --- | --- |
| **Repo** | [github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) |
| **Remote** | `origin` → `https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git` |
| **Branch** | `main` (PRs **#1–#5** merged) |

## Done until now

| Area | Status |
| ---- | ------ |
| Phase 1 — scaffold, strategies, marketdata, backtest | **Done** |
| Phase 2 — strategy UX, custom upload, deploy review | **Done** |
| Phase 3 — MT5 agent, live worker, broker API | **Done** |
| Phase 4 — FX/stock downloads | **Done** |
| Polish slices 0–7 | **Done** |
| **C** — HTF bars + SignalEngine/BacktestRunner unify | **Done** (merged via #4) |
| **A/B** — Rules engine + builder UI | **Done** (merged via #4) |
| **D** — Builder pct_offset/arith + HTF indicator source | **Done** (merged via #4) |
| **E** — HTF form gate, `seed_rule_templates`, smoke path | **Done** (merged #4) |
| **Library SL/TP knobs** | **Done** (merged #5) |

## Merged this session (ops)

| PR | What |
| -- | ---- |
| **#4** | Phases C→E (superseded #1–#3 content) fast-forwarded to `main` |
| **#5** | Optional `stop_loss_pct` / `take_profit_pct` on library strategies |

## Left to do (optional)

| Item | Notes |
| ---- | ----- |
| **Windows MT5 smoke** | Seed templates → backtest M5/H1 → deploy; try library strategies with non-zero SL/TP pcts |
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

- `2c83ea6` — docs: note PR #5 in untilNow handoff (tip before this ops note)
- Feature tip: `54007e2` — Add optional SL/TP pct params to library strategies

## Recommended next work

- On Windows: smoke-test HTF rule strategies and library SL/TP pct params against demo MT5.
- Do **not** start hedge-mode, Parquet cache, or deeper nested expression UI unless explicitly requested.
