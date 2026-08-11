"""Aggregate precision/recall/F1 and TP rates."""

from __future__ import annotations

from typing import Any

from harness.match import Match, match_key


def _safe_div(n: float, d: float) -> float | None:
    if d == 0:
        return None
    return n / d


def compute_detection_metrics(
    *,
    n_true_labels: int,
    matches: list[Match],
    unmatched_true: list[dict[str, Any]],
    unmatched_detections: list[dict[str, Any]],
    false_accepts: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    TP = matched true labels
    FP = unmatched detections + false accepts on hard negatives
    FN = unmatched true labels
    """
    tp = len(matches)
    fp = len(unmatched_detections) + len(false_accepts)
    fn = len(unmatched_true)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    if precision is None or recall is None or (precision + recall) == 0:
        f1 = None
    else:
        f1 = 2 * precision * recall / (precision + recall)

    entry_considered = [m for m in matches if m.entry_matched is not None]
    entry_hits = sum(1 for m in entry_considered if m.entry_matched)
    entry_rate = _safe_div(entry_hits, len(entry_considered))

    return {
        "n_true_labels": n_true_labels,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "missed_label_ids": [lb["label_id"] for lb in unmatched_true],
        "false_accept_label_ids": [fa["label"]["label_id"] for fa in false_accepts],
        "unmatched_detection_ids": [d["detection_id"] for d in unmatched_detections],
        "entry_bar_match_rate": entry_rate,
        "entry_bar_match_n": len(entry_considered),
        "entry_bar_match_hits": entry_hits,
    }


def compute_tp_rates(per_label_outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [o for o in per_label_outcomes if o.get("hit_0_5H") is not None]
    n = len(usable)
    hit05 = sum(1 for o in usable if o["hit_0_5H"])
    hit_k = sum(1 for o in usable if o.get("hit_kH"))
    hit10 = sum(1 for o in usable if o["hit_1_0H"])
    tp2_mult = usable[0].get("tp2_mult_h", 0.51) if usable else 0.51
    return {
        "n_labels_with_outcomes": n,
        "tp2_mult_h": tp2_mult,
        "hit_0_5H_rate": _safe_div(hit05, n),
        "hit_kH_rate": _safe_div(hit_k, n),
        "hit_1_0H_rate": _safe_div(hit10, n),
        "hit_0_5H_count": hit05,
        "hit_kH_count": hit_k,
        "hit_1_0H_count": hit10,
        "note": "Rates computed on OUR bars from label entry; not Bulkowski equity figures.",
    }


def compute_premature_entry_rate(
    labels: list[dict[str, Any]],
    detections: list[dict[str, Any]],
    *,
    match_tol_bars: int,
) -> dict[str, Any]:
    """
    E5: On labels tagged premature_entry_test, fraction where a nearby detection
    enters before confirmation (entry_bar_index < confirmation_bar_index).
    """
    test_labels = [
        lb
        for lb in labels
        if lb.get("premature_entry_test") is True
        or (isinstance(lb.get("notes"), str) and "premature_entry_test" in lb["notes"])
    ]
    if not test_labels:
        return {
            "n_premature_test_labels": 0,
            "premature_violations": 0,
            "premature_entry_rate": None,
            "note": "No premature_entry_test labels found",
        }

    dets_by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for d in detections:
        dets_by_key.setdefault(match_key(d["symbol"], d["timeframe"], d["direction"]), []).append(d)

    violations = 0
    for lb in test_labels:
        bucket = dets_by_key.get(match_key(lb["symbol"], lb["timeframe"], lb["direction"]), [])
        for d in bucket:
            delta = abs(int(d["head_bar_index"]) - int(lb["head_bar_index"]))
            if delta > match_tol_bars:
                continue
            entry_i = d.get("entry_bar_index")
            confirm_i = d.get("confirmation_bar_index")
            if entry_i is None or confirm_i is None:
                continue
            if int(entry_i) < int(confirm_i):
                violations += 1
                break
            # Also flag RS-bar entry
            if int(entry_i) <= int(lb["RS_bar_index"]) and int(entry_i) < int(confirm_i):
                violations += 1
                break

    n = len(test_labels)
    return {
        "n_premature_test_labels": n,
        "premature_violations": violations,
        "premature_entry_rate": _safe_div(violations, n),
        "note": "E5 gate: rate should be ≤ 0.10 TUNABLE",
    }


def detector_premature_rate(detections: list[dict[str, Any]]) -> dict[str, Any]:
    """All detections where entry precedes confirmation (or failure reclaim)."""
    considered = [
        d
        for d in detections
        if d.get("entry_bar_index") is not None and d.get("confirmation_bar_index") is not None
    ]
    bad = 0
    for d in considered:
        entry_i = int(d["entry_bar_index"])
        confirm_i = int(d["confirmation_bar_index"])
        if d.get("trade_kind") == "failure":
            if entry_i <= confirm_i:
                bad += 1
                continue
            fail_i = d.get("failure_bar_index")
            if fail_i is not None and entry_i < int(fail_i):
                bad += 1
        elif entry_i < confirm_i:
            bad += 1
    return {
        "n_detections_with_entry": len(considered),
        "premature_count": bad,
        "premature_rate": _safe_div(bad, len(considered)),
    }


def compute_failure_gates(
    labels: list[dict[str, Any]],
    detections: list[dict[str, Any]],
    *,
    match_tol_bars: int,
) -> dict[str, Any]:
    """
    Failure-only gates vs trade_kind=failure labels.
    classic_leak_count should be 0 when evaluating a failure-mode export.
    """
    fail_labels = [
        lb
        for lb in labels
        if not lb.get("hard_negative") and lb.get("trade_kind") == "failure"
    ]
    fail_dets = [d for d in detections if d.get("trade_kind") == "failure"]
    classic_leaks = [d for d in detections if d.get("trade_kind") == "classic"]

    used: set[str] = set()
    tp = 0
    for lb in fail_labels:
        best = None
        best_delta = None
        for d in fail_dets:
            if d["detection_id"] in used:
                continue
            if d["symbol"].upper() != str(lb["symbol"]).upper():
                continue
            if d["timeframe"].upper() != str(lb["timeframe"]).upper():
                continue
            if d["direction"] != lb["direction"]:
                continue
            delta = abs(int(d["head_bar_index"]) - int(lb["head_bar_index"]))
            if delta > match_tol_bars:
                continue
            if best is None or delta < best_delta:  # type: ignore[operator]
                best = d
                best_delta = delta
        if best is not None:
            used.add(best["detection_id"])
            tp += 1
    fp = max(0, len(fail_dets) - tp)
    fn = max(0, len(fail_labels) - tp)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)

    premature = sum(
        1
        for d in fail_dets
        if int(d["entry_bar_index"]) <= int(d["confirmation_bar_index"])
    )

    return {
        "n_failure_labels": len(fail_labels),
        "n_failure_detections": len(fail_dets),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "premature_failure_count": premature,
        "premature_failure_rate": _safe_div(premature, len(fail_dets)),
        "classic_leak_count": len(classic_leaks),
        "classic_false_trade_rate": _safe_div(len(classic_leaks), max(len(detections), 1)),
        "gates": {
            "precision_floor": 0.45,
            "recall_floor": 0.55,
            "premature_max": 0.10,
            "classic_leak_max": 0.0,
        },
    }
