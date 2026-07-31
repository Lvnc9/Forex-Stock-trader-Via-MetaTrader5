# TradeBot progress (`untilNow`)

Handoff for the **next agent chat**. Read at start; update at end.

## GitHub

| | |
| --- | --- |
| **Repo** | [github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) |
| **Remote** | `origin` → `https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git` |
| **Open PRs** | #1 Phase C · #2 A/B · #3 Phase D · Phase E on `cursor/phase-e-htf-gate-seed-48fe` |

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
| **E** — HTF form gate, `seed_rule_templates`, LiveWorker HTF+rules smoke | **Done** (this branch) |

## Phase E (this session)

| Item | What |
| ---- | ---- |
| HTF gate | Backtest + deploy forms require `htf_timeframe` when strategy rule_spec uses HTF indicators |
| Seed | `python manage.py seed_rule_templates` |
| Smoke | LiveWorker test with RuleStrategy + HTF; agent README smoke steps |

## Left to do (optional / ops)

| Item | Notes |
| ---- | ----- |
| **Merge PR stack** | Prefer merge **#3** (or #E once opened) into `main` — includes C→D; then E |
| **Windows MT5 smoke** | Real agent: seed templates → backtest M5/H1 → deploy (see `agent/README.md`) |
| Library SL/TP knobs | Python library strategies still often emit entries without SL/TP metadata |
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

- `e04cfff` — Phase E: HTF form gate, seed_rule_templates, and smoke path

## Recommended next work

- Merge open PRs to `main`.
- On Windows: follow agent README HTF rule smoke-test.
- Optional product polish: SL/TP params on library Python strategies.
