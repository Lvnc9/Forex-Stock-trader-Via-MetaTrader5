# TradeBot progress (`untilNow`)

Handoff file for the **next agent chat**. Update at the end of every session.

## GitHub repository

| | |
| --- | --- |
| **Display name** | Forex-Stock trader Via MetaTrader5 |
| **Repo** | [github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) |
| **Remote** | `origin` → `https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git` |
| **Default branch** | `main` |

**Clone (new machine):**

```bash
git clone https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5.git
cd Forex-Stock-trader-Via-MetaTrader5
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate && python manage.py seed_library_strategies
```

**Push updates** (from local `tradeBot/` repo root):

```bash
git add -A && git status
git commit -m "your message"
git push origin main
```

**Not in git:** `venv/`, `.env`, `db.sqlite3`, `data/**/*.csv`, `apps/strategies/user/custom_*.py` (runtime uploads).

**Optional:** In GitHub → **Settings → General**, set repository name/description to match the display title; enable Issues/Discussions if you want public feedback.

## Plan reference

- Full spec: [PLAN.md](./PLAN.md)

## Current state (last updated: 2026-07-29)

| Area | Status |
| ---- | ------ |
| Phase 1 (foundation + backtest) | **Done** |
| Phase 2 (strategy UX) | **In progress** — params, custom upload, compare runs |
| Phase 3 (MT5 agent + Broker UI) | Not started |

## Phase 2 checklist (this session)

| Item | Status |
| ---- | ------ |
| GitHub repo created + `main` pushed | ✓ |
| Per-strategy parameter forms (`/strategies/<id>/parameters/`) | ✓ |
| Library “Configure parameters” + duplicate | ✓ |
| Custom Python upload + AST/import/dry-run validation | ✓ |
| Backtest compare (2–4 completed runs) | ✓ |
| Deploy review step (Phase 2 remainder) | ○ |

## How to run

```bash
cd tradeBot   # or cloned repo folder
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_library_strategies
python manage.py runserver
```

## Last commit

- (update after push)

## Next session

**Phase 2 finish or Phase 3:** deploy review UI, backtest polish — **or** `TradingAgent` model, agent API, Broker page (PLAN Phase 3). Attach `@PLAN.md`, `@untilNow.md`.

## Decisions / notes

- Custom strategies saved under `apps/strategies/user/custom_*.py` (gitignored).
- Compare view only includes runs with `status=completed`.
