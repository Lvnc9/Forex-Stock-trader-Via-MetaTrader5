"""Main detection pipeline."""

from __future__ import annotations

from typing import Any

from apps.strategies.patterns.bars import Bar
from apps.strategies.patterns.head_shoulders.assembler import assemble_inverse, assemble_top, merge_dual_scale
from apps.strategies.patterns.head_shoulders.atr import atr_at, compute_atr
from apps.strategies.patterns.head_shoulders.confirm import find_confirmation
from apps.strategies.patterns.head_shoulders.entry import resolve_entry
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
) -> list[dict[str, Any]]:
    spec = spec or get_spec()
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

        entry = resolve_entry(cand, bars, confirm, spec, entry_mode=entry_mode)
        if entry is None:
            continue

        det_id = f"{symbol}_{timeframe}_{cand.direction}_h{cand.head.index}_{cand.scale}"
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
                "entry_mode": entry.mode,
                "entry_bar_index": entry.bar_index,
                "entry_price": entry.price,
                "retest_bar_index": entry.retest_bar_index,
                "H": geo.H,
                "score": round(geo.score, 2),
                "scale": cand.scale,
            }
        )

    by_head: dict[tuple[str, int], dict[str, Any]] = {}
    for d in detections:
        key = (d["direction"], d["head_bar_index"])
        prev = by_head.get(key)
        if prev is None or d["score"] > prev["score"]:
            by_head[key] = d
    return sorted(by_head.values(), key=lambda x: x["head_bar_index"])
