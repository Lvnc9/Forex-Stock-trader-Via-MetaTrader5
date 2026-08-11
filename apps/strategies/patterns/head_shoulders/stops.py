"""Stop-loss and take-profit from H&S detection fields."""

from __future__ import annotations

from typing import Any

from apps.strategies.patterns.bars import Bar
from apps.strategies.patterns.head_shoulders.atr import atr_at, compute_atr
from apps.strategies.patterns.head_shoulders.spec import HSSpec


def compute_stops(
    detection: dict[str, Any],
    bars: list[Bar],
    spec: HSSpec,
    *,
    tp_target: str = "tp1",
    tp2_k: float | None = None,
) -> tuple[float, float]:
    """Return (stop_loss, take_profit) for the detection entry."""
    atr = compute_atr(bars, spec.atr_period)
    a = atr_at(atr, detection["head_bar_index"])
    h_val = float(detection["H"])
    entry = float(detection["entry_price"])
    rs_price = float(detection["RS_price"])
    direction = detection["direction"]

    if tp_target == "tp2":
        tp_mult = float(tp2_k if tp2_k is not None else spec.tp2_mult_h)
    else:
        tp_mult = spec.tp1_mult_h

    if direction == "top":
        stop_loss = rs_price + spec.sl_atr_buffer * a
        take_profit = entry - tp_mult * h_val
    else:
        stop_loss = rs_price - spec.sl_atr_buffer * a
        take_profit = entry + tp_mult * h_val

    return stop_loss, take_profit
