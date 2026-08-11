"""Entry modes A (confirm close) and B (retest rejection)."""

from __future__ import annotations

from dataclasses import dataclass

from apps.strategies.patterns.bars import Bar
from apps.strategies.patterns.head_shoulders.assembler import PatternCandidate
from apps.strategies.patterns.head_shoulders.confirm import Confirmation
from apps.strategies.patterns.head_shoulders.neckline import neckline_price_at
from apps.strategies.patterns.head_shoulders.spec import HSSpec


@dataclass
class Entry:
    mode: str
    bar_index: int
    price: float
    retest_bar_index: int | None = None


def resolve_entry(
    candidate: PatternCandidate,
    bars: list[Bar],
    confirm: Confirmation,
    spec: HSSpec,
    *,
    entry_mode: str = "A",
) -> Entry | None:
    if entry_mode == "A":
        if spec.enter_next_open and confirm.bar_index + 1 < len(bars):
            nxt = confirm.bar_index + 1
            return Entry("A", nxt, bars[nxt].open)
        return Entry("A", confirm.bar_index, confirm.price)

    level = confirm.price
    if confirm.confirm_rule == "close_beyond_neckline":
        level = neckline_price_at(
            candidate.armpit1.index,
            candidate.armpit1.price,
            candidate.armpit2.index,
            candidate.armpit2.price,
            confirm.bar_index,
        )
    else:
        level = candidate.armpit2.price

    for i in range(confirm.bar_index + 1, min(len(bars), confirm.bar_index + spec.retest_max_bars + 1)):
        bar = bars[i]
        if candidate.direction == "top":
            touched = bar.high >= level
            rejected = bar.close < level
        else:
            touched = bar.low <= level
            rejected = bar.close > level
        if touched and rejected:
            return Entry("B", i, bar.close, retest_bar_index=i)
    return None
