"""Bulkowski-style H&S failure / bust entry after classic confirmation."""

from __future__ import annotations

from dataclasses import dataclass

from apps.strategies.patterns.bars import Bar
from apps.strategies.patterns.head_shoulders.assembler import PatternCandidate
from apps.strategies.patterns.head_shoulders.confirm import Confirmation
from apps.strategies.patterns.head_shoulders.neckline import neckline_price_at
from apps.strategies.patterns.head_shoulders.spec import HSSpec


@dataclass(frozen=True)
class FailureEntry:
    bar_index: int
    price: float
    failure_level: str
    failed_extreme: float
    max_adverse: float
    status: str = "failed"


def _failure_level_price(
    candidate: PatternCandidate,
    bars: list[Bar],
    confirm: Confirmation,
    level: str,
) -> float:
    if level == "head":
        return float(candidate.head.price)
    if level == "rs":
        return float(candidate.rs.price)
    # neckline reclaim at the bar we will evaluate (use confirm bar as baseline;
    # caller re-evaluates with bar index via neckline_price_at when needed).
    return neckline_price_at(
        candidate.armpit1.index,
        candidate.armpit1.price,
        candidate.armpit2.index,
        candidate.armpit2.price,
        confirm.bar_index,
    )


def find_failure(
    candidate: PatternCandidate,
    bars: list[Bar],
    confirm: Confirmation,
    spec: HSSpec,
    atr: float,
    *,
    failure_level: str | None = None,
) -> FailureEntry | None:
    """
    After classic confirmation, watch for a bust.

    Top: adverse = breakout_price - bar.low; failure = close > level.
    Inverse: adverse = bar.high - breakout_price; failure = close < level.
    If adverse exceeds max_bust_atr * ATR before failure → dead (None).
    """
    level_name = (failure_level or spec.failure_entry_level or "head").lower()
    if level_name not in ("head", "rs", "neckline"):
        level_name = "head"

    breakout = float(confirm.price)
    max_allowed = float(spec.max_bust_atr) * float(atr)
    if max_allowed <= 0:
        return None

    start = confirm.bar_index + 1
    end = min(len(bars), confirm.bar_index + int(spec.failure_max_watch_bars) + 1)
    max_adverse = 0.0
    failed_extreme = breakout

    for i in range(start, end):
        bar = bars[i]
        if candidate.direction == "top":
            # Dead check uses close (bar-close system); SL extreme still tracks lows.
            adverse_close = breakout - float(bar.close)
            max_adverse = max(max_adverse, breakout - float(bar.low))
            failed_extreme = min(failed_extreme, float(bar.low))
            if adverse_close > max_allowed:
                return None

            if level_name == "neckline":
                level_px = neckline_price_at(
                    candidate.armpit1.index,
                    candidate.armpit1.price,
                    candidate.armpit2.index,
                    candidate.armpit2.price,
                    i,
                )
            else:
                level_px = _failure_level_price(candidate, bars, confirm, level_name)

            if float(bar.close) > level_px:
                entry_i = i
                entry_px = float(bar.close)
                if spec.failure_enter_next_open and i + 1 < len(bars):
                    entry_i = i + 1
                    entry_px = float(bars[entry_i].open)
                return FailureEntry(
                    bar_index=entry_i,
                    price=entry_px,
                    failure_level=level_name,
                    failed_extreme=failed_extreme,
                    max_adverse=max_adverse,
                )
        else:
            adverse_close = float(bar.close) - breakout
            max_adverse = max(max_adverse, float(bar.high) - breakout)
            failed_extreme = max(failed_extreme, float(bar.high))
            if adverse_close > max_allowed:
                return None

            if level_name == "neckline":
                level_px = neckline_price_at(
                    candidate.armpit1.index,
                    candidate.armpit1.price,
                    candidate.armpit2.index,
                    candidate.armpit2.price,
                    i,
                )
            else:
                level_px = _failure_level_price(candidate, bars, confirm, level_name)

            if float(bar.close) < level_px:
                entry_i = i
                entry_px = float(bar.close)
                if spec.failure_enter_next_open and i + 1 < len(bars):
                    entry_i = i + 1
                    entry_px = float(bars[entry_i].open)
                return FailureEntry(
                    bar_index=entry_i,
                    price=entry_px,
                    failure_level=level_name,
                    failed_extreme=failed_extreme,
                    max_adverse=max_adverse,
                )

    return None
