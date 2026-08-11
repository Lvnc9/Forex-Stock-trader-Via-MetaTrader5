"""Main detection pipeline."""

from __future__ import annotations

from typing import Any

from apps.strategies.patterns.bars import Bar
from apps.strategies.patterns.head_shoulders.assembler import assemble_inverse, assemble_top, merge_dual_scale
from apps.strategies.patterns.head_shoulders.atr import atr_at, compute_atr
from apps.strategies.patterns.head_shoulders.confirm import find_confirmation
from apps.strategies.patterns.head_shoulders.entry import resolve_entry
from apps.strategies.patterns.head_shoulders.failure import find_failure
from apps.strategies.patterns.head_shoulders.geometry import evaluate_geometry
from apps.strategies.patterns.head_shoulders.pivots import find_all_pivots
from apps.strategies.patterns.head_shoulders.spec import HSSpec, get_spec


def _dual_scale_hit(head_index: int, short_heads: set[int], medium_heads: set[int], merge: int) -> bool:
    for h in short_heads:
        if abs(h - head_index) <= merge:
            return True
    for h in medium_heads:
        if abs(h - head_index) <= merge:
            return True
    return head_index in short_heads and head_index in medium_heads


def detect_on_bars(
    bars: list[Bar],
    symbol: str,
    timeframe: str,
    spec: HSSpec | None = None,
    *,
    entry_mode: str = "A",
    trade_mode: str = "classic",
) -> list[dict[str, Any]]:
    """
    Detect H&S patterns.

    trade_mode:
      - classic: enter on neckline confirmation (legacy)
      - failure: confirm structure, then enter only on Bulkowski-style bust
    """
    spec = spec or get_spec()
    mode = (trade_mode or "classic").lower()
    short, medium = find_all_pivots(bars, spec)
    short_heads = {p.index for p in short if p.kind == "high"} | {p.index for p in short if p.kind == "low"}
    medium_heads = {p.index for p in medium if p.kind == "high"} | {p.index for p in medium if p.kind == "low"}

    tops = assemble_top(short, medium, spec)
    inverses = assemble_inverse(short, medium, spec)
    candidates = merge_dual_scale(tops, inverses, spec)

    atr = compute_atr(bars, spec.atr_period)
    detections: list[dict[str, Any]] = []

    for cand in candidates:
        dsh = _dual_scale_hit(cand.head.index, short_heads, medium_heads, spec.merge_head_bars)
        geo = evaluate_geometry(cand, bars, spec, dual_scale_hit=dsh)
        if not geo.valid:
            continue

        a = atr_at(atr, cand.head.index)
        confirm = find_confirmation(cand, bars, spec, a, geo.neckline_slope)
        if confirm is None:
            continue

        if mode == "failure":
            failure = find_failure(
                cand,
                bars,
                confirm,
                spec,
                a,
                failure_level=spec.failure_entry_level,
            )
            if failure is None:
                continue
            entry_bar_index = failure.bar_index
            entry_price = failure.price
            entry_mode_out = "failure"
            retest_bar_index = None
            failure_fields = {
                "trade_kind": "failure",
                "failure_level": failure.failure_level,
                "failure_bar_index": failure.bar_index,
                "failure_price": failure.price,
                "failed_extreme_price": failure.failed_extreme,
                "max_adverse": failure.max_adverse,
            }
        else:
            entry = resolve_entry(cand, bars, confirm, spec, entry_mode=entry_mode)
            if entry is None:
                continue
            entry_bar_index = entry.bar_index
            entry_price = entry.price
            entry_mode_out = entry.mode
            retest_bar_index = entry.retest_bar_index
            failure_fields = {
                "trade_kind": "classic",
                "failure_level": None,
                "failure_bar_index": None,
                "failure_price": None,
                "failed_extreme_price": None,
                "max_adverse": None,
            }

        det_id = f"{symbol}_{timeframe}_{cand.direction}_h{cand.head.index}_{cand.scale}"
        if mode == "failure":
            det_id = f"{det_id}_fail"
        detections.append(
            {
                "detection_id": det_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "direction": cand.direction,
                "LS_bar_index": cand.ls.index,
                "LS_price": cand.ls.price,
                "trough1_bar_index": cand.armpit1.index,
                "trough1_price": cand.armpit1.price,
                "head_bar_index": cand.head.index,
                "head_price": cand.head.price,
                "trough2_bar_index": cand.armpit2.index,
                "trough2_price": cand.armpit2.price,
                "RS_bar_index": cand.rs.index,
                "RS_price": cand.rs.price,
                "neckline_left_bar_index": cand.armpit1.index,
                "neckline_left_price": cand.armpit1.price,
                "neckline_right_bar_index": cand.armpit2.index,
                "neckline_right_price": cand.armpit2.price,
                "confirmation_bar_index": confirm.bar_index,
                "confirmation_price": confirm.price,
                "confirm_rule": confirm.confirm_rule,
                "entry_mode": entry_mode_out,
                "entry_bar_index": entry_bar_index,
                "entry_price": entry_price,
                "retest_bar_index": retest_bar_index,
                "H": geo.H,
                "score": round(geo.score, 2),
                "scale": cand.scale,
                **failure_fields,
            }
        )

    by_head: dict[tuple[str, int], dict[str, Any]] = {}
    for d in detections:
        key = (d["direction"], d["head_bar_index"])
        prev = by_head.get(key)
        if prev is None or d["score"] > prev["score"]:
            by_head[key] = d
    return sorted(by_head.values(), key=lambda x: x["head_bar_index"])
