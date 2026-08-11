"""Compute MFE/MAE and TP hit rates from bars + labels."""

from __future__ import annotations

from typing import Any

from harness.bars import Bar
from harness.labels import expected_entry_bar


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


def measure_H(label: dict[str, Any]) -> float:
    if label.get("H"):
        return float(label["H"])
    nl = neckline_price_at(
        int(label["neckline_left_bar_index"]),
        float(label["neckline_left_price"]),
        int(label["neckline_right_bar_index"]),
        float(label["neckline_right_price"]),
        int(label["head_bar_index"]),
    )
    return abs(float(label["head_price"]) - nl)


def compute_outcomes(
    label: dict[str, Any],
    bars: list[Bar],
    *,
    outcome_bars: int,
    entry_mode: str,
    tp2_mult_h: float = 0.51,
) -> dict[str, Any]:
    """
    From entry bar, scan next N bars for:
      hit_0_5H, hit_kH (TP2), hit_1_0H, mfe, mae
    Direction: top = short (favor down); inverse = long (favor up).
    Targets measured from entry price by 0.5H / k×H / 1.0H.
    """
    H = measure_H(label)
    entry_i = expected_entry_bar(label, entry_mode)
    if entry_i is None:
        return {
            "outcome_bars": outcome_bars,
            "hit_0_5H": None,
            "hit_kH": None,
            "hit_1_0H": None,
            "mfe": None,
            "mae": None,
            "error": "no_entry_bar",
        }
    if entry_i < 0 or entry_i >= len(bars):
        return {
            "outcome_bars": outcome_bars,
            "hit_0_5H": None,
            "hit_kH": None,
            "hit_1_0H": None,
            "mfe": None,
            "mae": None,
            "error": "entry_out_of_range",
        }

    entry_price = label.get("entry_price")
    if entry_price is None:
        entry_price = bars[entry_i].close
    else:
        entry_price = float(entry_price)

    direction = label["direction"]
    # Failure trades are opposite of classic: top failure → long; inverse failure → short.
    long_side = (direction == "inverse") if label.get("trade_kind") != "failure" else (direction == "top")
    end = min(len(bars) - 1, entry_i + outcome_bars)
    mfe = 0.0
    mae = 0.0
    hit_05 = False
    hit_k = False
    hit_10 = False

    if long_side:
        tp05 = entry_price + 0.5 * H
        tpk = entry_price + tp2_mult_h * H
        tp10 = entry_price + 1.0 * H
    else:
        tp05 = entry_price - 0.5 * H
        tpk = entry_price - tp2_mult_h * H
        tp10 = entry_price - 1.0 * H

    for i in range(entry_i + 1, end + 1):
        bar = bars[i]
        if long_side:
            fav = bar.high - entry_price
            adv = entry_price - bar.low
            if bar.high >= tp05:
                hit_05 = True
            if bar.high >= tpk:
                hit_k = True
            if bar.high >= tp10:
                hit_10 = True
        else:
            fav = entry_price - bar.low
            adv = bar.high - entry_price
            if bar.low <= tp05:
                hit_05 = True
            if bar.low <= tpk:
                hit_k = True
            if bar.low <= tp10:
                hit_10 = True
        if fav > mfe:
            mfe = fav
        if adv > mae:
            mae = adv

    return {
        "outcome_bars": outcome_bars,
        "entry_bar_index": entry_i,
        "entry_price": entry_price,
        "H": H,
        "trade_kind": label.get("trade_kind") or "classic",
        "long_side": long_side,
        "tp_0_5H": tp05,
        "tp_kH": tpk,
        "tp_1_0H": tp10,
        "tp2_mult_h": tp2_mult_h,
        "hit_0_5H": hit_05,
        "hit_kH": hit_k,
        "hit_1_0H": hit_10,
        "mfe": mfe,
        "mae": mae,
        "error": None,
    }
