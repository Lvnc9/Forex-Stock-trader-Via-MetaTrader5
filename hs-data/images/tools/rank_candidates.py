"""CV-lite ranking of rendered candlestick windows for human review."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _score_image(path: Path) -> float:
    """
    Heuristic: prefer images with clear vertical structure (high contrast peaks).
    Uses Pillow only — not a live detector.
    """
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("Pillow required: pip install Pillow") from exc

    img = Image.open(path).convert("L").resize((160, 80))
    pixels = list(img.getdata())
    w, h = img.size
    # Column-wise max brightness as a crude "high" envelope; score peakiness.
    cols = []
    for x in range(w):
        col = [pixels[y * w + x] for y in range(h)]
        cols.append(max(col))
    if len(cols) < 10:
        return 0.0
    # Three-peak score: left, mid, right thirds
    n = len(cols)
    thirds = [cols[: n // 3], cols[n // 3 : 2 * n // 3], cols[2 * n // 3 :]]
    peaks = [max(t) if t else 0 for t in thirds]
    mid_boost = peaks[1] - 0.5 * (peaks[0] + peaks[2])
    contrast = (max(cols) - min(cols)) / 255.0
    return float(max(0.0, mid_boost / 255.0) + contrast)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Rank rendered chart images for H&S review")
    p.add_argument("--rendered-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = sorted(
        list(args.rendered_dir.glob("*.png")) + list(args.rendered_dir.glob("*.jpg"))
    )
    ranked = []
    for path in paths:
        ranked.append(
            {
                "path": str(path),
                "score": round(_score_image(path), 4),
            }
        )
    ranked.sort(key=lambda r: r["score"], reverse=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n": len(ranked),
        "note": "Heuristic only — humans label; do not auto-trade on this score.",
        "ranked": ranked,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Ranked {len(ranked)} images → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
