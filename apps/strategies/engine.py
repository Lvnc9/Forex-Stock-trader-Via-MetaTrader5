from __future__ import annotations

from collections.abc import Callable
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


class _CachedIndicatorRegistry(IndicatorRegistry):
    """IndicatorRegistry that memoizes rolling series on the full bar frame.

    Strategies still see series truncated to the current bar (iloc[:end+1]),
    so crossover helpers remain correct without recomputing SMA/RSI each bar.
    """

    def __init__(self, bars: pd.DataFrame, end_index: int, cache: dict) -> None:
        super().__init__(bars.iloc[: end_index + 1])
        self._full_bars = bars
        self._end_index = end_index
        self._cache = cache

    def _cached(self, key: tuple, factory) -> pd.Series:
        if key not in self._cache:
            self._cache[key] = factory(self._full_bars)
        return self._cache[key].iloc[: self._end_index + 1]

    def sma(self, period: int, column: str = "close") -> pd.Series:
        return self._cached(
            ("sma", period, column),
            lambda bars: bars[column].rolling(period, min_periods=period).mean(),
        )

    def ema(self, period: int, column: str = "close") -> pd.Series:
        return self._cached(
            ("ema", period, column),
            lambda bars: bars[column].ewm(span=period, adjust=False, min_periods=period).mean(),
        )

    def rsi(self, period: int = 14, column: str = "close") -> pd.Series:
        def factory(bars: pd.DataFrame) -> pd.Series:
            close = bars[column]
            delta = close.diff()
            gain = delta.clip(lower=0)
            loss = (-delta).clip(lower=0)
            avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
            rs = avg_gain / avg_loss.replace(0, pd.NA)
            return 100 - (100 / (1 + rs))

        return self._cached(("rsi", period, column), factory)

    def atr(self, period: int = 14) -> pd.Series:
        def factory(bars: pd.DataFrame) -> pd.Series:
            high = bars["high"]
            low = bars["low"]
            close = bars["close"]
            prev_close = close.shift(1)
            tr = pd.concat(
                [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
                axis=1,
            ).max(axis=1)
            return tr.rolling(period, min_periods=period).mean()

        return self._cached(("atr", period), factory)


class SignalEngine:
    """Bar-by-bar strategy runner (shared by backtester and live worker)."""

    def build_context(
        self,
        strategy: BaseStrategy,
        bars: pd.DataFrame,
        bar_index: int,
        *,
        htf_bars: pd.DataFrame | None = None,
        indicator_cache: dict | None = None,
    ) -> BarContext:
        window = bars.iloc[: bar_index + 1]
        htf_window = None
        if htf_bars is not None and not htf_bars.empty:
            ts = window.index[-1]
            htf_window = htf_bars.loc[:ts]
        if indicator_cache is not None:
            indicators: IndicatorRegistry = _CachedIndicatorRegistry(bars, bar_index, indicator_cache)
        else:
            indicators = IndicatorRegistry(window)
        return BarContext(
            bar_index=bar_index,
            timestamp=window.index[-1],
            bars=window,
            parameters=strategy.parameters,
            indicators=indicators,
            htf_bars=htf_window,
        )

    def run(
        self,
        strategy: BaseStrategy,
        bars: pd.DataFrame,
        *,
        htf_bars: pd.DataFrame | None = None,
        warmup: int | None = None,
        progress_callback: Callable[[float, str], None] | None = None,
        use_indicator_cache: bool = True,
    ) -> list[SignalEvent]:
        if bars.empty:
            return []

        min_bars = warmup if warmup is not None else self._warmup_bars(strategy)
        events: list[SignalEvent] = []
        cache: dict | None = {} if use_indicator_cache else None
        n = len(bars)
        stride = max(n // 20, 1)

        for i in range(n):
            if i + 1 < min_bars:
                continue
            ctx = self.build_context(
                strategy, bars, i, htf_bars=htf_bars, indicator_cache=cache
            )
            signal = strategy.on_bar(ctx)
            if signal is not None:
                events.append(SignalEvent(bar_index=i, timestamp=ctx.timestamp, signal=signal))
            if progress_callback is not None and (i % stride == 0 or i == n - 1):
                progress_callback((i + 1) / n * 100.0, f"Signals {i + 1}/{n}")

        return events

    def on_latest_bar(
        self,
        strategy: BaseStrategy,
        bars: pd.DataFrame,
        *,
        htf_bars: pd.DataFrame | None = None,
        warmup: int | None = None,
    ) -> Signal | None:
        """Evaluate strategy on the last closed bar only (live path)."""
        if bars.empty:
            return None
        min_bars = warmup if warmup is not None else self._warmup_bars(strategy)
        i = len(bars) - 1
        if i + 1 < min_bars:
            return None
        ctx = self.build_context(strategy, bars, i, htf_bars=htf_bars)
        return strategy.on_bar(ctx)

    @staticmethod
    def _warmup_bars(strategy: BaseStrategy) -> int:
        # Use configured int periods/lookbacks — not schema max (which blocked live
        # when MT5 fetch count was smaller than max+5, e.g. MA slow max 400 → 405).
        nums: list[int] = [2]
        params = getattr(strategy, "parameters", {}) or {}
        for spec in strategy.parameter_schema:
            if spec.get("type") != "int":
                continue
            name = spec.get("name")
            if name in params:
                nums.append(int(params[name]))
            elif "default" in spec:
                nums.append(int(spec["default"]))
        return max(nums) + 5
