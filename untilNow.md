# TradeBot progress (`untilNow`)

Handoff for the **next agent chat**. Read at start; update at end.

## GitHub

| | |
| --- | --- |
| **Repo** | [github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) |
| **Remote** | `origin` → `https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git` |
| **This branch** | `cursor/library-strategy-sl-tp-864d` (on Phase E) |
| **Open PRs** | #1–#4 (C→E); prefer merge **#4** into `main` first (supersedes #1–#3) |

## Done until now

| Area | Status |
| ---- | ------ |
| Phase 1 — scaffold, strategies, marketdata, backtest | **Done** |
| Phase 2 — strategy UX, custom upload, deploy review | **Done** |
| Phase 3 — MT5 agent, live worker, broker API | **Done** |
| Phase 4 — FX/stock downloads | **Done** |
| Polish slices 0–7 | **Done** |
| **C** — HTF bars + SignalEngine/BacktestRunner unify | **Done** (PR #1+) |
| **A** — Rules expression engine + RuleStrategy | **Done** (PR #2+) |
| **B** — Rule builder UI, dry-run, delete, Python in-place edit | **Done** (PR #2+) |
| **D** — Builder pct_offset/arith + HTF indicator source + template | **Done** (PR #3) |
| **E** — HTF form gate, `seed_rule_templates`, LiveWorker HTF+rules smoke | **Done** (PR #4) |
| **Library SL/TP knobs** | **Done** (this branch) |

## This session — library strategy SL/TP

| Item | What |
| ---- | ---- |
| Params | Optional `stop_loss_pct` / `take_profit_pct` (default `0` = omit) on `ma_crossover`, `rsi_reversal`, `range_breakout` |
| Helper | `apps/strategies/library/exits.py` → absolute prices on `Signal.stop_loss` / `take_profit` |
| Warmup | `SignalEngine._warmup_bars` uses **int** schema only (float pct/levels no longer inflate warmup) |
| Tests | `apps/strategies/tests/test_library_sl_tp.py` — full suite **63/63** green |

## Left to do (optional / ops)

| Item | Notes |
| ---- | ----- |
| **Merge PR stack** | Prefer merge **#4** into `main` (includes C→E), then this SL/TP PR (or rebase onto main after #4) |
| **Windows MT5 smoke** | Real agent: seed templates → backtest M5/H1 → deploy with SL/TP params set |
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

- (this branch) Library strategies emit optional SL/TP from pct params

## Recommended next work

- **Ops first:** merge PR **#4** into `main`, then merge/rebase this SL/TP branch; refresh `untilNow.md` on `main`.
- On Windows: smoke-test library strategies with non-zero `stop_loss_pct` / `take_profit_pct` so MT5 orders carry SL/TP.
- Do **not** start hedge-mode, Parquet cache, or deeper nested expression UI unless explicitly requested.
