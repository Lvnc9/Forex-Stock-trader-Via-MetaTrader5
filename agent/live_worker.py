from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.bootstrap import ensure_repo_root

ensure_repo_root()

from apps.strategies.context import BarContext  # noqa: E402
from apps.strategies.indicators.registry import IndicatorRegistry  # noqa: E402
from apps.strategies.loader import instantiate_strategy  # noqa: E402
from apps.strategies.signals import Signal  # noqa: E402


@dataclass
class DeploymentRuntime:
    deployment_id: int
    last_bar_iso: str | None = None


@dataclass
class LiveWorker:
    adapter: Any
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

        window = bars
        ctx = BarContext(
            bar_index=len(window) - 1,
            timestamp=last_ts,
            bars=window,
            parameters=strategy.parameters,
            indicators=IndicatorRegistry(window),
        )
        signal: Signal | None = strategy.on_bar(ctx)
        action_result = None
        if signal is not None:
            action_result = self.adapter.execute_signal(symbol, signal.action.value, lot)

        runtime.last_bar_iso = last_iso
        return {
            "id": dep_id,
            "last_bar": last_iso,
            "status": "processed",
            "signal": signal.action.value if signal else None,
            "order": action_result,
        }
