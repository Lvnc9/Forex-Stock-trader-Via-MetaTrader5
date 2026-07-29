from __future__ import annotations

import pandas as pd


def _series(bars: pd.DataFrame, column: str) -> pd.Series:
    if column not in bars.columns:
        raise KeyError(f"Column {column!r} not in OHLCV frame")
    return bars[column]


class IndicatorRegistry:
    """Indicator helpers over a growing OHLCV window (shared backtest + live)."""

    def __init__(self, bars: pd.DataFrame) -> None:
        self._bars = bars

    @property
    def bars(self) -> pd.DataFrame:
        return self._bars

    def sma(self, period: int, column: str = "close") -> pd.Series:
        return _series(self._bars, column).rolling(period, min_periods=period).mean()

    def ema(self, period: int, column: str = "close") -> pd.Series:
        return _series(self._bars, column).ewm(span=period, adjust=False, min_periods=period).mean()

    def rsi(self, period: int = 14, column: str = "close") -> pd.Series:
        close = _series(self._bars, column)
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, pd.NA)
        return 100 - (100 / (1 + rs))

    def macd(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        column: str = "close",
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        close = _series(self._bars, column)
        macd_line = self.ema(fast, column) - self.ema(slow, column)
        signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
        hist = macd_line - signal_line
        return macd_line, signal_line, hist

    def bollinger(
        self, period: int = 20, std_dev: float = 2.0, column: str = "close"
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        mid = self.sma(period, column)
        std = _series(self._bars, column).rolling(period, min_periods=period).std()
        upper = mid + std_dev * std
        lower = mid - std_dev * std
        return lower, mid, upper

    def atr(self, period: int = 14) -> pd.Series:
        high = _series(self._bars, "high")
        low = _series(self._bars, "low")
        close = _series(self._bars, "close")
        prev_close = close.shift(1)
        tr = pd.concat(
            [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
            axis=1,
        ).max(axis=1)
        return tr.rolling(period, min_periods=period).mean()

    @staticmethod
    def crossed_above(fast: pd.Series, slow: pd.Series) -> bool:
        if len(fast) < 2 or len(slow) < 2:
            return False
        return bool(fast.iloc[-2] <= slow.iloc[-2] and fast.iloc[-1] > slow.iloc[-1])

    @staticmethod
    def crossed_below(fast: pd.Series, slow: pd.Series) -> bool:
        if len(fast) < 2 or len(slow) < 2:
            return False
        return bool(fast.iloc[-2] >= slow.iloc[-2] and fast.iloc[-1] < slow.iloc[-1])

    def value(self, series: pd.Series) -> float | None:
        if series.empty or pd.isna(series.iloc[-1]):
            return None
        return float(series.iloc[-1])
