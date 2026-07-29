# Forex-Stock trader Via MetaTrader5 (TradeBot)

**GitHub:** [Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5)

Django trading platform: Python strategies (shared backtest + live), local M1 CSV backtests, and MetaTrader 5 execution via a Windows agent. See [PLAN.md](./PLAN.md) for the full architecture.

## Quick start (development)

```bash
cd tradeBot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # optional; defaults work for local SQLite
python manage.py migrate
python manage.py seed_library_strategies
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ and sign in.

| Path | Purpose |
| ---- | ------- |
| `/strategies/` | Parameters, custom Python |
| `/data/` | Local CSV catalog |
| `/backtest/` | Run, compare, win rate + equity chart |
| `/live/` | Deployments, live sync |
| `/broker/` | MT5 agents, API tokens |

**Windows agent:** [agent/README.md](./agent/README.md)

## Layout

- `config/` — Django settings, URLs
- `apps/` — `core`, `strategies`, `marketdata`, `backtest`, `trading`, `brokers`
- `agent/` — Windows MT5 poll worker (not imported by Django on Mac/web-only host)
- `templates/` — Tailwind + HTMX UI
- `data/` — local M1 OHLC CSVs (not in git)
- `docs/WORKFLOW.md` — agent prompts and multi-agent playbook

## Progress

Session handoff: [untilNow.md](./untilNow.md). Full plan: [PLAN.md](./PLAN.md).
