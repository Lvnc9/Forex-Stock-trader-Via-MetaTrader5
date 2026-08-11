"""Shared live/backtest position intent helpers (no MT5 dependency)."""

from __future__ import annotations

from dataclasses import dataclass

from apps.strategies.signals import Signal, SignalAction


@dataclass(frozen=True)
class PositionIntent:
    """What the executor should do given an open side and a new signal."""

    close_first: bool
    open_side: str | None  # "long" | "short" | None
    stop_loss: float | None = None
    take_profit: float | None = None


def resolve_signal_intent(signal: Signal, open_side: str | None) -> PositionIntent:
    """
    Align live agent with backtester flip rules:
    - EXIT / CLOSE_ALL → close only
    - ENTER same side → no-op open
    - ENTER opposite side → close first, then open
    """
    action = signal.action
    if action in (SignalAction.EXIT, SignalAction.CLOSE_ALL):
        return PositionIntent(close_first=open_side is not None, open_side=None)

    want = "long" if action == SignalAction.ENTER_LONG else "short"
    if open_side == want:
        return PositionIntent(
            close_first=False,
            open_side=None,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )
    return PositionIntent(
        close_first=open_side is not None,
        open_side=want,
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
    )
