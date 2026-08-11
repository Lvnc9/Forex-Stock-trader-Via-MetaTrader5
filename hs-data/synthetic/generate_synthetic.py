"""Generate geometric H&S bar series for harness unit tests ONLY."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _write_bars(path: Path, closes: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close", "volume"])
        prev = closes[0]
        n = len(closes)
        for i, c in enumerate(closes):
            o = prev
            left = closes[i - 1] if i > 0 else c
            right = closes[i + 1] if i + 1 < n else c
            if c >= left and c >= right:
                h = c + 0.0010
                l = min(o, c) - 0.0002
            elif c <= left and c <= right:
                h = max(o, c) + 0.0002
                l = c - 0.0010
            else:
                h = max(o, c) + 0.0002
                l = min(o, c) - 0.0002
            ts = (t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
            w.writerow([ts, f"{o:.5f}", f"{h:.5f}", f"{l:.5f}", f"{c:.5f}", 100])
            prev = c


def _top_pattern() -> tuple[list[float], dict]:
    """Build a simple H&S top in a flat series; head at index ~40."""
    closes = [1.1000 + 0.0001 * i for i in range(30)]  # mild uptrend
    # LS peak ~1.1050 around 35
    seg = []
    # climb to LS
    for i in range(10):
        seg.append(1.1000 + 0.0005 * i)
    ls_i = 30 + 9
    # down to trough1
    for i in range(8):
        seg.append(1.1045 - 0.0006 * i)
    t1_i = 30 + 10 + 7
    # up to head
    for i in range(12):
        seg.append(1.1000 + 0.0010 * i)
    head_i = t1_i + 12
    # down to trough2
    for i in range(10):
        seg.append(1.1110 - 0.0011 * i)
    t2_i = head_i + 10
    # up to RS (lower than head)
    for i in range(10):
        seg.append(1.1005 + 0.00045 * i)
    rs_i = t2_i + 10
    # break below neckline
    for i in range(15):
        seg.append(1.1045 - 0.0008 * i)
    confirm_i = rs_i + 8
    closes = closes[:30] + seg
    # pad
    while len(closes) < confirm_i + 60:
        closes.append(closes[-1] - 0.0001)

    H = abs(closes[head_i] - ((closes[t1_i] + closes[t2_i]) / 2))
    label = {
        "label_id": "SYNTH_H1_top_geom_001",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "direction": "top",
        "hard_negative": False,
        "hard_negative_reason": None,
        "LS_bar_index": ls_i,
        "LS_price": closes[ls_i],
        "LS_time": None,
        "trough1_bar_index": t1_i,
        "trough1_price": closes[t1_i],
        "trough1_time": None,
        "head_bar_index": head_i,
        "head_price": closes[head_i],
        "head_time": None,
        "trough2_bar_index": t2_i,
        "trough2_price": closes[t2_i],
        "trough2_time": None,
        "RS_bar_index": rs_i,
        "RS_price": closes[rs_i],
        "RS_time": None,
        "neckline_left_bar_index": t1_i,
        "neckline_left_price": closes[t1_i],
        "neckline_right_bar_index": t2_i,
        "neckline_right_price": closes[t2_i],
        "confirmation_bar_index": confirm_i,
        "confirmation_price": closes[confirm_i],
        "confirm_rule": "close_beyond_neckline",
        "retest_bar_index": None,
        "H": H,
        "label_quality": "gold",
        "entry_mode": "A",
        "entry_bar_index": confirm_i,
        "entry_price": closes[confirm_i],
        "sl_price": None,
        "tp1_price": None,
        "tp2_price": None,
        "outcomes": {
            "outcome_bars": 50,
            "hit_0_5H": None,
            "hit_1_0H": None,
            "mfe": None,
            "mae": None,
        },
        "false_positive": False,
        "notes": "SYNTHETIC geometric top — unit test only",
        "bars_file": "EURUSD_H1.csv",
    }
    return closes, label


def _inverse_on_same(closes: list[float], offset: int = 200) -> dict:
    """Place an inverse pattern later in the series by mirroring a slice."""
    # Use a dedicated region starting at offset
    base = 1.0800
    region = []
    for i in range(10):
        region.append(base - 0.0004 * i)  # prior downtrend into LS low
    ls_local = len(region) - 1
    for i in range(8):
        region.append(region[-1] + 0.00055)  # trough1 high (armpit)
    t1_local = len(region) - 1
    for i in range(12):
        region.append(region[-1] - 0.0009)  # head low
    head_local = len(region) - 1
    for i in range(10):
        region.append(region[-1] + 0.00085)
    t2_local = len(region) - 1
    for i in range(10):
        region.append(region[-1] - 0.0005)  # RS
    rs_local = len(region) - 1
    for i in range(15):
        region.append(region[-1] + 0.0007)  # break up
    confirm_local = rs_local + 8

    # extend closes
    while len(closes) < offset:
        closes.append(closes[-1])
    for c in region:
        closes.append(c)
    while len(closes) < offset + confirm_local + 60:
        closes.append(closes[-1] + 0.00005)

    ls_i = offset + ls_local
    t1_i = offset + t1_local
    head_i = offset + head_local
    t2_i = offset + t2_local
    rs_i = offset + rs_local
    confirm_i = offset + confirm_local
    H = abs(closes[head_i] - ((closes[t1_i] + closes[t2_i]) / 2))
    return {
        "label_id": "SYNTH_H1_inverse_geom_001",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "direction": "inverse",
        "hard_negative": False,
        "hard_negative_reason": None,
        "LS_bar_index": ls_i,
        "LS_price": closes[ls_i],
        "LS_time": None,
        "trough1_bar_index": t1_i,
        "trough1_price": closes[t1_i],
        "trough1_time": None,
        "head_bar_index": head_i,
        "head_price": closes[head_i],
        "head_time": None,
        "trough2_bar_index": t2_i,
        "trough2_price": closes[t2_i],
        "trough2_time": None,
        "RS_bar_index": rs_i,
        "RS_price": closes[rs_i],
        "RS_time": None,
        "neckline_left_bar_index": t1_i,
        "neckline_left_price": closes[t1_i],
        "neckline_right_bar_index": t2_i,
        "neckline_right_price": closes[t2_i],
        "confirmation_bar_index": confirm_i,
        "confirmation_price": closes[confirm_i],
        "confirm_rule": "close_beyond_neckline",
        "retest_bar_index": None,
        "H": H,
        "label_quality": "gold",
        "entry_mode": "A",
        "entry_bar_index": confirm_i,
        "entry_price": closes[confirm_i],
        "sl_price": None,
        "tp1_price": None,
        "tp2_price": None,
        "outcomes": {
            "outcome_bars": 50,
            "hit_0_5H": None,
            "hit_1_0H": None,
            "mfe": None,
            "mae": None,
        },
        "false_positive": False,
        "notes": "SYNTHETIC geometric inverse — unit test only",
        "bars_file": "EURUSD_H1.csv",
    }


def _hard_neg_double_top(closes: list[float], offset: int = 400) -> dict:
    while len(closes) < offset:
        closes.append(closes[-1])
    region = []
    for i in range(15):
        region.append(1.0900 + 0.0003 * i)
    p1 = len(region) - 1
    for i in range(10):
        region.append(region[-1] - 0.0004)
    mid = len(region) - 1
    for i in range(15):
        region.append(region[-1] + 0.00028)  # second peak ~same height
    p2 = len(region) - 1
    for i in range(20):
        region.append(region[-1] - 0.0002)
    for c in region:
        closes.append(c)
    ls_i = offset + p1
    head_i = offset + p2  # "fake head" same height
    t1_i = offset + mid
    t2_i = offset + p2 + 5
    rs_i = head_i  # degenerate
    confirm_i = offset + len(region) - 5
    return {
        "label_id": "SYNTH_H1_neg_double_top_001",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "direction": "top",
        "hard_negative": True,
        "hard_negative_reason": "double_top",
        "LS_bar_index": ls_i,
        "LS_price": closes[ls_i],
        "LS_time": None,
        "trough1_bar_index": t1_i,
        "trough1_price": closes[t1_i],
        "trough1_time": None,
        "head_bar_index": head_i,
        "head_price": closes[head_i],
        "head_time": None,
        "trough2_bar_index": min(t2_i, len(closes) - 1),
        "trough2_price": closes[min(t2_i, len(closes) - 1)],
        "trough2_time": None,
        "RS_bar_index": rs_i,
        "RS_price": closes[rs_i],
        "RS_time": None,
        "neckline_left_bar_index": t1_i,
        "neckline_left_price": closes[t1_i],
        "neckline_right_bar_index": min(t2_i, len(closes) - 1),
        "neckline_right_price": closes[min(t2_i, len(closes) - 1)],
        "confirmation_bar_index": confirm_i,
        "confirmation_price": closes[confirm_i],
        "confirm_rule": "close_beyond_neckline",
        "retest_bar_index": None,
        "H": 0.001,
        "label_quality": "reject",
        "entry_mode": None,
        "entry_bar_index": None,
        "entry_price": None,
        "sl_price": None,
        "tp1_price": None,
        "tp2_price": None,
        "outcomes": {
            "outcome_bars": 50,
            "hit_0_5H": None,
            "hit_1_0H": None,
            "mfe": None,
            "mae": None,
        },
        "false_positive": True,
        "notes": "SYNTHETIC hard negative double top — unit test only",
        "bars_file": "EURUSD_H1.csv",
    }


def _top_down_neckline(closes: list[float], offset: int = 600) -> dict:
    """Top with down-sloping neckline → confirm on right armpit (PB04 matrix)."""
    while len(closes) < offset:
        closes.append(closes[-1])
    region = []
    for i in range(55):
        region.append(1.1000 + 0.00007 * i)
    ls_local = len(region) - 1
    for i in range(8):
        region.append(region[-1] - 0.0005)
    t1_local = len(region) - 1
    t1_p = region[-1]
    for i in range(12):
        region.append(region[-1] + 0.0010)
    head_local = len(region) - 1
    head_p = region[-1]
    for i in range(10):
        region.append(region[-1] - 0.0010)
    t2_local = len(region) - 1
    t2_p = region[-1] - 0.0005  # down-sloping neckline
    region[-1] = t2_p
    for i in range(10):
        region.append(region[-1] + 0.0004)
    rs_local = len(region) - 1
    for i in range(12):
        region.append(region[-1] - 0.0008)
    confirm_local = rs_local + 6

    while len(closes) < offset + len(region):
        closes.append(closes[-1])
    for i, v in enumerate(region):
        closes[offset + i] = v

    ls_i = offset + ls_local
    t1_i = offset + t1_local
    head_i = offset + head_local
    t2_i = offset + t2_local
    rs_i = offset + rs_local
    confirm_i = offset + confirm_local
    nl_head = t1_p + (t2_p - t1_p) * (head_local - t1_local) / max(t2_local - t1_local, 1)
    H = abs(head_p - nl_head)

    return {
        "label_id": "SYNTH_H1_top_down_neck_001",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "direction": "top",
        "hard_negative": False,
        "hard_negative_reason": None,
        "LS_bar_index": ls_i,
        "LS_price": closes[ls_i],
        "trough1_bar_index": t1_i,
        "trough1_price": closes[t1_i],
        "head_bar_index": head_i,
        "head_price": closes[head_i],
        "trough2_bar_index": t2_i,
        "trough2_price": closes[t2_i],
        "RS_bar_index": rs_i,
        "RS_price": closes[rs_i],
        "neckline_left_bar_index": t1_i,
        "neckline_left_price": closes[t1_i],
        "neckline_right_bar_index": t2_i,
        "neckline_right_price": closes[t2_i],
        "confirmation_bar_index": confirm_i,
        "confirmation_price": closes[confirm_i],
        "confirm_rule": "close_beyond_right_armpit",
        "retest_bar_index": None,
        "H": H,
        "label_quality": "gold",
        "entry_mode": "A",
        "entry_bar_index": confirm_i,
        "entry_price": closes[confirm_i],
        "sl_price": None,
        "tp1_price": None,
        "tp2_price": None,
        "outcomes": {"outcome_bars": 50, "hit_0_5H": None, "hit_1_0H": None, "mfe": None, "mae": None},
        "false_positive": False,
        "notes": "SYNTHETIC top down neckline — PB04 matrix",
        "bars_file": "EURUSD_H1.csv",
    }


def _hard_neg_no_prior_trend(closes: list[float], offset: int = 800) -> dict:
    while len(closes) < offset:
        closes.append(closes[-1])
    region = [1.1050 + 0.00005 * (i % 3 - 1) for i in range(120)]
    for c in region:
        closes.append(c)
    head_i = offset + 60
    return {
        "label_id": "SYNTH_H1_neg_no_prior_001",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "direction": "top",
        "hard_negative": True,
        "hard_negative_reason": "missing_prior_trend",
        "LS_bar_index": offset + 20,
        "LS_price": closes[offset + 20],
        "trough1_bar_index": offset + 35,
        "trough1_price": closes[offset + 35],
        "head_bar_index": head_i,
        "head_price": closes[head_i],
        "trough2_bar_index": offset + 75,
        "trough2_price": closes[offset + 75],
        "RS_bar_index": offset + 90,
        "RS_price": closes[offset + 90],
        "neckline_left_bar_index": offset + 35,
        "neckline_left_price": closes[offset + 35],
        "neckline_right_bar_index": offset + 75,
        "neckline_right_price": closes[offset + 75],
        "confirmation_bar_index": offset + 100,
        "confirmation_price": closes[offset + 100],
        "confirm_rule": "close_beyond_neckline",
        "retest_bar_index": None,
        "H": 0.001,
        "label_quality": "reject",
        "entry_mode": None,
        "entry_bar_index": None,
        "entry_price": None,
        "sl_price": None,
        "tp1_price": None,
        "tp2_price": None,
        "outcomes": {"outcome_bars": 50, "hit_0_5H": None, "hit_1_0H": None, "mfe": None, "mae": None},
        "false_positive": True,
        "notes": "SYNTHETIC hard negative no prior trend — PB04",
        "bars_file": "EURUSD_H1.csv",
    }


def _detection_from_label(label: dict, det_id: str) -> dict:
    return {
        "detection_id": det_id,
        "symbol": label["symbol"],
        "timeframe": label["timeframe"],
        "direction": label["direction"],
        "LS_bar_index": label["LS_bar_index"],
        "LS_price": label["LS_price"],
        "trough1_bar_index": label["trough1_bar_index"],
        "trough1_price": label["trough1_price"],
        "head_bar_index": label["head_bar_index"],
        "head_price": label["head_price"],
        "trough2_bar_index": label["trough2_bar_index"],
        "trough2_price": label["trough2_price"],
        "RS_bar_index": label["RS_bar_index"],
        "RS_price": label["RS_price"],
        "neckline_left_bar_index": label["neckline_left_bar_index"],
        "neckline_left_price": label["neckline_left_price"],
        "neckline_right_bar_index": label["neckline_right_bar_index"],
        "neckline_right_price": label["neckline_right_price"],
        "confirmation_bar_index": label["confirmation_bar_index"],
        "confirmation_price": label["confirmation_price"],
        "confirm_rule": label["confirm_rule"],
        "entry_mode": label.get("entry_mode") or "A",
        "entry_bar_index": label.get("entry_bar_index") or label["confirmation_bar_index"],
        "entry_price": label.get("entry_price") or label["confirmation_price"],
        "H": label["H"],
        "score": 80.0,
        "scale": "medium",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Synthetic H&S fixtures (unit tests only)")
    p.add_argument("--out", type=Path, default=Path("synthetic/out"))
    p.add_argument("--seed", type=int, default=42, help="Reserved for future noise")
    args = p.parse_args(argv)

    closes, top = _top_pattern()
    inv = _inverse_on_same(closes, offset=200)
    neg = _hard_neg_double_top(closes, offset=400)
    top_down = _top_down_neckline(closes, offset=600)
    neg_prior = _hard_neg_no_prior_trend(closes, offset=800)

    bars_path = args.out / "bars" / "EURUSD_H1.csv"
    _write_bars(bars_path, closes)

    labels_dir = args.out / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)
    all_labels = (top, inv, neg, top_down, neg_prior)
    for lab in all_labels:
        (labels_dir / f"{lab['label_id']}.json").write_text(json.dumps(lab, indent=2) + "\n")

    true_labels = [top, inv, top_down]
    perfect = [_detection_from_label(lab, f"det_{lab['label_id']}") for lab in true_labels]
    miss = [_detection_from_label(inv, "det_inv_only")]

    (args.out / "detections_perfect.json").write_text(json.dumps(perfect, indent=2) + "\n")
    (args.out / "detections_miss_one.json").write_text(json.dumps(miss, indent=2) + "\n")

    meta = {
        "synthetic": True,
        "warning": "Unit-test seeds only. Do not use as live FX truth.",
        "seed": args.seed,
        "n_bars": len(closes),
        "matrix": {
            "true_top_flat": top["label_id"],
            "true_inverse_flat": inv["label_id"],
            "true_top_down_neck": top_down["label_id"],
            "hard_neg_double_top": neg["label_id"],
            "hard_neg_no_prior": neg_prior["label_id"],
        },
    }
    (args.out / "META.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Wrote synthetic pack to {args.out} ({len(closes)} bars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
