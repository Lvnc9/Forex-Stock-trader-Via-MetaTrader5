"""Simulated broker: fills, spread, commission, conservative intrabar SL/TP."""

from __future__ import annotations

import pandas as pd

from apps.backtest.types import Position, TradeRecord


class SimulatedBroker:
    def __init__(self, *, spread_pct: float = 0.0, commission: float = 0.0) -> None:
        self.spread_pct = float(spread_pct)
        self.commission = float(commission)

    def entry_price(self, side: str, close: float) -> float:
        half = self.spread_pct / 2.0
        if side == "long":
            return close * (1 + half)
        return close * (1 - half)

    def exit_price(self, side: str, close: float) -> float:
        half = self.spread_pct / 2.0
        if side == "long":
            return close * (1 - half)
        return close * (1 + half)

    @staticmethod
    def check_intrabar_exit(position: Position, bar: pd.Series) -> tuple[float | None, str | None]:
        low = float(bar["low"])
        high = float(bar["high"])
        sl = position.stop_loss
        tp = position.take_profit

        if position.side == "long":
            sl_hit = sl is not None and low <= sl
            tp_hit = tp is not None and high >= tp
            if sl_hit and tp_hit:
                return sl, "stop_loss"
            if sl_hit:
                return sl, "stop_loss"
            if tp_hit:
                return tp, "take_profit"
        else:
            sl_hit = sl is not None and high >= sl
            tp_hit = tp is not None and low <= tp
            if sl_hit and tp_hit:
                return sl, "stop_loss"
            if sl_hit:
                return sl, "stop_loss"
            if tp_hit:
                return tp, "take_profit"
        return None, None

    @staticmethod
    def position_pnl(position: Position, exit_price: float) -> float:
        if position.side == "long":
            return (exit_price - position.entry_price) * position.units
        return (position.entry_price - exit_price) * position.units

    @staticmethod
    def unrealized_pnl(position: Position, mark: float) -> float:
        if position.side == "long":
            return (mark - position.entry_price) * position.units
        return (position.entry_price - mark) * position.units

    def close_position(
        self,
        position: Position,
        exit_price: float,
        ts: pd.Timestamp,
        reason: str,
        cash: float,
        trades: list[TradeRecord],
    ) -> tuple[float, None]:
        pnl = self.position_pnl(position, exit_price) - self.commission
        cash += pnl
        trades.append(
            TradeRecord(
                entry_time=position.entry_time,
                exit_time=ts,
                side=position.side,
                entry_price=position.entry_price,
                exit_price=exit_price,
                pnl=pnl,
                exit_reason=reason,
            )
        )
        return cash, None

    def size_all_in(self, cash: float, entry: float) -> float:
        if entry <= 0 or cash <= 0:
            return 0.0
        return cash / entry
