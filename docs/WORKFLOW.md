# TradeBot — agent workflow & prompts

Use this after **Phase 3**. One agent chat = **one slice**. Always attach `@tradeBot/PLAN.md`, `@tradeBot/untilNow.md`, `@tradeBot/AGENTS.md`.

---

## Structural prompt (copy shell)

Replace `{SLICE}`, `{SCOPE}`, `{DONE}`, `{FILES}`.

```text
Context (read only):
@tradeBot/PLAN.md
@tradeBot/untilNow.md
@tradeBot/AGENTS.md

Task: {SLICE}

Scope:
- {SCOPE}
- Edit files only under tradeBot/
- Do not read tradeBot/data/*.csv contents; use data/README.md and existing loaders
- Do not import MetaTrader5 outside agent/
- Match existing patterns in {FILES}

Quality bar:
- Run: python manage.py test (fix failures in touched apps)
- Run: python manage.py check
- Milestone git commits with clear messages; never commit data CSVs or secrets

Definition of done:
- {DONE}
- Update tradeBot/untilNow.md (phase status, last commit, next slice)
- Short summary: what changed, what the next agent should do
```

---

## Ready-made slices

### Optimize / harden (use Plan mode first)

```text
@tradeBot/PLAN.md @tradeBot/untilNow.md @tradeBot/AGENTS.md

Plan mode: audit tradeBot for production gaps (security, tests, error handling, live vs backtest parity).
Output a prioritized checklist in chat — do not implement until I approve.

Focus: agent API auth, deployment state machine, strategy validation, SQL injection/XSS in templates, missing migrations.
Ignore: Phase 4 data downloads unless trivial fixes.
```

### Phase 4a — download_bars

```text
@tradeBot/PLAN.md @tradeBot/untilNow.md

Phase 4a only: Django management command download_bars for FX majors via dukascopy-node (see PLAN marketdata section).
Wire optional trigger from /data/ UI. Document in README. Tests for command dry-run or mocked subprocess.
Do not start yfinance/stocks yet. Update untilNow.md when done.
```

### Polish — symbol map UI

```text
@tradeBot/PLAN.md @tradeBot/untilNow.md

Polish only: CRUD UI for SymbolMap (not admin-only), linked from /broker/ or /data/.
Validate catalog_slug exists before deploy (apps/trading/forms.py). HTMX + existing shell.
Tests for form validation. Update untilNow.md.
```

### Polish — live/backtest parity

```text
@tradeBot/PLAN.md @tradeBot/untilNow.md @agent/live_worker.py @apps/backtest/runner.py

Align live agent with backtester: document current gaps, then implement SL/TP and position flip rules shared where possible.
Add tests for pure-Python signal/position logic (no MT5 in tests). Update PLAN backlog if scope shrinks.
```

### Bugfix slice

```text
@tradeBot/untilNow.md

Bug: [describe symptom, URL, steps]

Reproduce with tests if possible. Minimal fix only — no refactors. python manage.py test before commit.
Update untilNow.md if the fix changes runbook or known limitations.
```

---

## Multiple agents — best performance

### Principle

| Role | One chat | Why |
| ---- | -------- | --- |
| **Planner** | Plan mode, no code | Cheap, clear scope |
| **Builder** | One slice, Agent mode | Focused diffs |
| **Reviewer** | Read-only / Bugbot | Catches drift |
| **Fixer** | New chat, minimal prompt | Avoids repair spirals |

Do **not** run Planner + Builder in the same thread if the task is large.

### Parallel agents (when safe)

Use **separate git worktrees** or branches so two agents do not edit the same files.

| Agent A | Agent B | OK in parallel? |
| ------- | ------- | --------------- |
| Phase 4 `download_bars` | Symbol map UI | Usually yes (different apps) |
| `agent/live_worker.py` | `apps/backtest/runner.py` parity | Risky — **sequence** or one owner |
| Two features in `apps/trading/` | — | **No** — one at a time |

Cursor worktrees: agent dropdown → worktree → Apply when done.

### Model / cost (Pro)

- **Default / Cost mode** — implementation, tests, docs.
- **Stronger model** — architecture audit, subtle live-trading bugs, security review.
- **Max mode** — only for cross-cutting refactors (many files); burns quota fast.

### Session hygiene

1. New chat per slice from [untilNow.md](../untilNow.md) “Recommended next work”.
2. `@Past Chats` only for continuity — not full transcript paste.
3. Stop when definition of done is met; do not “while you’re here” expand scope.
4. After long runs: `python manage.py test` + manual smoke (backtest + /live/ + /broker/).

### Human checklist (weekly)

- [ ] `untilNow.md` matches `git log -5`
- [ ] Tests green on `main`
- [ ] Demo deploy on Windows agent still heartbeats
- [ ] PLAN.md backlog still honest (move done items out of “next”)

---

## Making the project better (priority order)

1. **Tests** — more coverage on `backtest/runner`, `strategies/validation`, `brokers/api_views` (agent sync payloads).
2. **Live safety** — explicit live-account gate on deploy review; audit log for armed deployments.
3. **Observability** — structured agent errors in UI; optional Sentry later.
4. **Performance** — Celery for backtests; chunked CSV reads (already planned for huge M1).
5. **Phase 4 data** — FX + documented stock path so catalog matches real trading symbols.
