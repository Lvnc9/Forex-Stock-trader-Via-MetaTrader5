# TradeBot

Django trading platform: Python strategies (shared backtest + live), local M1 CSV backtests, and MetaTrader 5 execution via a Windows agent. See [PLAN.md](./PLAN.md) for the full architecture.

## Quick start (development)

```bash
cd tradeBot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # optional; defaults work for local SQLite
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ and sign in.

## Layout

- `config/` — Django settings, URLs
- `apps/` — `core`, `strategies`, `marketdata`, `backtest`, `trading`, `brokers` (stubs until later phases)
- `templates/` — Tailwind + HTMX UI
- `data/` — local M1 OHLC CSVs (not in git)

## Progress

Session handoff: [untilNow.md](./untilNow.md).
