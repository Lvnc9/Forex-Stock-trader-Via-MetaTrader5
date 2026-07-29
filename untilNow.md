# TradeBot progress (`untilNow`)

## GitHub

[github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5](https://github.com/Lvnc9/Forex-Stock-trader-Via-MetaTrader5) · `git push origin main`

## Current state (2026-07-29)

| Phase | Status |
| ----- | ------ |
| 1 — Backtest foundation | Done |
| 2 — Strategy UX + deploy review | Done |
| 3 — MT5 agent + live | **Mostly done** — LiveWorker + sync UI; polish/logs optional |

## Completed this session (Phase 3 cont.)

- **`agent/live_worker.py`** — new-bar detection, `instantiate_strategy` + `on_bar`, MT5 market orders
- **`agent/mt5_adapter.py`** — initialize, rates → pandas, positions/deals, order send/close (MetaTrader5 **agent only**)
- **`agent/client.py`** — full poll: heartbeat → deployments → worker → sync
- **API sync** — stores `deployment_state` on `Deployment.last_agent_report`
- **`/live/`** — open positions, recent deals, agent errors; re-arm paused → review
- **`agent.env.example`**, expanded `agent/README.md`

## Run

**Web (any OS):**

```bash
source venv/bin/activate && python manage.py migrate && python manage.py runserver
```

**Agent (Windows + MT5, from repo root):**

```bash
pip install -r requirements.txt -r agent/requirements.txt
cp agent.env.example agent.env   # set WEBAPP_URL + AGENT_TOKEN
python -m agent
```

Without MetaTrader5 (Mac dev), agent still heartbeats and syncs empty positions.

## Last commit

- (after push)

## Next (optional)

- Agent: SL/TP on broker side, position flip rules matching backtester
- UI: deployment event log, symbol map editor (non-admin)
- Phase 4: `download_bars` management command, FX/stock data breadth
- `windows-agent` package polish (Windows Service docs)
