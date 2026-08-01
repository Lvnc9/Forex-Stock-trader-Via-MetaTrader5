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

## Run as a Windows Service (optional)

For 24/7 trading on a VPS, keep MT5 logged in and run the agent as a service so it restarts after reboot.

### Option A — NSSM (recommended)

1. Download [NSSM](https://nssm.cc/download) and extract `nssm.exe`.
2. From an **Administrator** PowerShell in the repo root:

```powershell
.\agent\scripts\install-service-nssm.ps1 `
  -NssmPath "C:\tools\nssm\win64\nssm.exe" `
  -RepoRoot (Get-Location).Path `
  -PythonExe (Join-Path (Get-Location) "venv\Scripts\python.exe")
```

Or manually:

```powershell
nssm install TradeBotAgent "C:\path\to\repo\venv\Scripts\python.exe"
nssm set TradeBotAgent AppDirectory "C:\path\to\repo"
nssm set TradeBotAgent AppParameters "-m agent"
nssm set TradeBotAgent AppEnvironmentExtra "WEBAPP_URL=http://127.0.0.1:8000" "AGENT_TOKEN=YOUR_TOKEN"
nssm set TradeBotAgent Start SERVICE_AUTO_START
nssm start TradeBotAgent
```

Logs: `nssm set TradeBotAgent AppStdout C:\path\to\repo\agent\logs\stdout.log` (and AppStderr).

### Option B — Task Scheduler

1. Create a basic task → **When the computer starts**.
2. Action: Start a program → `C:\path\to\repo\venv\Scripts\python.exe`
3. Arguments: `-m agent`
4. Start in: `C:\path\to\repo`
5. Check **Run whether user is logged on or not** (MT5 session must still be available for Algo Trading).

Unload: `nssm stop TradeBotAgent` then `nssm remove TradeBotAgent confirm`.

## Windows MT5 demo smoke checklist

Run this on a **Windows** host with MT5 demo (or all-in-one). Do **not** mark smoke as passed in docs without evidence from this run.

### Prep

1. `git pull` the branch you are testing; `pip install -r requirements.txt` (+ `agent\requirements.txt`).
2. `python manage.py migrate` (includes backtest sizing + parameter_overrides).
3. `python manage.py seed_library_strategies`
4. `python manage.py seed_rule_templates`
5. Start Django (`runserver`); optionally Redis + Celery for long backtests.
6. Broker → Create agent → paste token into `agent.env`; start `python -m agent` with MT5 logged in and **Algo Trading** ON.
7. Confirm **Broker** shows agent **Online** and a demo account snapshot.

### Backtest → deploy

1. **Backtest** a library or HTF rule strategy on a local catalog slug:
   - Primary **M5**, optional HTF **H1** when the strategy requires it.
   - Prefer **Position sizing → Fixed lots** with `lot_size=0.01` (matches `Deployment.lot_size`) so metrics are comparable to live.
2. Open the completed run; note win rate / return / sizing line.
3. Strategies → **Deploy review** → create deployment to the online agent:
   - Same catalog → MT5 symbol map; same primary (+ HTF) as the backtest.
   - `lot_size` equal to the fixed-lots backtest (e.g. `0.01`).
4. Arm the deployment; wait for a **new closed bar**.
5. On **/live/** confirm: agent report `status=processed`, optional `htf_timeframe`, and an order/position or clean exit with no strategy/MT5 errors.
6. Pause or stop the deployment when done.

### Optional: parameter sweep (web or CLI)

- UI: **Backtest → Param sweep** (≤ 8 values; multiprocess over independent runs).
- CLI: `python manage.py run_param_sweep --strategy <slug> --catalog <slug> --start YYYY-MM-DD --end YYYY-MM-DD --param fast_period --values 5,10,15 --sync`

### Smoke-test: HTF rule strategy (short)

1. Strategies → open **MA cross + HTF filter** (or Customize rules from that template).
2. Backtest with primary e.g. `M5` and **Higher timeframe** `H1` (form blocks blank HTF when required).
3. Deploy with the same HTF field; confirm agent report shows `htf_timeframe` and processes new bars (`/live/`).

Without MT5, pure-Python LiveWorker tests cover HTF bar fetch + `RuleStrategy` evaluation — that is **not** a substitute for this Windows demo smoke.
