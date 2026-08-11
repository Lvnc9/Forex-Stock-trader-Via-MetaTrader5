"""Timeframe-aware market data preparation for backtests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from apps.marketdata.loader import load_prepared_bars
from apps.marketdata.timeframes import describe_backtest_timeframes, normalize_timeframe


class BacktestDataHandler:
    """Loads M1 source bars and prepares primary (+ optional HTF) series."""

    def __init__(self, data_root: Path, *, max_workers: int | None = None, use_cache: bool = True):
        self.data_root = Path(data_root)
        self.max_workers = max_workers
        self.use_cache = use_cache

    def load(
        self,
        slug: str,
        timeframe: str,
        *,
        htf_timeframe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame | None, dict]:
        primary_tf = normalize_timeframe(timeframe)
        htf_tf = normalize_timeframe(htf_timeframe or "") or None
        bars, htf_bars = load_prepared_bars(
            slug,
            self.data_root,
            primary_tf,
            htf_timeframe=htf_tf,
            start=start,
            end=end,
            use_cache=self.use_cache,
            max_workers=self.max_workers,
        )
        meta = describe_backtest_timeframes(primary_tf, htf_tf)
        meta["bar_count"] = int(len(bars))
        meta["htf_bar_count"] = int(len(htf_bars)) if htf_bars is not None else 0
        if not bars.empty:
            meta["first_bar"] = bars.index[0].isoformat()
            meta["last_bar"] = bars.index[-1].isoformat()
        return bars, htf_bars, meta
