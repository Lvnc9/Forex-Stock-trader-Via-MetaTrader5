from __future__ import annotations

import os
import time
from pathlib import Path

import requests

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
    print(f"TradeBot agent → {base_url} (poll every {POLL_SECONDS}s)")

    while True:
        try:
            hb = requests.post(
                f"{base_url}/api/agent/heartbeat",
                json={"mt5_connected": False, "account": {}},
                headers=headers,
                timeout=15,
            )
            if hb.status_code == 200:
                dep = requests.get(f"{base_url}/api/agent/deployments", headers=headers, timeout=15)
                count = len(dep.json().get("deployments", [])) if dep.ok else 0
                print(f"heartbeat ok · armed deployments: {count}")
            else:
                print(f"heartbeat failed: {hb.status_code}")
        except requests.RequestException as exc:
            print(f"poll error: {exc}")
        time.sleep(POLL_SECONDS)
