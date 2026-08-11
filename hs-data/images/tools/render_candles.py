"""Render OHLC bars to a simple candlestick PNG for human labeling."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def load_ohlc(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "time": row.get("time") or row.get("Time") or "",
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                }
            )
    return rows


def render_png(
    bars: list[dict],
    out_path: Path,
    *,
    width: int = 900,
    height: int = 400,
    pad: int = 20,
) -> None:
    """Minimal PNG writer (no matplotlib dependency) — RGB candles on dark slate."""
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "Pillow is required for render_candles. pip install Pillow"
        ) from exc

    if not bars:
        raise ValueError("no bars to render")

    lo = min(b["low"] for b in bars)
    hi = max(b["high"] for b in bars)
    span = max(hi - lo, 1e-9)
    n = len(bars)
    img = Image.new("RGB", (width, height), (24, 28, 34))
    draw = ImageDraw.Draw(img)
    usable_w = width - 2 * pad
    usable_h = height - 2 * pad
    candle_w = max(1, int(usable_w / max(n, 1) * 0.6))

    def y_of(price: float) -> int:
        return int(pad + (hi - price) / span * usable_h)

    for i, b in enumerate(bars):
        x = pad + int((i + 0.5) / n * usable_w)
        y_h, y_l = y_of(b["high"]), y_of(b["low"])
        y_o, y_c = y_of(b["open"]), y_of(b["close"])
        up = b["close"] >= b["open"]
        color = (70, 180, 120) if up else (200, 80, 90)
        draw.line([(x, y_h), (x, y_l)], fill=color, width=1)
        top, bot = min(y_o, y_c), max(y_o, y_c)
        if bot == top:
            bot = top + 1
        draw.rectangle([x - candle_w // 2, top, x + candle_w // 2, bot], fill=color)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Render OHLC window to candlestick PNG")
    p.add_argument("--bars", type=Path, required=True)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--end", type=int, default=None, help="Exclusive end index")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--meta-out", type=Path, default=None)
    p.add_argument("--symbol", default="")
    p.add_argument("--timeframe", default="")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    all_bars = load_ohlc(args.bars)
    end = args.end if args.end is not None else len(all_bars)
    window = all_bars[args.start : end]
    if not window:
        print("Empty window")
        return 2
    render_png(window, args.out)
    stem = args.bars.stem
    sym, tf = args.symbol, args.timeframe
    if not sym or not tf:
        parts = stem.rsplit("_", 1)
        if len(parts) == 2:
            sym, tf = parts[0], parts[1]
    meta = {
        "meta_id": f"{stem}_{args.start}_{end}",
        "source_kind": "rendered_bars",
        "bars_file": str(args.bars.name),
        "symbol": sym,
        "timeframe": tf,
        "start_bar_index": args.start,
        "end_bar_index": end,
        "n_bars": len(window),
        "image_relpath": str(args.out),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "label_hints": {
            "structure_ok": None,
            "neckline_confirm_bar": None,
            "failure_bar": None,
            "failure_level": "head",
            "outcome": None,
        },
        "notes": "Self-rendered from project bars — preferred for gold labeling.",
    }
    meta_path = args.meta_out
    if meta_path is None:
        meta_path = Path("images/metadata") / f"{meta['meta_id']}.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} and {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
