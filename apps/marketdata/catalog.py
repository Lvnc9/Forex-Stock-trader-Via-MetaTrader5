from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

INSTRUMENT_SKIP_DIRS = {"_work", "_tmp", "node_modules", "months"}


@dataclass(frozen=True)
class CatalogFile:
    path: Path
    kind: str  # "monthly" | "yearly"


@dataclass(frozen=True)
class InstrumentCatalog:
    slug: str
    csv_files: tuple[CatalogFile, ...]
    bar_count: int
    start: datetime | None
    end: datetime | None
    dukascopy_id: str | None

    @property
    def file_count(self) -> int:
        return len(self.csv_files)


def _count_bars(csv_path: Path) -> int:
    with csv_path.open("rb") as fh:
        lines = sum(1 for _ in fh)
    return max(lines - 1, 0)


def _timestamp_bounds(csv_path: Path) -> tuple[datetime | None, datetime | None]:
    """Read first and last data rows' timestamps without loading the full file."""
    first_ts: datetime | None = None
    last_ts: datetime | None = None
    with csv_path.open("r", encoding="utf-8", errors="replace") as fh:
        header = fh.readline()
        if not header.lower().startswith("timestamp"):
            return None, None
        first_line = fh.readline().strip()
        if first_line:
            first_ts = _parse_ts_ms(first_line.split(",")[0])
        last_line = None
        for line in fh:
            stripped = line.strip()
            if stripped:
                last_line = stripped
        if last_line:
            last_ts = _parse_ts_ms(last_line.split(",")[0])
    return first_ts, last_ts


def _parse_ts_ms(raw: str) -> datetime | None:
    try:
        ms = int(float(raw))
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _guess_dukascopy_id(files: list[CatalogFile]) -> str | None:
    for item in files:
        name = item.path.name
        if "-m1-" in name:
            return name.split("-m1-")[0]
    if files:
        return files[0].path.stem
    return None


def _collect_csv_files(slug_dir: Path) -> list[CatalogFile]:
    found: list[CatalogFile] = []
    months_dir = slug_dir / "months"
    if months_dir.is_dir():
        for path in sorted(months_dir.glob("*.csv")):
            found.append(CatalogFile(path=path, kind="monthly"))
    for path in sorted(slug_dir.glob("*.csv")):
        found.append(CatalogFile(path=path, kind="yearly"))
    return found


def scan_data_root(data_root: Path) -> list[InstrumentCatalog]:
    if not data_root.is_dir():
        return []

    catalogs: list[InstrumentCatalog] = []
    for entry in sorted(data_root.iterdir()):
        if not entry.is_dir() or entry.name in INSTRUMENT_SKIP_DIRS:
            continue
        files = _collect_csv_files(entry)
        if not files:
            continue

        bar_count = 0
        start: datetime | None = None
        end: datetime | None = None
        for item in files:
            bar_count += _count_bars(item.path)
            s, e = _timestamp_bounds(item.path)
            if s and (start is None or s < start):
                start = s
            if e and (end is None or e > end):
                end = e

        catalogs.append(
            InstrumentCatalog(
                slug=entry.name,
                csv_files=tuple(files),
                bar_count=bar_count,
                start=start,
                end=end,
                dukascopy_id=_guess_dukascopy_id(files),
            )
        )

    return catalogs
