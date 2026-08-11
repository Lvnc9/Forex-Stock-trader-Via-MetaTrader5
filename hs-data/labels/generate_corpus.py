"""Generate filled label corpus by embedding geometric H&S patterns in bar series."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _write_bars(path: Path, closes: list[float], base_price: float = 1.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2019, 1, 1, tzinfo=timezone.utc)
    n = len(closes)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close", "volume"])
        prev = closes[0]
        for i, c in enumerate(closes):
            o = prev
            left = closes[i - 1] if i > 0 else c
            right = closes[i + 1] if i + 1 < n else c
            spread = max(abs(c) * 0.0001, 0.0002)
            if c >= left and c >= right:
                h = c + max(spread * 5, 0.0010)
                l = min(o, c) - spread
            elif c <= left and c <= right:
                h = max(o, c) + spread
                l = c - max(spread * 5, 0.0010)
            else:
                h = max(o, c) + spread
                l = min(o, c) - spread
            ts = (t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
            w.writerow([ts, f"{o:.5f}", f"{h:.5f}", f"{l:.5f}", f"{c:.5f}", 100 + i % 50])
            prev = c


def _embed_top(
    closes: list[float],
    offset: int,
    *,
    neck_slope: str = "flat",
    asym: float = 0.0,
) -> dict[str, Any]:
    """Embed H&S top starting at offset; return label dict."""
    region: list[float] = []
    # prior uptrend
    for i in range(55):
        region.append(1.1000 + 0.00008 * i + random.uniform(-0.00005, 0.00005))
    ls_local = len(region) - 1
    for i in range(8):
        region.append(region[-1] - 0.00055)
    t1_local = len(region) - 1
    t1_p = region[-1]
    for i in range(12):
        region.append(region[-1] + 0.00095)
    head_local = len(region) - 1
    head_p = region[-1]
    for i in range(10):
        region.append(region[-1] - 0.0010)
    t2_local = len(region) - 1
    t2_base = region[-1]
    if neck_slope == "up":
        t2_p = t2_base + 0.0004
    elif neck_slope == "down":
        t2_p = t2_base - 0.0004
    else:
        t2_p = t2_base
    region[-1] = t2_p
    rs_adj = 1.0 - asym * 0.3
    for i in range(10):
        region.append(region[-1] + 0.00042 * rs_adj)
    rs_local = len(region) - 1
    confirm_rule = "close_beyond_neckline" if neck_slope in ("up", "flat") else "close_beyond_right_armpit"
    for i in range(12):
        region.append(region[-1] - 0.00075)
    confirm_local = rs_local + 8

    while len(closes) < offset + len(region):
        closes.append(closes[-1] if closes else 1.1)
    scale = closes[offset - 1] if offset > 0 else 1.1
    for i, v in enumerate(region):
        closes[offset + i] = scale + (v - 1.1000)

    ls_i = offset + ls_local
    t1_i = offset + t1_local
    head_i = offset + head_local
    t2_i = offset + t2_local
    rs_i = offset + rs_local
    confirm_i = offset + confirm_local
    nl_head = t1_p + (t2_p - t1_p) * (head_local - t1_local) / max(t2_local - t1_local, 1)
    H = abs(head_p - nl_head)

    return {
        "label_id": f"CORPUS_{offset:05d}_top_{neck_slope}",
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
        "confirm_rule": confirm_rule,
        "retest_bar_index": None,
        "H": H,
        "label_quality": "gold" if asym < 0.15 else "silver",
        "entry_mode": "A",
        "entry_bar_index": confirm_i,
        "entry_price": closes[confirm_i],
        "sl_price": None,
        "tp1_price": None,
        "tp2_price": None,
        "outcomes": {"outcome_bars": 50, "hit_0_5H": None, "hit_1_0H": None, "mfe": None, "mae": None},
        "false_positive": False,
        "notes": f"Corpus embed top neck={neck_slope} asym={asym:.2f}",
        "bars_file": "EURUSD_H1_corpus.csv",
    }


def _embed_inverse(closes: list[float], offset: int, *, neck_slope: str = "flat") -> dict[str, Any]:
    region: list[float] = []
    for i in range(55):
        region.append(1.0800 - 0.00007 * i + random.uniform(-0.00004, 0.00004))
    ls_local = len(region) - 1
    for i in range(8):
        region.append(region[-1] + 0.0005)
    t1_local = len(region) - 1
    t1_p = region[-1]
    for i in range(12):
        region.append(region[-1] - 0.00088)
    head_local = len(region) - 1
    head_p = region[-1]
    for i in range(10):
        region.append(region[-1] + 0.0009)
    t2_local = len(region) - 1
    if neck_slope == "down":
        t2_p = region[-1] - 0.00035
    elif neck_slope == "up":
        t2_p = region[-1] + 0.00035
    else:
        t2_p = region[-1]
    region[-1] = t2_p
    for i in range(10):
        region.append(region[-1] - 0.00045)
    rs_local = len(region) - 1
    confirm_rule = "close_beyond_neckline" if neck_slope in ("down", "flat") else "close_beyond_right_armpit"
    for i in range(12):
        region.append(region[-1] + 0.0007)
    confirm_local = rs_local + 8

    while len(closes) < offset + len(region):
        closes.append(closes[-1] if closes else 1.08)
    scale = closes[offset - 1] if offset > 0 else 1.08
    for i, v in enumerate(region):
        closes[offset + i] = scale + (v - 1.0800)

    ls_i = offset + ls_local
    t1_i = offset + t1_local
    head_i = offset + head_local
    t2_i = offset + t2_local
    rs_i = offset + rs_local
    confirm_i = offset + confirm_local
    nl_head = t1_p + (region[t2_local] - t1_p) * (head_local - t1_local) / max(t2_local - t1_local, 1)
    H = abs(head_p - nl_head)

    return {
        "label_id": f"CORPUS_{offset:05d}_inverse_{neck_slope}",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "direction": "inverse",
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
        "confirm_rule": confirm_rule,
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
        "notes": f"Corpus embed inverse neck={neck_slope}",
        "bars_file": "EURUSD_H1_corpus.csv",
    }


def _embed_hard_negative(
    closes: list[float],
    offset: int,
    reason: str,
) -> dict[str, Any]:
    region: list[float] = []
    if reason == "double_top":
        for i in range(20):
            region.append(1.09 + 0.0003 * i)
        p1 = len(region) - 1
        for i in range(8):
            region.append(region[-1] - 0.0004)
        mid = len(region) - 1
        for i in range(18):
            region.append(region[-1] + 0.00028)
        head_local = len(region) - 1
        direction = "top"
    elif reason == "missing_prior_trend":
        for i in range(55):
            region.append(1.10 + random.uniform(-0.0001, 0.0001))
        ls_local = len(region) - 1
        for i in range(30):
            region.append(region[-1] + (0.0003 if i % 2 == 0 else -0.00025))
        head_local = len(region) - 1
        p1 = ls_local
        mid = ls_local + 5
        direction = "top"
    else:
        for i in range(40):
            region.append(1.10 + 0.0002 * math.sin(i / 3))
        head_local = len(region) - 1
        p1 = head_local // 2
        mid = head_local // 2 + 3
        direction = "top"

    while len(closes) < offset + len(region) + 10:
        closes.append(closes[-1] if closes else 1.1)
    scale = closes[offset - 1] if offset > 0 else 1.1
    for i, v in enumerate(region):
        closes[offset + i] = scale + (v - 1.10)

    head_i = offset + head_local
    ls_i = offset + p1
    t1_i = offset + mid
    t2_i = min(offset + head_local + 5, len(closes) - 10)
    rs_i = head_i
    confirm_i = min(t2_i + 5, len(closes) - 1)

    return {
        "label_id": f"CORPUS_{offset:05d}_neg_{reason}",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "direction": direction,
        "hard_negative": True,
        "hard_negative_reason": reason,
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
        "notes": f"Hard negative corpus: {reason}",
        "bars_file": "EURUSD_H1_corpus.csv",
    }


def _premature_entry_label(closes: list[float], offset: int) -> dict[str, Any]:
    lab = _embed_top(closes, offset, neck_slope="flat", asym=0.05)
    lab["label_id"] = f"CORPUS_{offset:05d}_premature_entry_test"
    lab["notes"] = "premature_entry_test: true — detector must not enter before confirmation"
    return lab


def generate_corpus(
    *,
    n_true: int = 52,
    n_hard_neg: int = 32,
    seed: int = 42,
) -> tuple[list[float], list[dict[str, Any]]]:
    random.seed(seed)
    closes = [1.0950 + 0.00001 * i for i in range(200)]
    labels: list[dict[str, Any]] = []
    offset = 250
    step = 200

    neck_slopes = ["flat", "up", "down"]
    idx = 0
    while len([lb for lb in labels if not lb["hard_negative"]]) < n_true:
        neck = neck_slopes[idx % 3]
        asym = (idx % 5) * 0.05
        if idx % 3 == 0:
            labels.append(_embed_top(closes, offset, neck_slope=neck, asym=asym))
        elif idx % 3 == 1:
            labels.append(_embed_inverse(closes, offset, neck_slope=neck))
        else:
            labels.append(_premature_entry_label(closes, offset))
        offset += step + (idx % 7) * 5
        idx += 1
        while len(closes) < offset + 150:
            closes.append(closes[-1] + random.uniform(-0.0001, 0.0001))

    neg_reasons = [
        "double_top",
        "double_bottom",
        "false_break",
        "missing_prior_trend",
        "no_head_prominence",
        "broken_sequence",
        "excessive_neckline_slope",
        "range_three_peak",
        "broadening",
        "other",
    ]
    ni = 0
    while len([lb for lb in labels if lb["hard_negative"]]) < n_hard_neg:
        reason = neg_reasons[ni % len(neg_reasons)]
        labels.append(_embed_hard_negative(closes, offset, reason))
        offset += step
        ni += 1
        while len(closes) < offset + 80:
            closes.append(closes[-1] + random.uniform(-0.00008, 0.00008))

    return closes, labels


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate filled label corpus + corpus bars")
    p.add_argument("--bars-dir", type=Path, default=Path("bars"))
    p.add_argument("--labels-dir", type=Path, default=Path("labels/filled"))
    p.add_argument("--n-true", type=int, default=52)
    p.add_argument("--n-hard-neg", type=int, default=32)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    closes, labels = generate_corpus(n_true=args.n_true, n_hard_neg=args.n_hard_neg, seed=args.seed)
    _write_bars(args.bars_dir / "EURUSD_H1_corpus.csv", closes)
    args.labels_dir.mkdir(parents=True, exist_ok=True)
    for lb in labels:
        (args.labels_dir / f"{lb['label_id']}.json").write_text(json.dumps(lb, indent=2) + "\n")

    n_true = sum(1 for lb in labels if not lb["hard_negative"])
    n_neg = sum(1 for lb in labels if lb["hard_negative"])
    print(f"Wrote {len(closes)} bars and {len(labels)} labels ({n_true} true, {n_neg} hard neg)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
