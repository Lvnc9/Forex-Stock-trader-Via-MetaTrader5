from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.bootstrap import ensure_repo_root

ensure_repo_root()

from apps.strategies.engine import SignalEngine  # noqa: E402
from apps.strategies.loader import instantiate_strategy  # noqa: E402
from apps.strategies.position_intent import resolve_signal_intent  # noqa: E402
from apps.strategies.signals import Signal  # noqa: E402


@dataclass
class DeploymentRuntime:
    deployment_id: int
    last_bar_iso: str | None = None


@dataclass
class LiveWorker:
    adapter: Any
    engine: SignalEngine = field(default_factory=SignalEngine)
    runtimes: dict[int, DeploymentRuntime] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def process_deployments(self, deployments: list[dict]) -> list[dict]:
        reports: list[dict] = []
        if not self.adapter.connected:
            return reports

        for dep in deployments:
            report = self._process_one(dep)
            if report:
                reports.append(report)
        return reports

    def _process_one(self, dep: dict) -> dict | None:
        dep_id = int(dep["id"])
        symbol = dep["mt5_symbol"]
        tf = dep["timeframe"]
        htf_tf = (dep.get("htf_timeframe") or "").strip()
        lot = float(dep.get("lot_size") or 0.01)
        runtime = self.runtimes.setdefault(dep_id, DeploymentRuntime(deployment_id=dep_id))

        bars = self.adapter.copy_rates_df(symbol, tf)
        if bars.empty or len(bars) < 30:
            self.errors.append(f"dep {dep_id}: insufficient bars for {symbol}")
            return {
                "id": dep_id,
                "last_bar": runtime.last_bar_iso,
                "status": "no_data",
            }

        last_ts = bars.index[-1]
        last_iso = last_ts.isoformat()
        if runtime.last_bar_iso == last_iso:
            return {"id": dep_id, "last_bar": last_iso, "status": "unchanged"}

        try:
            strategy = instantiate_strategy(dep["module_path"], dep.get("parameters"))
        except Exception as exc:
            self.errors.append(f"dep {dep_id}: strategy load failed: {exc}")
            return {"id": dep_id, "last_bar": last_iso, "status": "strategy_error"}

        htf_bars = None
        if htf_tf:
            htf_bars = self.adapter.copy_rates_df(symbol, htf_tf)
            if htf_bars.empty:
                self.errors.append(f"dep {dep_id}: insufficient HTF bars ({htf_tf}) for {symbol}")
                return {"id": dep_id, "last_bar": last_iso, "status": "no_htf_data"}

        signal: Signal | None = self.engine.on_latest_bar(strategy, bars, htf_bars=htf_bars)
        action_result = None
        if signal is not None:
            open_side = None
            if hasattr(self.adapter, "open_side_for"):
                open_side = self.adapter.open_side_for(symbol)
            intent = resolve_signal_intent(signal, open_side)
            if intent.close_first and not intent.open_side:
                action_result = self.adapter.execute_signal(symbol, "exit", lot)
            elif intent.open_side:
                action = "enter_long" if intent.open_side == "long" else "enter_short"
                action_result = self.adapter.execute_signal(
                    symbol,
                    action,
                    lot,
                    stop_loss=intent.stop_loss,
                    take_profit=intent.take_profit,
                    open_side=open_side,
                )

        runtime.last_bar_iso = last_iso
        return {
            "id": dep_id,
            "last_bar": last_iso,
            "status": "processed",
            "signal": signal.action.value if signal else None,
            "order": action_result,
            "htf_timeframe": htf_tf or None,
        }
