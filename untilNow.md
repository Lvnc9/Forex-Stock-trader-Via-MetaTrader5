# TradeBot progress (`untilNow`)

Handoff file for the **next agent chat**. Update at the end of every session.

## Plan reference

- Full spec: [PLAN.md](./PLAN.md)
- YAML todos in PLAN frontmatter: update status there when you complete major items (optional but helpful).

## Current state (last updated: 2026-07-29)

| Area | Status |
| ---- | ------ |
| Repo | `tradeBot/` git initialized; Django **Phase 1a complete** |
| Phase 1a (scaffold + auth + UI shell) | **Done** |
| Phase 1b (strategies + marketdata) | Not started |
| Phase 1c (backtest + results UI) | Not started |
| Git | Initialized under `tradeBot/` |

## Phase 1 checklist (PLAN)

| Item | 1a | 1b | 1c |
| ---- | -- | -- | -- |
| Django project (`config/`, `apps/`, `manage.py`) | ✓ | | |
| App stubs: `core`, `strategies`, `marketdata`, `backtest`, `trading`, `brokers` | ✓ | | |
| Auth (login / logout, protected dashboard) | ✓ | | |
| Tailwind + HTMX base shell (sidebar nav per PLAN) | ✓ | | |
| `BaseStrategy` + `IndicatorRegistry` + example strategies | | ○ | |
| Market data catalog + M1 loader | | ○ | |
| Backtest runner + results UI (win rate %, equity chart) | | | ○ |

## Completed this session (Phase 1a)

- Django 5 project: `config/`, `manage.py`, `requirements.txt` (Django, django-environ, django-htmx)
- Six apps registered per PLAN (only `core` has views/templates; others are stubs)
- Session auth: login page, logout (POST), `@login_required` dashboard
- UI: dark zinc sidebar + top bar, nav placeholders, Demo/MT5 offline pills, HTMX boost on body, Alpine for mobile sidebar
- `README.md`, `.env.example`, local `venv` + `migrate` verified

## How to run

```bash
cd tradeBot
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # optional
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ → redirects to login → dashboard after sign-in.

## Last commit

- `8e8b457` — docs: update untilNow and ignore download/ CSV artifacts
- `2652b47` — Phase 1a: Django scaffold, auth, and Tailwind+HTMX shell

## Next session (Phase 1b)

New chat. Attach `@tradeBot/PLAN.md`, `@tradeBot/untilNow.md`, `@tradeBot/AGENTS.md`.

> Phase **1b** only: `BaseStrategy`, `IndicatorRegistry`, `SignalEngine`, three library strategies; `marketdata` catalog scanner + M1 loader/resampler wired to `data/` paths (no CSV ingestion in chat). Do **not** start backtest runner (1c).

## Decisions / notes

- Tailwind via CDN for 1a; move to built assets under `static/` when the UI grows.
- `MetaTrader5` stays out of Django requirements until the Windows agent phase.
- Workspace parent may be `WorkFlow/`; only edit under `tradeBot/`.
- Local CSV backtest data stays on disk under `data/`; not in git.
