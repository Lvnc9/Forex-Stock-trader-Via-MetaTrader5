"""Load OHLCV bar CSVs."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Bar:
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None


def _f(row: dict[str, str], *keys: str) -> float:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return float(row[k])
    raise KeyError(f"missing one of {keys} in row keys={list(row)}")


def load_bars_csv(path: Path) -> list[Bar]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"empty CSV: {path}")
        # normalize headers
        rows = []
        for raw in reader:
            row = {((k or "").strip().lower()): (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
            vol = None
            if "volume" in row and row["volume"] not in (None, ""):
                vol = float(row["volume"])
            elif "tick_volume" in row and row["tick_volume"] not in (None, ""):
                vol = float(row["tick_volume"])
            time_val = row.get("time") or row.get("datetime") or row.get("date")
            if time_val is None:
                raise ValueError(f"no time column in {path}")
            rows.append(
                Bar(
                    time=str(time_val),
                    open=_f(row, "open", "o"),
                    high=_f(row, "high", "h"),
                    low=_f(row, "low", "l"),
                    close=_f(row, "close", "c"),
                    volume=vol,
                )
            )
    # stable chronological order if times are ISO/sortable; else keep file order
    try:
        rows.sort(key=lambda b: b.time)
    except TypeError:
        pass
    return rows


def resolve_bars_path(bars_dir: Path, symbol: str, timeframe: str, bars_file: str | None) -> Path:
    if bars_file:
        p = bars_dir / bars_file
        if p.exists():
            return p
        raise FileNotFoundError(p)
    candidate = bars_dir / f"{symbol}_{timeframe}.csv"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(candidate)


def load_bars_for_label(
    bars_dir: Path,
    symbol: str,
    timeframe: str,
    bars_file: str | None,
    cache: dict[Path, list[Bar]],
) -> list[Bar]:
    path = resolve_bars_path(bars_dir, symbol, timeframe, bars_file)
    if path not in cache:
        cache[path] = load_bars_csv(path)
    return cache[path]
