"""ATR helper."""

from __future__ import annotations

from apps.strategies.patterns.bars import Bar


def compute_atr(bars: list[Bar], period: int = 14) -> list[float]:
    if not bars:
        return []
    trs: list[float] = [bars[0].high - bars[0].low]
    for i in range(1, len(bars)):
        h, l, pc = bars[i].high, bars[i].low, bars[i - 1].close
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    out: list[float] = []
    for i in range(len(bars)):
        start = max(0, i - period + 1)
        window = trs[start : i + 1]
        out.append(sum(window) / len(window) if window else trs[0])
    return out


def atr_at(atr_series: list[float], index: int, fallback: float = 0.0001) -> float:
    if 0 <= index < len(atr_series):
        v = atr_series[index]
        return v if v > 0 else fallback
    return fallback
