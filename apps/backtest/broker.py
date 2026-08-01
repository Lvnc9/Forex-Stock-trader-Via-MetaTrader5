"""Simulated broker: fills, spread, commission, conservative intrabar SL/TP."""

from __future__ import annotations

import pandas as pd

from apps.backtest.types import Position, TradeRecord

# Match Deployment.lot_size defaults; 100_000 = standard FX contract (1.0 lot).
SIZING_ALL_IN = "all_in"
SIZING_FIXED_LOTS = "fixed_lots"
SIZING_MODES = (SIZING_ALL_IN, SIZING_FIXED_LOTS)
DEFAULT_CONTRACT_SIZE = 100_000.0
DEFAULT_LOT_SIZE = 0.01


class SimulatedBroker:
    def __init__(
        self,
        *,
        spread_pct: float = 0.0,
        commission: float = 0.0,
        sizing_mode: str = SIZING_ALL_IN,
        lot_size: float = DEFAULT_LOT_SIZE,
        contract_size: float = DEFAULT_CONTRACT_SIZE,
    ) -> None:
        mode = (sizing_mode or SIZING_ALL_IN).strip().lower()
        if mode not in SIZING_MODES:
            raise ValueError(f"Unknown sizing_mode {sizing_mode!r}; expected one of {SIZING_MODES}")
        self.spread_pct = float(spread_pct)
        self.commission = float(commission)
        self.sizing_mode = mode
        self.lot_size = float(lot_size)
        self.contract_size = float(contract_size)

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

    def size_fixed_lots(self) -> float:
        """Notional units = lot_size × contract_size (matches MT5 volume semantics)."""
        if self.lot_size <= 0 or self.contract_size <= 0:
            return 0.0
        return self.lot_size * self.contract_size

    def size_position(self, cash: float, entry: float) -> float:
        if self.sizing_mode == SIZING_FIXED_LOTS:
            return self.size_fixed_lots()
        return self.size_all_in(cash, entry)

    def sizing_meta(self) -> dict:
        return {
            "sizing_mode": self.sizing_mode,
            "lot_size": self.lot_size,
            "contract_size": self.contract_size,
        }
