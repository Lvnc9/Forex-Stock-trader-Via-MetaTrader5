from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from apps.marketdata.catalog import CatalogFile, _collect_csv_files

OHLC_COLUMNS = ["timestamp", "open", "high", "low", "close"]

TIMEFRAME_RULES: dict[str, str] = {
    "M1": "1min",
    "M5": "5min",
    "M15": "15min",
    "M30": "30min",
    "H1": "1h",
    "H4": "4h",
    "D1": "1D",
}


def _read_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, usecols=OHLC_COLUMNS)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
    frame = frame.set_index("timestamp").sort_index()
    return frame


def load_m1_bars(
    slug: str,
    data_root: Path,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    files: tuple[CatalogFile, ...] | None = None,
) -> pd.DataFrame:
    slug_dir = data_root / slug
    if not slug_dir.is_dir():
        raise FileNotFoundError(f"Unknown catalog slug: {slug}")

    catalog_files = list(files) if files is not None else _collect_csv_files(slug_dir)
    if not catalog_files:
        raise FileNotFoundError(f"No CSV files for slug: {slug}")

    frames = [_read_csv(item.path) for item in catalog_files]
    bars = pd.concat(frames).sort_index()
    bars = bars[~bars.index.duplicated(keep="last")]

    if start is not None:
        start_ts = pd.Timestamp(start).tz_convert("UTC") if pd.Timestamp(start).tzinfo else pd.Timestamp(start, tz="UTC")
        bars = bars.loc[start_ts:]
    if end is not None:
        end_ts = pd.Timestamp(end).tz_convert("UTC") if pd.Timestamp(end).tzinfo else pd.Timestamp(end, tz="UTC")
        bars = bars.loc[:end_ts]

    return bars


def resample_bars(bars: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    rule = TIMEFRAME_RULES.get(timeframe.upper())
    if rule is None:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    if timeframe.upper() == "M1":
        return bars.copy()

    ohlc = bars.resample(rule).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    )
    return ohlc.dropna(how="any")


def align_htf(primary: pd.DataFrame, htf: pd.DataFrame) -> pd.DataFrame:
    """Forward-fill higher-timeframe OHLC onto primary bar index."""
    if primary.empty or htf.empty:
        return htf
    aligned = htf.reindex(primary.index, method="ffill")
    return aligned


def prepare_primary_and_htf(
    m1: pd.DataFrame,
    timeframe: str,
    htf_timeframe: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Resample M1 into primary TF and optional coarser HTF series."""
    from apps.marketdata.timeframes import is_higher_timeframe, normalize_timeframe

    primary = resample_bars(m1, timeframe)
    htf_tf = normalize_timeframe(htf_timeframe or "")
    if not htf_tf:
        return primary, None
    if not is_higher_timeframe(htf_tf, timeframe):
        raise ValueError(
            f"HTF timeframe {htf_tf} must be higher than primary timeframe {normalize_timeframe(timeframe)}."
        )
    return primary, resample_bars(m1, htf_tf)