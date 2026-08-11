"""Load M1 OHLC CSVs, resample to strategy timeframes, optional disk cache."""

from __future__ import annotations

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd

from apps.marketdata.catalog import CatalogFile, _collect_csv_files, file_covers_range
from apps.marketdata.timeframes import (
    normalize_timeframe,
    pandas_resample_rule,
    is_higher_timeframe,
)

logger = logging.getLogger(__name__)

OHLC_COLUMNS = ["timestamp", "open", "high", "low", "close"]

# Backward-compatible alias used by older imports / docs.
TIMEFRAME_RULES: dict[str, str] = {
    "M1": "1min",
    "M5": "5min",
    "M15": "15min",
    "M30": "30min",
    "H1": "1h",
    "H4": "4h",
    "D1": "1D",
}


def _aware_utc(ts: datetime | pd.Timestamp) -> pd.Timestamp:
    stamp = pd.Timestamp(ts)
    if stamp.tzinfo is None:
        return stamp.tz_localize("UTC")
    return stamp.tz_convert("UTC")


def parse_timestamp_column(series: pd.Series) -> pd.Series:
    """Parse mixed timestamp formats: epoch ms/s or datetime strings."""
    if series.empty:
        return pd.to_datetime(series, utc=True)

    sample = series.dropna().astype(str).str.strip().head(32)
    if sample.empty:
        return pd.to_datetime(series, utc=True, errors="coerce")

    numeric_ok = True
    numeric_vals: list[float] = []
    for raw in sample:
        try:
            numeric_vals.append(float(raw))
        except ValueError:
            numeric_ok = False
            break

    if numeric_ok and numeric_vals:
        median = sorted(numeric_vals)[len(numeric_vals) // 2]
        unit = "ms" if median >= 1_000_000_000_000 else "s"
        return pd.to_datetime(pd.to_numeric(series, errors="coerce"), unit=unit, utc=True)

    return pd.to_datetime(series, utc=True, errors="coerce")


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path, usecols=lambda c: str(c).lower() in OHLC_COLUMNS or c in OHLC_COLUMNS)
    except ValueError:
        # Header mismatch / corrupt — try without usecols then normalize.
        frame = pd.read_csv(path)
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    missing = [c for c in OHLC_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}")

    frame = frame[OHLC_COLUMNS].copy()
    frame["timestamp"] = parse_timestamp_column(frame["timestamp"])
    frame = frame.dropna(subset=["timestamp"])
    for col in ("open", "high", "low", "close"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.dropna(subset=["open", "high", "low", "close"])
    frame = frame.set_index("timestamp").sort_index()
    return frame


def _cache_dir(data_root: Path) -> Path:
    path = data_root / ".cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


CACHE_EXT = ".parquet"
LEGACY_CACHE_EXT = ".pkl"


def _m1_cache_path(data_root: Path, slug: str, files: list[CatalogFile]) -> Path:
    digest = hashlib.sha1()
    digest.update(slug.encode())
    for item in files:
        st = item.path.stat()
        digest.update(f"{item.path.name}:{st.st_mtime_ns}:{st.st_size}".encode())
    return _cache_dir(data_root) / slug / f"m1-{digest.hexdigest()[:16]}{CACHE_EXT}"


def _resample_cache_path(
    data_root: Path,
    slug: str,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    files: list[CatalogFile],
) -> Path:
    digest = hashlib.sha1()
    digest.update(slug.encode())
    digest.update(normalize_timeframe(timeframe).encode())
    digest.update(repr(start).encode())
    digest.update(repr(end).encode())
    for item in files:
        st = item.path.stat()
        digest.update(f"{item.path.name}:{st.st_mtime_ns}:{st.st_size}".encode())
    return (
        _cache_dir(data_root)
        / slug
        / f"{normalize_timeframe(timeframe).lower()}-{digest.hexdigest()[:16]}{CACHE_EXT}"
    )


def _legacy_pickle_path(path: Path) -> Path:
    return path.with_suffix(LEGACY_CACHE_EXT)


def _unlink_quiet(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.debug("Could not remove %s", path, exc_info=True)


def _load_frame_cache(path: Path) -> pd.DataFrame | None:
    if path.is_file():
        try:
            return pd.read_parquet(path)
        except Exception:
            logger.warning("Ignoring corrupt Parquet bar cache %s", path)
            _unlink_quiet(path)
            return None

    # One-shot migration from Phase F pickle caches (same digest stem).
    legacy = _legacy_pickle_path(path)
    if legacy.is_file():
        try:
            frame = pd.read_pickle(legacy)
            _save_frame_cache(path, frame)
            _unlink_quiet(legacy)
            return frame
        except Exception:
            logger.warning("Ignoring corrupt legacy pickle cache %s", legacy)
            _unlink_quiet(legacy)
            return None
    return None


def _save_frame_cache(path: Path, frame: pd.DataFrame) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        frame.to_parquet(tmp, engine="pyarrow")
        tmp.replace(path)
        _unlink_quiet(_legacy_pickle_path(path))
    except Exception:
        logger.warning("Could not write bar cache %s", path, exc_info=True)
        _unlink_quiet(path.with_suffix(path.suffix + ".tmp"))


def _read_csvs_parallel(files: list[CatalogFile], max_workers: int) -> list[pd.DataFrame]:
    if not files:
        return []
    workers = max(1, min(max_workers, len(files)))
    if workers == 1 or len(files) == 1:
        return [_read_csv(item.path) for item in files]

    frames: list[pd.DataFrame | None] = [None] * len(files)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_read_csv, item.path): idx for idx, item in enumerate(files)}
        for fut in as_completed(futures):
            idx = futures[fut]
            frames[idx] = fut.result()
    return [f for f in frames if f is not None and not f.empty]


def select_catalog_files(
    slug: str,
    data_root: Path,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    files: tuple[CatalogFile, ...] | None = None,
) -> list[CatalogFile]:
    slug_dir = data_root / slug
    if not slug_dir.is_dir():
        raise FileNotFoundError(f"Unknown catalog slug: {slug}")

    catalog_files = list(files) if files is not None else _collect_csv_files(slug_dir)
    if not catalog_files:
        raise FileNotFoundError(f"No CSV files for slug: {slug}")

    start_ts = _aware_utc(start).to_pydatetime() if start is not None else None
    end_ts = _aware_utc(end).to_pydatetime() if end is not None else None
    filtered = [item for item in catalog_files if file_covers_range(item.path, start_ts, end_ts)]
    return filtered or catalog_files


def load_m1_bars(
    slug: str,
    data_root: Path,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    files: tuple[CatalogFile, ...] | None = None,
    max_workers: int | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Load M1 bars for *slug*, optionally filtered to [start, end].

    Uses month shards preferentially (see catalog), parallel CSV reads, and an
    optional on-disk Parquet cache under ``data/.cache/``.
    """
    from django.conf import settings

    workers = max_workers
    if workers is None:
        workers = int(getattr(settings, "TRADEBOT_BACKTEST_LOAD_WORKERS", 4))

    catalog_files = select_catalog_files(slug, data_root, start=start, end=end, files=files)
    cache_path = _m1_cache_path(data_root, slug, catalog_files) if use_cache else None
    bars: pd.DataFrame | None = _load_frame_cache(cache_path) if cache_path else None

    if bars is None:
        frames = _read_csvs_parallel(catalog_files, workers)
        if not frames:
            raise FileNotFoundError(f"No readable CSV rows for slug: {slug}")
        bars = pd.concat(frames).sort_index()
        bars = bars[~bars.index.duplicated(keep="last")]
        if cache_path is not None:
            _save_frame_cache(cache_path, bars)

    if start is not None:
        bars = bars.loc[_aware_utc(start) :]
    if end is not None:
        bars = bars.loc[: _aware_utc(end)]
    return bars


def resample_bars(bars: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    tf = normalize_timeframe(timeframe)
    if tf == "M1":
        return bars.copy()

    rule = pandas_resample_rule(tf)
    ohlc = bars.resample(rule).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    )
    return ohlc.dropna(how="any")


def align_htf(primary: pd.DataFrame, htf: pd.DataFrame) -> pd.DataFrame:
    """Forward-fill higher-timeframe OHLC onto primary bar index."""
    if primary.empty or htf.empty:
        return htf
    return htf.reindex(primary.index, method="ffill")


def prepare_primary_and_htf(
    m1: pd.DataFrame,
    timeframe: str,
    htf_timeframe: str | None = None,
    *,
    parallel: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Resample M1 into primary TF and optional coarser HTF series."""
    primary_tf = normalize_timeframe(timeframe)
    htf_tf = normalize_timeframe(htf_timeframe or "")

    if not htf_tf:
        return resample_bars(m1, primary_tf), None
    if not is_higher_timeframe(htf_tf, primary_tf):
        raise ValueError(
            f"HTF timeframe {htf_tf} must be higher than primary timeframe {primary_tf}."
        )

    if not parallel or primary_tf == "M1":
        return resample_bars(m1, primary_tf), resample_bars(m1, htf_tf)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_primary = pool.submit(resample_bars, m1, primary_tf)
        fut_htf = pool.submit(resample_bars, m1, htf_tf)
        return fut_primary.result(), fut_htf.result()


def load_prepared_bars(
    slug: str,
    data_root: Path,
    timeframe: str,
    *,
    htf_timeframe: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    use_cache: bool = True,
    max_workers: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Load M1 → resample primary (+ HTF) with disk cache of resampled frames."""
    catalog_files = select_catalog_files(slug, data_root, start=start, end=end)
    primary_tf = normalize_timeframe(timeframe)
    htf_tf = normalize_timeframe(htf_timeframe or "")

    primary_cache = (
        _resample_cache_path(data_root, slug, primary_tf, start, end, catalog_files)
        if use_cache
        else None
    )
    htf_cache = (
        _resample_cache_path(data_root, slug, htf_tf, start, end, catalog_files)
        if use_cache and htf_tf
        else None
    )

    primary = _load_frame_cache(primary_cache) if primary_cache else None
    htf = _load_frame_cache(htf_cache) if htf_cache else None

    if primary is not None and (not htf_tf or htf is not None):
        return primary, htf

    m1 = load_m1_bars(
        slug,
        data_root,
        start=start,
        end=end,
        files=tuple(catalog_files),
        max_workers=max_workers,
        use_cache=use_cache,
    )
    primary, htf = prepare_primary_and_htf(m1, primary_tf, htf_tf or None)

    if primary_cache is not None:
        _save_frame_cache(primary_cache, primary)
    if htf_cache is not None and htf is not None:
        _save_frame_cache(htf_cache, htf)
    return primary, htf
