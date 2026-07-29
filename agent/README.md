# TradeBot Windows Agent

Polls Django over **HTTPS/HTTP** (outbound). **MetaTrader 5** and the official Python package run on this machine only.

## Requirements

- Windows 10/11, MT5 logged in, **Algo Trading** enabled
- Python 3.11+ (same major as web app)
- Repo cloned (or copy `agent/` + `apps/` from this repository)

## Setup

```powershell
cd C:\path\to\Forex-Stock-trader-Via-MetaTrader5
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r agent\requirements.txt
copy agent.env.example agent.env
```

Edit `agent.env`:

- `WEBAPP_URL` — Django URL reachable from this PC
- `AGENT_TOKEN` — from **Broker → Create agent** (shown once)

Optional: `MT5_TERMINAL_PATH` if auto-detect fails.

## Run

From repo root (so `apps.strategies` imports resolve):

```powershell
venv\Scripts\activate
python -m agent
```

Each poll cycle:

1. Heartbeat + MT5 account snapshot  
2. Fetch **armed** deployments  
3. On each **new closed bar**, run the Python strategy once and send market orders  
4. POST positions, deals, and per-deployment state to `/api/agent/sync`

On Mac/Linux without MT5, the agent runs in **heartbeat-only** mode for API testing.

## Mac web + Windows agent (split)

Set `WEBAPP_URL=https://your-vps-or-lan-ip:8000` on Windows. No inbound ports on the trading PC.
