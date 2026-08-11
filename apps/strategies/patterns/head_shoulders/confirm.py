"""Neckline confirmation (bar close only)."""

from __future__ import annotations

from dataclasses import dataclass

from apps.strategies.patterns.bars import Bar
from apps.strategies.patterns.head_shoulders.assembler import PatternCandidate
from apps.strategies.patterns.head_shoulders.neckline import neckline_price_at
from apps.strategies.patterns.head_shoulders.spec import HSSpec


@dataclass
class Confirmation:
    bar_index: int
    price: float
    confirm_rule: str


def find_confirmation(
    candidate: PatternCandidate,
    bars: list[Bar],
    spec: HSSpec,
    atr: float,
    neckline_slope: str,
    *,
    search_after: int | None = None,
) -> Confirmation | None:
    start = (search_after if search_after is not None else candidate.rs.index) + 1
    a1_i, a1_p = candidate.armpit1.index, candidate.armpit1.price
    a2_i, a2_p = candidate.armpit2.index, candidate.armpit2.price
    nk = neckline_slope

    for i in range(start, len(bars)):
        close = bars[i].close
        nl = neckline_price_at(a1_i, a1_p, a2_i, a2_p, i)

        if candidate.direction == "top":
            if nk in ("up", "flat"):
                if close < nl:
                    return Confirmation(i, close, "close_beyond_neckline")
            elif close < a2_p:
                return Confirmation(i, close, "close_beyond_right_armpit")
        else:
            if nk in ("down", "flat"):
                if close > nl:
                    return Confirmation(i, close, "close_beyond_neckline")
            elif close > a2_p:
                return Confirmation(i, close, "close_beyond_right_armpit")
    return None
