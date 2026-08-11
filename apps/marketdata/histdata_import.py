"""Import HistData.com semicolon M1 CSVs into TradeBot catalog monthly shards."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

OHLC_OUT = ["timestamp", "open", "high", "low", "close"]

HISTDATA_DIR_RE = re.compile(r"^HISTDATA_.*", re.IGNORECASE)
HISTDATA_FILE_RE = re.compile(r"^DAT_ASCII_(?P<symbol>[A-Z0-9]+)_M1_(?P<year>\d{4})\.csv$", re.IGNORECASE)


@dataclass(frozen=True)
class HistDataImportResult:
    slug: str
    source_files: tuple[Path, ...]
    month_files: tuple[Path, ...]
    bar_count: int
    start: datetime | None
    end: datetime | None


def is_histdata_staging_dir(name: str) -> bool:
    return bool(HISTDATA_DIR_RE.match(name))


def discover_histdata_csvs(data_root: Path, symbol: str) -> list[Path]:
    """Find ``DAT_ASCII_{SYMBOL}_M1_YYYY.csv`` under ``data/HISTDATA_*`` folders."""
    sym = symbol.upper()
    paths: list[Path] = []
    for entry in sorted(data_root.iterdir()):
        if not entry.is_dir() or not is_histdata_staging_dir(entry.name):
            continue
        if sym not in entry.name.upper():
            continue
        for csv_path in sorted(entry.glob("DAT_ASCII_*.csv")):
            match = HISTDATA_FILE_RE.match(csv_path.name)
            if match and match.group("symbol").upper() == sym:
                paths.append(csv_path)
    return paths


def read_histdata_m1(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        sep=";",
        header=None,
        names=["dt", "open", "high", "low", "close", "volume"],
        dtype={"dt": str},
    )
    frame["timestamp"] = pd.to_datetime(frame["dt"], format="%Y%m%d %H%M%S", utc=True)
    for col in ("open", "high", "low", "close"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.dropna(subset=["timestamp", "open", "high", "low", "close"])
    frame = frame.sort_values("timestamp")
    return frame.set_index("timestamp")


def _month_shard_path(out_dir: Path, slug: str, ts: pd.Timestamp) -> Path:
    return out_dir / f"{slug.lower()}-m1-{ts.year:04d}-{ts.month:02d}.csv"


def write_monthly_shards(
    frames: list[pd.DataFrame],
    *,
    slug: str,
    out_dir: Path,
    overwrite: bool = False,
) -> tuple[list[Path], int]:
    if not frames:
        return [], 0

    combined = pd.concat(frames).sort_index()
    combined = combined[~combined.index.duplicated(keep="last")]

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    total = 0

    for period, chunk in combined.groupby(pd.Grouper(freq="MS")):
        if chunk.empty:
            continue
        out_path = _month_shard_path(out_dir, slug, period)
        if out_path.exists() and not overwrite:
            existing = pd.read_csv(out_path, usecols=["timestamp"])
            if len(existing) >= len(chunk):
                written.append(out_path)
                total += len(existing)
                continue
        export = chunk.reset_index()
        export["timestamp"] = (export["timestamp"].astype("int64") // 10**6).astype(int)
        export = export[OHLC_OUT]
        export.to_csv(out_path, index=False)
        written.append(out_path)
        total += len(export)

    return written, total


def import_histdata_to_slug(
    data_root: Path,
    *,
    slug: str,
    symbol: str,
    source_paths: list[Path] | None = None,
    overwrite: bool = False,
) -> HistDataImportResult:
    slug = slug.strip().lower()
    sources = source_paths or discover_histdata_csvs(data_root, symbol)
    if not sources:
        raise FileNotFoundError(
            f"No HistData CSVs for {symbol.upper()} under {data_root}/HISTDATA_*"
        )

    frames = [read_histdata_m1(path) for path in sources]
    combined = pd.concat(frames).sort_index()
    combined = combined[~combined.index.duplicated(keep="last")]
    idx = combined.index

    out_dir = data_root / slug / "months"
    month_files, bar_count = write_monthly_shards([combined], slug=slug, out_dir=out_dir, overwrite=overwrite)
    bar_count = len(combined)
    meta = {
        "source": "histdata.com",
        "symbol": symbol.upper(),
        "slug": slug,
        "imported_from": [str(p.relative_to(data_root)) for p in sources],
        "month_shards": len(month_files),
        "bar_count": bar_count,
        "from": idx[0].isoformat() if len(idx) else None,
        "to": idx[-1].isoformat() if len(idx) else None,
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }
    (data_root / slug / "import_meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    return HistDataImportResult(
        slug=slug,
        source_files=tuple(sources),
        month_files=tuple(month_files),
        bar_count=bar_count,
        start=idx[0].to_pydatetime() if len(idx) else None,
        end=idx[-1].to_pydatetime() if len(idx) else None,
    )
