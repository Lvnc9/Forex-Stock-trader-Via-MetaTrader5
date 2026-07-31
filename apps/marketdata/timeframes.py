"""Shared timeframe ordering and helpers for primary + HTF selection."""

from __future__ import annotations

TIMEFRAME_ORDER: tuple[str, ...] = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")

TIMEFRAME_CHOICES: list[tuple[str, str]] = [(tf, tf) for tf in TIMEFRAME_ORDER]

HTF_TIMEFRAME_CHOICES: list[tuple[str, str]] = [("", "— none —"), *TIMEFRAME_CHOICES]


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
