# TradeBot Windows Agent (Phase 3 stub)

Polls the Django web app over **HTTPS** (outbound only). MT5 + `MetaTrader5` run on this machine — not on the Mac/web host.

## Setup

```bash
cd agent
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `agent.env` in the repo root (see PLAN.md):

```env
WEBAPP_URL=http://127.0.0.1:8000
AGENT_TOKEN=<from Broker → Create agent>
```

## Run

```bash
python -m agent
```

The stub client sends heartbeats and fetches armed deployments. Full bar loop + order execution comes in a later slice.
