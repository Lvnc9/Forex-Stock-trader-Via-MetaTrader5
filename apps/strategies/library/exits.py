"""Optional percentage-based SL/TP helpers for library strategies."""

from __future__ import annotations


# Shared optional params: 0 means omit (no broker/backtest SL or TP).
SL_TP_DEFAULTS = {"stop_loss_pct": 0.0, "take_profit_pct": 0.0}
SL_TP_SCHEMA = [
    {"name": "stop_loss_pct", "type": "float", "min": 0.0, "max": 50.0, "default": 0.0},
    {"name": "take_profit_pct", "type": "float", "min": 0.0, "max": 100.0, "default": 0.0},
]


def levels_from_pct(
    close: float,
    *,
    is_long: bool,
    stop_loss_pct: float,
    take_profit_pct: float,
) -> tuple[float | None, float | None]:
    """Return absolute stop_loss / take_profit prices, or None when pct <= 0."""
    sl: float | None = None
    tp: float | None = None
    if stop_loss_pct > 0:
        frac = stop_loss_pct / 100.0
        sl = close * (1.0 - frac) if is_long else close * (1.0 + frac)
    if take_profit_pct > 0:
        frac = take_profit_pct / 100.0
        tp = close * (1.0 + frac) if is_long else close * (1.0 - frac)
    return sl, tp
