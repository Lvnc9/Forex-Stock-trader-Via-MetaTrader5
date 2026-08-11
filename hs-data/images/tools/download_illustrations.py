"""Download illustrative article pages/images listed in sources.json (optional)."""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse


USER_AGENT = "TradeBotHSResearch/1.0 (+local research; respect robots)"


def _fetch(url: str, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _extract_img_urls(html: str, base: str) -> list[str]:
    found: list[str] = []
    for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', html, flags=re.I):
        src = match.group(1)
        if src.startswith("data:"):
            continue
        found.append(urljoin(base, src))
    return found


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Download illustrative H&S failure page images")
    p.add_argument("--sources", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--max-images-per-source", type=int, default=3)
    p.add_argument("--meta-dir", type=Path, default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)
    meta_dir = args.meta_dir or (args.out.parent / "metadata")
    meta_dir.mkdir(parents=True, exist_ok=True)

    for src in sources:
        sid = src["id"]
        url = src["url"]
        print(f"Fetching page {sid}: {url}")
        try:
            raw = _fetch(url)
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"  skip page: {exc}")
            continue
        html = raw.decode("utf-8", errors="replace")
        imgs = _extract_img_urls(html, url)[: args.max_images_per_source]
        for i, img_url in enumerate(imgs):
            ext = Path(urlparse(img_url).path).suffix.lower() or ".img"
            if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".img"):
                ext = ".img"
            out_file = args.out / f"{sid}_{i}{ext}"
            try:
                data = _fetch(img_url)
                out_file.write_bytes(data)
            except (urllib.error.URLError, TimeoutError) as exc:
                print(f"  skip image {img_url}: {exc}")
                continue
            meta = {
                "meta_id": f"{sid}_{i}",
                "source_kind": "downloaded_illustration",
                "source_id": sid,
                "page_url": url,
                "image_url": img_url,
                "image_relpath": str(out_file),
                "license_note": src.get("license_note"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "label_hints": {
                    "structure_ok": None,
                    "neckline_confirm_bar": None,
                    "failure_bar": None,
                    "failure_level": "head",
                    "outcome": None,
                },
                "notes": src.get("note"),
            }
            (meta_dir / f"{sid}_{i}.json").write_text(
                json.dumps(meta, indent=2) + "\n", encoding="utf-8"
            )
            print(f"  saved {out_file.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
