# TradeBot — agent instructions

All application code for this product lives under **`tradeBot/`** only. Do not copy from sibling folders in `WorkFlow/` (e.g. `TradeBot-main/`, `trading_backtester/`).

## Source of truth

- **Product plan:** `@PLAN.md` (phases, layout, stack).
- **Progress handoff:** `@untilNow.md` — read at session start; update at session end.

## Phases (one agent chat ≈ one slice)

| Slice | Scope |
| ----- | ----- |
| **1a** | Django scaffold, auth, Tailwind + HTMX base shell |
| **1b** | `BaseStrategy`, indicators, example strategies, marketdata catalog + loader |
| **1c** | Backtest runner, results UI (win rate %, equity chart) |
| **2+** | See `PLAN.md` |

When a slice is done, **stop** and start a **new chat** with `@untilNow.md` and `@PLAN.md`. Do not continue unrelated phases in the same thread.

## Market data

- CSVs live under `data/` (see `data/README.md`). **Never read CSV contents into chat** unless debugging one small sample; implement loaders using paths and schema from the plan.
- **Never commit** `*.csv` or bulk data (see `.gitignore`).

## Stack (from plan)

- Django, server-rendered templates, **HTMX**, Tailwind; minimal Alpine.js when needed.
- Python 3.11+. MetaTrader5 only on the Windows agent — **not** in Django on Mac/split web host.

## Git

- Repo root is **`tradeBot/`** (init here if missing).
- Commit after **logical milestones**, not every file save.
- Do not commit secrets, `db.sqlite3`, or market CSVs.

## Session end checklist

1. Run migrations / tests relevant to your slice.
2. Update `untilNow.md` (checklist, commands, last commit, next slice).
3. Summarize what the **next** agent should do in one short paragraph.

## If the agent drifts

Revert, refine the plan slice in `PLAN.md` or your prompt, and rerun in a **new** chat — do not stack long fix-up threads.
