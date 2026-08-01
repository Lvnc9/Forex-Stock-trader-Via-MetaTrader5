"""Portfolio state: cash, open position, equity marks."""

from __future__ import annotations

import pandas as pd

from apps.backtest.broker import SimulatedBroker
from apps.backtest.types import Position, TradeRecord
from apps.strategies.signals import Signal, SignalAction


class Portfolio:
    def __init__(
        self,
        broker: SimulatedBroker,
        *,
        initial_balance: float = 10_000.0,
    ) -> None:
        self.broker = broker
        self.initial_balance = float(initial_balance)
        self.cash = float(initial_balance)
        self.position: Position | None = None
        self.trades: list[TradeRecord] = []

    def equity(self, mark: float) -> float:
        value = self.cash
        if self.position is not None:
            value += self.broker.unrealized_pnl(self.position, mark)
        return value

    def maybe_intrabar_exit(self, bar: pd.Series, ts: pd.Timestamp) -> None:
        if self.position is None:
            return
        exit_price, reason = self.broker.check_intrabar_exit(self.position, bar)
        if exit_price is not None and reason is not None:
            self.cash, self.position = self.broker.close_position(
                self.position, exit_price, ts, reason, self.cash, self.trades
            )

    def apply_signal(self, signal: Signal, bar: pd.Series, ts: pd.Timestamp) -> None:
        action = signal.action
        if action in (SignalAction.EXIT, SignalAction.CLOSE_ALL):
            if self.position is None:
                return
            exit_price = self.broker.exit_price(self.position.side, float(bar["close"]))
            self.cash, self.position = self.broker.close_position(
                self.position, exit_price, ts, "signal_exit", self.cash, self.trades
            )
            return

        if action == SignalAction.ENTER_LONG:
            self._enter("long", signal, bar, ts)
            return
        if action == SignalAction.ENTER_SHORT:
            self._enter("short", signal, bar, ts)

    def _enter(self, side: str, signal: Signal, bar: pd.Series, ts: pd.Timestamp) -> None:
        if self.position is not None:
            if self.position.side == side:
                return
            exit_price = self.broker.exit_price(self.position.side, float(bar["close"]))
            self.cash, self.position = self.broker.close_position(
                self.position, exit_price, ts, "signal_reverse", self.cash, self.trades
            )

        entry = self.broker.entry_price(side, float(bar["close"]))
        units = self.broker.size_all_in(self.cash, entry)
        if units <= 0:
            self.position = None
            return
        self.position = Position(
            side=side,
            entry_price=entry,
            entry_time=ts,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            units=units,
        )

    def force_close(self, bar: pd.Series, ts: pd.Timestamp, reason: str = "end_of_data") -> None:
        if self.position is None:
            return
        exit_price = self.broker.exit_price(self.position.side, float(bar["close"]))
        self.cash, self.position = self.broker.close_position(
            self.position, exit_price, ts, reason, self.cash, self.trades
        )
