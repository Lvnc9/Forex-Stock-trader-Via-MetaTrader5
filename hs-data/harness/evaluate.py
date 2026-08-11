"""CLI: evaluate detector export against labels + bars."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness.bars import load_bars_for_label
from harness.detections import load_detections
from harness.labels import load_labels
from harness.match import match_detections
from harness.metrics import (
    compute_detection_metrics,
    compute_failure_gates,
    compute_premature_entry_rate,
    compute_tp_rates,
    detector_premature_rate,
)
from harness.outcomes import compute_outcomes


def _md_scorecard(card: dict[str, Any]) -> str:
    det = card["detection_metrics"]
    tp = card["tp_metrics"]

    def pct(x: float | None) -> str:
        if x is None:
            return "n/a"
        return f"{100.0 * x:.1f}%"

    lines = [
        "# H&S harness scorecard",
        "",
        f"- Generated: `{card['generated_at']}`",
        f"- Entry mode: `{card['entry_mode']}`",
        f"- Match tol (bars): `{card['match_tol_bars']}`",
        f"- Outcome bars: `{card['outcome_bars']}`",
        "",
        "## Detection quality (Bug A — recall)",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| True labels | {det['n_true_labels']} |",
        f"| TP / FP / FN | {det['tp']} / {det['fp']} / {det['fn']} |",
        f"| Precision | {pct(det['precision'])} |",
        f"| Recall | {pct(det['recall'])} |",
        f"| F1 | {pct(det['f1']) if det['f1'] is not None else 'n/a'} |",
        "",
        f"Missed label IDs ({len(det['missed_label_ids'])}):",
        "",
    ]
    if det["missed_label_ids"]:
        for lid in det["missed_label_ids"]:
            lines.append(f"- `{lid}`")
    else:
        lines.append("- (none)")

    lines += [
        "",
        "## Entry timing (Bug B)",
        "",
        f"- entry_bar_match_rate: **{pct(det['entry_bar_match_rate'])}** "
        f"({det['entry_bar_match_hits']}/{det['entry_bar_match_n']})",
        "",
        "## Take-profit hits (Bug C) — OUR FX bars",
        "",
        f"| Target | Hit rate | Count |",
        f"|--------|----------|-------|",
        f"| 0.5 × H | {pct(tp['hit_0_5H_rate'])} | {tp['hit_0_5H_count']}/{tp['n_labels_with_outcomes']} |",
        f"| {tp.get('tp2_mult_h', 0.51)} × H (TP2) | {pct(tp.get('hit_kH_rate'))} | {tp.get('hit_kH_count', 0)}/{tp['n_labels_with_outcomes']} |",
        f"| 1.0 × H | {pct(tp['hit_1_0H_rate'])} | {tp['hit_1_0H_count']}/{tp['n_labels_with_outcomes']} |",
        "",
        f"_{tp['note']}_",
        "",
        "## Entry premature rate (Bug B — E5)",
        "",
    ]
    e5 = card.get("premature_entry_metrics", {})
    det_prem = card.get("detector_premature_metrics", {})
    fail = card.get("failure_metrics") or {}
    lines += [
        f"- premature_entry_rate (labeled tests): **{pct(e5.get('premature_entry_rate'))}** "
        f"({e5.get('premature_violations', 0)}/{e5.get('n_premature_test_labels', 0)})",
        f"- detector premature rate (all dets): **{pct(det_prem.get('premature_rate'))}** "
        f"({det_prem.get('premature_count', 0)}/{det_prem.get('n_detections_with_entry', 0)})",
        "",
        "## Failure / bust gates",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Failure labels | {fail.get('n_failure_labels', 0)} |",
        f"| Failure detections | {fail.get('n_failure_detections', 0)} |",
        f"| Failure precision | {pct(fail.get('precision'))} |",
        f"| Failure recall | {pct(fail.get('recall'))} |",
        f"| Premature failure rate | {pct(fail.get('premature_failure_rate'))} |",
        f"| Classic leak count | {fail.get('classic_leak_count', 0)} |",
        "",
        "## Hard-negative false accepts",
        "",
    ]
    if det["false_accept_label_ids"]:
        for lid in det["false_accept_label_ids"]:
            lines.append(f"- `{lid}`")
    else:
        lines.append("- (none)")
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Evaluate H&S detector export vs labels")
    p.add_argument("--bars-dir", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True, help="Label file or directory")
    p.add_argument("--detections", type=Path, required=True, help="Detector CSV/JSON export")
    p.add_argument("--entry-mode", choices=["A", "B"], default="A")
    p.add_argument(
        "--trade-mode",
        choices=["classic", "failure"],
        default="classic",
        help="Scorecard annotation; failure detections should set trade_kind=failure",
    )
    p.add_argument("--outcome-bars", type=int, default=50)
    p.add_argument("--match-tol-bars", type=int, default=5)
    p.add_argument("--tp2-mult-h", type=float, default=0.51, help="TP2 target as k×H (spec default 0.51)")
    p.add_argument("--out", type=Path, required=True, help="Output report directory")
    p.add_argument(
        "--outcomes-on",
        choices=["true_all", "matched_only"],
        default="true_all",
        help="Compute TP outcomes on all true labels (default) or matched only",
    )
    return p


def run(args: argparse.Namespace) -> dict[str, Any]:
    labels = load_labels(args.labels)
    detections = load_detections(args.detections)
    true_labels = [lb for lb in labels if not lb.get("hard_negative")]

    matches, unmatched_true, unmatched_dets, false_accepts = match_detections(
        labels,
        detections,
        match_tol_bars=args.match_tol_bars,
        entry_mode=args.entry_mode,
    )

    det_metrics = compute_detection_metrics(
        n_true_labels=len(true_labels),
        matches=matches,
        unmatched_true=unmatched_true,
        unmatched_detections=unmatched_dets,
        false_accepts=false_accepts,
    )

    bars_cache: dict[Path, list] = {}
    outcome_labels = true_labels
    if args.outcomes_on == "matched_only":
        outcome_labels = [m.label for m in matches]

    per_label_outcomes: list[dict[str, Any]] = []
    for lb in outcome_labels:
        try:
            bars = load_bars_for_label(
                args.bars_dir,
                lb["symbol"],
                lb["timeframe"],
                lb.get("bars_file"),
                bars_cache,
            )
            oc = compute_outcomes(
                lb,
                bars,
                outcome_bars=args.outcome_bars,
                entry_mode=args.entry_mode,
                tp2_mult_h=args.tp2_mult_h,
            )
        except FileNotFoundError as exc:
            oc = {
                "outcome_bars": args.outcome_bars,
                "hit_0_5H": None,
                "hit_1_0H": None,
                "mfe": None,
                "mae": None,
                "error": f"missing_bars:{exc}",
            }
        oc["label_id"] = lb["label_id"]
        per_label_outcomes.append(oc)

    tp_metrics = compute_tp_rates(per_label_outcomes)
    premature_metrics = compute_premature_entry_rate(
        labels, detections, match_tol_bars=args.match_tol_bars
    )
    det_premature = detector_premature_rate(detections)
    failure_metrics = compute_failure_gates(
        labels, detections, match_tol_bars=args.match_tol_bars
    )

    card = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entry_mode": args.entry_mode,
        "trade_mode": getattr(args, "trade_mode", "classic"),
        "match_tol_bars": args.match_tol_bars,
        "outcome_bars": args.outcome_bars,
        "tp2_mult_h": args.tp2_mult_h,
        "outcomes_on": args.outcomes_on,
        "n_labels": len(labels),
        "n_detections": len(detections),
        "detection_metrics": det_metrics,
        "tp_metrics": tp_metrics,
        "premature_entry_metrics": premature_metrics,
        "detector_premature_metrics": det_premature,
        "failure_metrics": failure_metrics,
        "spec_ref": "hs-curriculum/hs-spec.v1.json",
        "l0_ref": "hs-curriculum/L0-diagnosis.md",
        "failure_docs_ref": "docs/HS-FAILURE-TRADE.md",
    }
    return {
        "scorecard": card,
        "missed_label_ids": det_metrics["missed_label_ids"],
        "false_accepts": [
            {
                "label_id": fa["label"]["label_id"],
                "detection_id": fa["detection"]["detection_id"],
                "head_bar_delta": fa["head_bar_delta"],
                "reason": fa["label"].get("hard_negative_reason"),
            }
            for fa in false_accepts
        ],
        "per_label_outcomes": per_label_outcomes,
        "matches": [
            {
                "label_id": m.label["label_id"],
                "detection_id": m.detection["detection_id"],
                "head_bar_delta": m.head_bar_delta,
                "entry_bar_delta": m.entry_bar_delta,
                "entry_matched": m.entry_matched,
            }
            for m in matches
        ],
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(args)
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    (out / "scorecard.json").write_text(json.dumps(result["scorecard"], indent=2) + "\n")
    (out / "scorecard.md").write_text(_md_scorecard(result["scorecard"]))
    (out / "missed_label_ids.json").write_text(
        json.dumps(result["missed_label_ids"], indent=2) + "\n"
    )
    (out / "false_accept_ids.json").write_text(json.dumps(result["false_accepts"], indent=2) + "\n")
    (out / "per_label_outcomes.json").write_text(
        json.dumps(result["per_label_outcomes"], indent=2) + "\n"
    )
    (out / "matches.json").write_text(json.dumps(result["matches"], indent=2) + "\n")

    print(f"Wrote reports to {out}")
    det = result["scorecard"]["detection_metrics"]
    print(
        f"precision={det['precision']} recall={det['recall']} f1={det['f1']} "
        f"entry_match={det['entry_bar_match_rate']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
