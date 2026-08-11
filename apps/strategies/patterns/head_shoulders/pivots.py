"""Dual-scale swing pivot detection."""

from __future__ import annotations

from dataclasses import dataclass

from apps.strategies.patterns.bars import Bar
from apps.strategies.patterns.head_shoulders.atr import atr_at, compute_atr
from apps.strategies.patterns.head_shoulders.spec import HSSpec


@dataclass(frozen=True)
class Pivot:
    index: int
    price: float
    kind: str  # "high" | "low"
    scale: str  # "short" | "medium"


def _is_pivot_high(bars: list[Bar], i: int, left: int, right: int) -> bool:
    hi = bars[i].high
    for j in range(i - left, i):
        if bars[j].high >= hi:
            return False
    for j in range(i + 1, i + right + 1):
        if j >= len(bars) or bars[j].high >= hi:
            return False
    return True


def _is_pivot_low(bars: list[Bar], i: int, left: int, right: int) -> bool:
    lo = bars[i].low
    for j in range(i - left, i):
        if bars[j].low <= lo:
            return False
    for j in range(i + 1, i + right + 1):
        if j >= len(bars) or bars[j].low <= lo:
            return False
    return True


def find_pivots(bars: list[Bar], spec: HSSpec, scale: str, swing_l: int) -> list[Pivot]:
    atr = compute_atr(bars, spec.atr_period)
    pivots: list[Pivot] = []
    for i in range(swing_l, len(bars) - swing_l):
        a = atr_at(atr, i)
        if _is_pivot_high(bars, i, swing_l, swing_l):
            amp = bars[i].high - min(bars[i - swing_l : i + swing_l + 1], key=lambda b: b.low).low
            if amp >= spec.min_pivot_atr * a:
                pivots.append(Pivot(i, bars[i].high, "high", scale))
        if _is_pivot_low(bars, i, swing_l, swing_l):
            amp = max(bars[i - swing_l : i + swing_l + 1], key=lambda b: b.high).high - bars[i].low
            if amp >= spec.min_pivot_atr * a:
                pivots.append(Pivot(i, bars[i].low, "low", scale))
    return pivots


def find_all_pivots(bars: list[Bar], spec: HSSpec) -> tuple[list[Pivot], list[Pivot]]:
    short = find_pivots(bars, spec, "short", spec.swing_l_short)
    medium = find_pivots(bars, spec, "medium", spec.swing_l_medium)
    return short, medium
