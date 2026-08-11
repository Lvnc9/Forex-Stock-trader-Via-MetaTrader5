"""CLI: run H&S detector over bar CSVs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from detector.detect import detect_on_bars, detect_patterns
from detector.export import detections_to_json
from harness.bars import load_bars_csv


def _parse_symbol_tf(stem: str) -> tuple[str, str] | None:
    parts = stem.rsplit("_", 1)
    if len(parts) != 2:
        return None
    sym, tf = parts
    if tf not in ("H1", "H4", "D1"):
        return None
    return sym.upper(), tf.upper()


def run_directory(
    bars_dir: Path,
    *,
    entry_mode: str = "A",
) -> list[dict]:
    all_dets: list[dict] = []
    for csv_path in sorted(bars_dir.glob("*.csv")):
        parsed = _parse_symbol_tf(csv_path.stem)
        if parsed is None:
            continue
        symbol, tf = parsed
        if "_duka" in csv_path.stem.lower():
            continue
        bars = load_bars_csv(csv_path)
        all_dets.extend(detect_on_bars(bars, symbol, tf, entry_mode=entry_mode))
    return all_dets


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="H&S detector — export JSON for harness")
    p.add_argument("--bars", type=Path, help="Single bar CSV file")
    p.add_argument("--bars-dir", type=Path, help="Directory of SYMBOL_TF.csv files")
    p.add_argument("--symbol", default="EURUSD")
    p.add_argument("--timeframe", default="H1", choices=["H1", "H4", "D1"])
    p.add_argument("--entry-mode", choices=["A", "B"], default="A")
    p.add_argument("--out", type=Path, required=True, help="Output detections JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.bars_dir:
        detections = run_directory(args.bars_dir, entry_mode=args.entry_mode)
    elif args.bars:
        bars = load_bars_csv(args.bars)
        detections = detect_on_bars(bars, args.symbol, args.timeframe, entry_mode=args.entry_mode)
    else:
        print("Provide --bars or --bars-dir", file=sys.stderr)
        return 2

    detections_to_json(detections, args.out)
    print(f"Wrote {len(detections)} detections to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
