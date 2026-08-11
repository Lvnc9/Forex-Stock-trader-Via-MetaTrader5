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
    """Return (stop_loss, take_profit) for classic neckline entries."""
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


def compute_failure_stops(
    detection: dict[str, Any],
    bars: list[Bar],
    spec: HSSpec,
    *,
    tp_target: str = "tp1",
    tp2_k: float | None = None,
) -> tuple[float, float]:
    """
    Stops for failure / bust trades (opposite of classic).

    Top failure → long: SL below failed breakdown extreme; TP projects H up.
    Inverse failure → short: SL above failed breakout extreme; TP projects H down.
    """
    atr = compute_atr(bars, spec.atr_period)
    a = atr_at(atr, detection["head_bar_index"])
    h_val = float(detection["H"])
    entry = float(detection["entry_price"])
    direction = detection["direction"]

    extreme = detection.get("failed_extreme_price")
    if extreme is None:
        confirm_i = int(detection["confirmation_bar_index"])
        entry_i = int(detection["entry_bar_index"])
        lo = min(confirm_i, entry_i)
        hi = max(confirm_i, entry_i)
        if direction == "top":
            extreme = min(float(bars[j].low) for j in range(lo, hi + 1))
        else:
            extreme = max(float(bars[j].high) for j in range(lo, hi + 1))
    extreme = float(extreme)

    if tp_target == "tp2":
        tp_mult = float(tp2_k if tp2_k is not None else spec.tp2_mult_h)
    else:
        tp_mult = spec.tp1_mult_h

    if direction == "top":
        # Failed top → long continuation
        stop_loss = extreme - spec.sl_atr_buffer * a
        take_profit = entry + tp_mult * h_val
    else:
        # Failed inverse → short continuation
        stop_loss = extreme + spec.sl_atr_buffer * a
        take_profit = entry - tp_mult * h_val

    return stop_loss, take_profit
