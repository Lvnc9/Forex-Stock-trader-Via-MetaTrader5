# TradeBot progress (`untilNow`)

Handoff for the **next agent chat**. Read at start; update at end.

## GitHub

| | |
| --- | --- |
| **Repo** | [github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) |
| **Remote** | `origin` → `https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git` |
| **Branches** | `cursor/htf-bars-engine-unification-48fe` (Phase C PR #1) · `cursor/rules-engine-builder-ab-48fe` (A/B on top of C) |

## Plan & workflow

- Architecture: [PLAN.md](./PLAN.md)
- Agent prompts: [docs/WORKFLOW.md](./docs/WORKFLOW.md)
- Data downloads: [docs/DATA.md](./docs/DATA.md)
- Conventions: [AGENTS.md](./AGENTS.md)

## Phase status (2026-07-31)

| Phase | Status |
| ----- | ------ |
| 1 — Backtest foundation | **Done** |
| 2 — Strategy UX + deploy review | **Done** |
| 3 — MT5 agent + live (v1) | **Done** |
| 4 — Data & stocks breadth | **Done** |
| Post–Phase 3 polish slices 0–7 | **Done** |
| **C — HTF bars + engine unification** | **Done** (intact; PR #1) |
| **A — Rules engine** | **Done** (this branch; was never on remote before) |
| **B — Rule builder UI** | **Done** (this branch) |

## Integrity check (this session)

- Phase C files match `origin/cursor/htf-bars-engine-unification-48fe` — **not damaged**.
- Prior “Phase A/B committed” claim: **false on GitHub** (only `main` + Phase C branch existed). A/B is now landed on `cursor/rules-engine-builder-ab-48fe`.

## Phase A/B (this session)

| Item | What |
| ---- | ---- |
| Rules engine | `apps/strategies/rules/` — expr language (indicator/price/value/param/pct_offset/arith), schema, `RuleStrategy` runtime |
| Templates | `ma_cross_rules`, `rsi_rules`, `range_breakout_rules` (pct_offset demo) |
| Builder UI | `/strategies/rules/new/`, `/strategies/rules/<pk>/edit/`, `?from=<slug>` |
| Dry-run | Spec validated via real SignalEngine before save |
| Python lifecycle | `update_custom_strategy_source` edits file in place with rollback |
| Delete | Blocked when BacktestRun/Deployment references strategy |
| Model | `Strategy.rule_spec` + `runtime_parameters()` for backtest/live |

## Run

```bash
cd tradeBot && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Last commit

- `5e063e2` — Phases A/B: rules engine and fixed-slot rule builder UI

## Recommended next work

- Merge Phase C PR #1, then this A/B branch (or merge this branch alone — it includes C).
- Optional Phase D: builder UI for `pct_offset` / nested `arith` (engine already supports them).
- HTF-consuming library/rule template.
- Windows agent smoke-test with HTF + rule strategy deploy.
