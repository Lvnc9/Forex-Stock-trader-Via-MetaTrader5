"""Neckline price and slope helpers."""

from __future__ import annotations


def neckline_price_at(
    left_i: int,
    left_p: float,
    right_i: int,
    right_p: float,
    at_i: int,
) -> float:
    if right_i == left_i:
        return float(left_p)
    t = (at_i - left_i) / (right_i - left_i)
    return float(left_p) + t * (float(right_p) - float(left_p))


def neckline_slope_norm(
    left_i: int,
    left_p: float,
    right_i: int,
    right_p: float,
    atr: float,
) -> float:
    if right_i == left_i or atr <= 0:
        return 0.0
    return abs(float(right_p) - float(left_p)) / (abs(right_i - left_i) * atr)


def neckline_kind(left_p: float, right_p: float, flat_eps_atr: float, atr: float) -> str:
    diff = float(right_p) - float(left_p)
    if abs(diff) <= flat_eps_atr * atr:
        return "flat"
    return "up" if diff > 0 else "down"
