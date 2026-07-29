from dataclasses import dataclass

import pandas as pd

from apps.strategies.indicators.registry import IndicatorRegistry


@dataclass
class BarContext:
    """Snapshot passed to ``BaseStrategy.on_bar`` for one closed bar."""

    bar_index: int
    timestamp: pd.Timestamp
    bars: pd.DataFrame
    parameters: dict
    indicators: IndicatorRegistry
    htf_bars: pd.DataFrame | None = None

    @property
    def close(self) -> float:
        return float(self.bars["close"].iloc[-1])

    @property
    def open(self) -> float:
        return float(self.bars["open"].iloc[-1])

    @property
    def high(self) -> float:
        return float(self.bars["high"].iloc[-1])

    @property
    def low(self) -> float:
        return float(self.bars["low"].iloc[-1])
