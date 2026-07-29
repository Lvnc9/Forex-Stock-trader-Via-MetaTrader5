from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext
from apps.strategies.indicators.registry import IndicatorRegistry
from apps.strategies.signals import Signal


@dataclass(frozen=True)
class SignalEvent:
    bar_index: int
    timestamp: pd.Timestamp
    signal: Signal


class SignalEngine:
    """Bar-by-bar strategy runner (used by backtester and live worker)."""

    def run(
        self,
        strategy: BaseStrategy,
        bars: pd.DataFrame,
        *,
        htf_bars: pd.DataFrame | None = None,
        warmup: int | None = None,
    ) -> list[SignalEvent]:
        if bars.empty:
            return []

        min_bars = warmup if warmup is not None else self._warmup_bars(strategy)
        events: list[SignalEvent] = []

        for i in range(len(bars)):
            if i + 1 < min_bars:
                continue
            window = bars.iloc[: i + 1]
            htf_window = None
            if htf_bars is not None and not htf_bars.empty:
                ts = window.index[-1]
                htf_window = htf_bars.loc[:ts]

            ctx = BarContext(
                bar_index=i,
                timestamp=window.index[-1],
                bars=window,
                parameters=strategy.parameters,
                indicators=IndicatorRegistry(window),
                htf_bars=htf_window,
            )
            signal = strategy.on_bar(ctx)
            if signal is not None:
                events.append(SignalEvent(bar_index=i, timestamp=ctx.timestamp, signal=signal))

        return events

    @staticmethod
    def _warmup_bars(strategy: BaseStrategy) -> int:
        nums: list[int] = [2]
        for spec in strategy.parameter_schema:
            if spec.get("type") in ("int", "float"):
                nums.append(int(spec.get("max", spec.get("default", 2))))
        return max(nums) + 5
