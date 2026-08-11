from __future__ import annotations

import os
import time
from pathlib import Path

import requests

from agent.bootstrap import ensure_repo_root
from agent.live_worker import LiveWorker
from agent.mt5_adapter import MT5BrokerAdapter

ensure_repo_root()

POLL_SECONDS = 30


def _load_env() -> tuple[str, str]:
    base = Path(__file__).resolve().parent.parent
    env_path = base / "agent.env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())
    url = os.environ.get("WEBAPP_URL", "http://127.0.0.1:8000").rstrip("/")
    token = os.environ.get("AGENT_TOKEN", "")
    if not token:
        raise SystemExit("Set AGENT_TOKEN in agent.env (Broker UI → Create agent).")
    return url, token


def run_forever() -> None:
    base_url, token = _load_env()
    headers = {"Authorization": f"Bearer {token}"}
    adapter = MT5BrokerAdapter()
    if adapter.available:
        ok = adapter.connect()
        print(f"MetaTrader5 initialize: {'ok' if ok else 'failed'}")
    else:
        print("MetaTrader5 package not installed — heartbeat-only mode (dev/Mac).")

    worker = LiveWorker(adapter=adapter)
    print(f"TradeBot agent → {base_url} (poll every {POLL_SECONDS}s)")

    try:
        while True:
            worker.errors.clear()
            try:
                account = adapter.account_info_dict() if adapter.connected else {}
                hb = requests.post(
                    f"{base_url}/api/agent/heartbeat",
                    json={"mt5_connected": adapter.connected, "account": account},
                    headers=headers,
                    timeout=30,
                )
                deployments: list[dict] = []
                if hb.status_code == 200:
                    dep_resp = requests.get(
                        f"{base_url}/api/agent/deployments",
                        headers=headers,
                        timeout=30,
                    )
                    if dep_resp.ok:
                        deployments = dep_resp.json().get("deployments", [])

                state = worker.process_deployments(deployments)
                sync_body = {
                    "positions": adapter.positions_payload() if adapter.connected else [],
                    "deals": adapter.deals_payload() if adapter.connected else [],
                    "errors": list(worker.errors),
                    "deployment_state": state,
                }
                requests.post(
                    f"{base_url}/api/agent/sync",
                    json=sync_body,
                    headers=headers,
                    timeout=30,
                )
                print(
                    f"heartbeat {hb.status_code} · mt5={adapter.connected} · "
                    f"deployments={len(deployments)} · bars processed={len(state)}"
                )
            except requests.RequestException as exc:
                print(f"poll error: {exc}")
            time.sleep(POLL_SECONDS)
    finally:
        adapter.shutdown()
