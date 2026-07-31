# TradeBot progress (`untilNow`)

Handoff for the **next agent chat**. Read at start; update at end.

## GitHub

| | |
| --- | --- |
| **Repo** | [github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) |
| **Remote** | `origin` → `https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git` |
| **Branches** | PR #1 Phase C · PR #2 Phases A/B (+C) · `cursor/phase-d-builder-expr-htf-48fe` (Phase D) |

## Plan & workflow

- Architecture: [PLAN.md](./PLAN.md)
- Agent prompts: [docs/WORKFLOW.md](./docs/WORKFLOW.md)
- Data downloads: [docs/DATA.md](./docs/DATA.md)
- Conventions: [AGENTS.md](./AGENTS.md)

## Phase status (2026-07-31)

| Phase | Status |
| ----- | ------ |
| 1–4 + polish 0–7 | **Done** |
| **C — HTF + engine unify** | **Done** (PR #1; also in #2/#3) |
| **A/B — Rules engine + builder** | **Done** (PR #2; also in #3) |
| **D — Builder pct_offset/arith + HTF indicators** | **Done** (this branch) |

## Phase D (this session)

| Item | What |
| ---- | ---- |
| Builder refs | `pct_offset` + `arith` editable in fixed-slot form (round-trip from templates) |
| Indicator source | `primary` \| `htf` on each indicator; RuleStrategy computes HTF via `ctx.htf_indicators` |
| Template | `htf_ma_filter_rules` — MA cross gated by HTF SMA trend |
| Tests | `test_phase_d_builder.py` — full suite green |

## Run

```bash
cd tradeBot && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Last commit

- `a961a86` — Phase D: builder pct_offset/arith and HTF indicator source

## Recommended next work

- Merge PR stack (#1 optional if merging #2 or #3 which include C/A/B).
- Windows agent smoke-test: deploy `htf_ma_filter_rules` with `htf_timeframe=H1`.
- Optional: richer nested expressions beyond one-level pct/arith nests.
