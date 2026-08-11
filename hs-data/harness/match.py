"""Match detections to labels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from harness.labels import expected_entry_bar


@dataclass
class Match:
    label: dict[str, Any]
    detection: dict[str, Any]
    head_bar_delta: int
    entry_bar_delta: int | None
    entry_matched: bool | None


def match_key(symbol: str, timeframe: str, direction: str) -> tuple[str, str, str]:
    return (symbol.upper(), timeframe.upper(), direction.lower())


def _key(symbol: str, timeframe: str, direction: str) -> tuple[str, str, str]:
    return match_key(symbol, timeframe, direction)


def match_detections(
    labels: list[dict[str, Any]],
    detections: list[dict[str, Any]],
    *,
    match_tol_bars: int,
    entry_mode: str,
) -> tuple[list[Match], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Greedy 1:1 match by symbol/TF/direction and closest head_bar within tol.

    Returns:
      matches, unmatched_true_labels, unmatched_detections, false_accepts (hard_neg matched)
    """
    dets_by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for d in detections:
        dets_by_key.setdefault(_key(d["symbol"], d["timeframe"], d["direction"]), []).append(d)

    used_det_ids: set[str] = set()
    matches: list[Match] = []
    unmatched_true: list[dict[str, Any]] = []
    false_accepts: list[dict[str, Any]] = []

    # Match true labels first (priority gold then silver)
    true_labels = [lb for lb in labels if not lb.get("hard_negative")]
    true_labels.sort(key=lambda lb: (0 if lb.get("label_quality") == "gold" else 1, lb["label_id"]))

    for lb in true_labels:
        bucket = dets_by_key.get(_key(lb["symbol"], lb["timeframe"], lb["direction"]), [])
        best = None
        best_delta = None
        for d in bucket:
            if d["detection_id"] in used_det_ids:
                continue
            delta = abs(int(d["head_bar_index"]) - int(lb["head_bar_index"]))
            if delta > match_tol_bars:
                continue
            if best is None or delta < best_delta:  # type: ignore[operator]
                best = d
                best_delta = delta
        if best is None:
            unmatched_true.append(lb)
            continue
        used_det_ids.add(best["detection_id"])
        exp_entry = expected_entry_bar(lb, entry_mode)
        det_entry = best.get("entry_bar_index")
        if det_entry is None:
            det_entry = best.get("confirmation_bar_index")
        entry_delta = None
        entry_matched = None
        if exp_entry is not None and det_entry is not None:
            entry_delta = abs(int(det_entry) - int(exp_entry))
            entry_matched = entry_delta <= match_tol_bars
        matches.append(
            Match(
                label=lb,
                detection=best,
                head_bar_delta=int(best_delta or 0),
                entry_bar_delta=entry_delta,
                entry_matched=entry_matched,
            )
        )

    # Hard negatives: if a detection lands nearby, it's a false accept
    hard_negs = [lb for lb in labels if lb.get("hard_negative")]
    for lb in hard_negs:
        bucket = dets_by_key.get(_key(lb["symbol"], lb["timeframe"], lb["direction"]), [])
        for d in bucket:
            if d["detection_id"] in used_det_ids:
                continue
            delta = abs(int(d["head_bar_index"]) - int(lb["head_bar_index"]))
            if delta <= match_tol_bars:
                used_det_ids.add(d["detection_id"])
                false_accepts.append({"label": lb, "detection": d, "head_bar_delta": delta})
                break

    unmatched_dets = [d for d in detections if d["detection_id"] not in used_det_ids]
    return matches, unmatched_true, unmatched_dets, false_accepts
