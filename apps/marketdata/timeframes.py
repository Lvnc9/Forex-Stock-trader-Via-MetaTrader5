"""Shared timeframe ordering and helpers for primary + HTF selection.

Backtests always start from M1 OHLC on disk, then resample to the primary
timeframe (and optional HTF). Warmup, bar counts, and HTF gates all use these
helpers so the engine stays timeframe-aware.
"""

from __future__ import annotations

from datetime import timedelta

TIMEFRAME_ORDER: tuple[str, ...] = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")

TIMEFRAME_CHOICES: list[tuple[str, str]] = [(tf, tf) for tf in TIMEFRAME_ORDER]

HTF_TIMEFRAME_CHOICES: list[tuple[str, str]] = [("", "— none —"), *TIMEFRAME_CHOICES]

# Minutes per closed bar (D1 ≈ session-agnostic calendar day for resample).
TIMEFRAME_MINUTES: dict[str, int] = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}

# pandas resample rules used by the M1 loader.
TIMEFRAME_PANDAS_RULES: dict[str, str] = {
    "M1": "1min",
    "M5": "5min",
    "M15": "15min",
    "M30": "30min",
    "H1": "1h",
    "H4": "4h",
    "D1": "1D",
}

TIMEFRAME_LABELS: dict[str, str] = {
    "M1": "1 minute",
    "M5": "5 minutes",
    "M15": "15 minutes",
    "M30": "30 minutes",
    "H1": "1 hour",
    "H4": "4 hours",
    "D1": "1 day",
}


def normalize_timeframe(timeframe: str) -> str:
    return (timeframe or "").strip().upper()


def timeframe_rank(timeframe: str) -> int:
    tf = normalize_timeframe(timeframe)
    try:
        return TIMEFRAME_ORDER.index(tf)
    except ValueError as exc:
        raise ValueError(f"Unsupported timeframe: {timeframe}") from exc


def is_higher_timeframe(htf: str, primary: str) -> bool:
    """True when *htf* is strictly coarser than *primary*."""
    return timeframe_rank(htf) > timeframe_rank(primary)


def timeframe_minutes(timeframe: str) -> int:
    tf = normalize_timeframe(timeframe)
    try:
        return TIMEFRAME_MINUTES[tf]
    except KeyError as exc:
        raise ValueError(f"Unsupported timeframe: {timeframe}") from exc


def pandas_resample_rule(timeframe: str) -> str:
    tf = normalize_timeframe(timeframe)
    try:
        return TIMEFRAME_PANDAS_RULES[tf]
    except KeyError as exc:
        raise ValueError(f"Unsupported timeframe: {timeframe}") from exc


def bars_per_day(timeframe: str) -> float:
    """Approximate closed bars per calendar day (FX 24h session assumption)."""
    return 1440 / timeframe_minutes(timeframe)


def m1_bars_for_primary(count: int, timeframe: str) -> int:
    """How many M1 rows roughly feed *count* primary bars."""
    return int(count * timeframe_minutes(timeframe))


def bar_timedelta(timeframe: str) -> timedelta:
    return timedelta(minutes=timeframe_minutes(timeframe))


def describe_backtest_timeframes(primary: str, htf: str | None = None) -> dict:
    """Metadata stored on BacktestRun.metrics for UI / debugging."""
    primary_tf = normalize_timeframe(primary)
    htf_tf = normalize_timeframe(htf or "")
    meta = {
        "primary_timeframe": primary_tf,
        "primary_label": TIMEFRAME_LABELS.get(primary_tf, primary_tf),
        "primary_minutes": timeframe_minutes(primary_tf),
        "source_timeframe": "M1",
        "source_label": TIMEFRAME_LABELS["M1"],
        "resample_rule": pandas_resample_rule(primary_tf),
    }
    if htf_tf:
        meta["htf_timeframe"] = htf_tf
        meta["htf_label"] = TIMEFRAME_LABELS.get(htf_tf, htf_tf)
        meta["htf_minutes"] = timeframe_minutes(htf_tf)
        meta["htf_resample_rule"] = pandas_resample_rule(htf_tf)
    return meta
