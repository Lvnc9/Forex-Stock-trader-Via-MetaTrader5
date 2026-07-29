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
