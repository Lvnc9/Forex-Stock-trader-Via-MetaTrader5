"""OHLCV bar types and conversions (no Django)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Bar:
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


def bars_from_dataframe(df: pd.DataFrame) -> list[Bar]:
    rows: list[Bar] = []
    for ts, row in df.iterrows():
        vol = None
        if "volume" in df.columns and pd.notna(row.get("volume")):
            vol = float(row["volume"])
        rows.append(
            Bar(
                time=str(ts),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=vol,
            )
        )
    return rows
