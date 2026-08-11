"""Main detection pipeline — thin wrapper over shared pattern core."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import detector._bootstrap  # noqa: F401
from apps.strategies.patterns.bars import Bar
from apps.strategies.patterns.head_shoulders.detect import detect_on_bars as _detect_on_bars
from apps.strategies.patterns.head_shoulders.spec import HSSpec, get_spec
from harness.bars import Bar as HarnessBar, load_bars_csv


def _to_pattern_bars(bars: list[HarnessBar]) -> list[Bar]:
    return [
        Bar(
            time=b.time,
            open=b.open,
            high=b.high,
            low=b.low,
            close=b.close,
            volume=b.volume,
        )
        for b in bars
    ]


def detect_on_bars(
    bars: list[HarnessBar],
    symbol: str,
    timeframe: str,
    spec: HSSpec | None = None,
    *,
    entry_mode: str = "A",
    trade_mode: str = "classic",
) -> list[dict[str, Any]]:
    return _detect_on_bars(
        _to_pattern_bars(bars),
        symbol,
        timeframe,
        spec,
        entry_mode=entry_mode,
        trade_mode=trade_mode,
    )


def detect_patterns(
    bars_dir: Path,
    symbol: str,
    timeframe: str,
    *,
    spec: HSSpec | None = None,
    entry_mode: str = "A",
    trade_mode: str = "classic",
    bars_file: str | None = None,
) -> list[dict[str, Any]]:
    path = bars_dir / (bars_file or f"{symbol}_{timeframe}.csv")
    bars = load_bars_csv(path)
    return detect_on_bars(
        bars, symbol, timeframe, spec, entry_mode=entry_mode, trade_mode=trade_mode
    )


__all__ = ["detect_on_bars", "detect_patterns", "HSSpec", "get_spec"]
