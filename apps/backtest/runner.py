from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from apps.backtest.constants import INTRABAR_RULE
from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext
from apps.strategies.indicators.registry import IndicatorRegistry
from apps.strategies.signals import Signal, SignalAction


@dataclass
class TradeRecord:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    side: str
    entry_price: float
    exit_price: float
    pnl: float
    exit_reason: str


@dataclass
class BacktestResult:
    trades: list[TradeRecord] = field(default_factory=list)
    equity_curve: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    intrabar_rule: str = INTRABAR_RULE


@dataclass
class _Position:
    side: str
    entry_price: float
    entry_time: pd.Timestamp
    stop_loss: float | None
    take_profit: float | None
    units: float


class BacktestRunner:
    def run(
        self,
        strategy: BaseStrategy,
        bars: pd.DataFrame,
        *,
        initial_balance: float = 10_000.0,
        spread_pct: float = 0.0,
        commission: float = 0.0,
        warmup: int | None = None,
    ) -> BacktestResult:
        if bars.empty:
            return BacktestResult(metrics=self._empty_metrics(initial_balance))

        min_bars = warmup if warmup is not None else self._warmup_bars(strategy)
        cash = float(initial_balance)
        position: _Position | None = None
        trades: list[TradeRecord] = []
        equity_curve: list[dict] = []

        for i in range(len(bars)):
            bar = bars.iloc[i]
            ts = bars.index[i]

            if i >= min_bars and position is not None:
                exit_price, reason = self._check_intrabar_exit(position, bar)
                if exit_price is not None and reason is not None:
                    cash, position = self._close_position(
                        position, exit_price, ts, reason, commission, cash, trades
                    )

            if i >= min_bars:
                window = bars.iloc[: i + 1]
                ctx = BarContext(
                    bar_index=i,
                    timestamp=ts,
                    bars=window,
                    parameters=strategy.parameters,
                    indicators=IndicatorRegistry(window),
                )
                signal = strategy.on_bar(ctx)
                if signal is not None:
                    cash, position = self._apply_signal(
                        signal, position, bar, ts, spread_pct, commission, cash, trades
                    )

            equity = cash
            if position is not None:
                equity += self._unrealized_pnl(position, float(bar["close"]))
            equity_curve.append({"t": ts.isoformat(), "equity": round(equity, 4)})

        if position is not None:
            last_bar = bars.iloc[-1]
            ts = bars.index[-1]
            exit_price = self._exit_price(position.side, float(last_bar["close"]), spread_pct)
            cash, _ = self._close_position(
                position, exit_price, ts, "end_of_data", commission, cash, trades
            )
            if equity_curve:
                equity_curve[-1]["equity"] = round(cash, 4)

        metrics = self._compute_metrics(trades, cash, initial_balance, equity_curve)
        return BacktestResult(trades=trades, equity_curve=equity_curve, metrics=metrics)

    def _apply_signal(
        self,
        signal: Signal,
        position: _Position | None,
        bar: pd.Series,
        ts: pd.Timestamp,
        spread_pct: float,
        commission: float,
        cash: float,
        trades: list[TradeRecord],
    ) -> tuple[float, _Position | None]:
        action = signal.action

        if action in (SignalAction.EXIT, SignalAction.CLOSE_ALL):
            if position is None:
                return cash, None
            exit_price = self._exit_price(position.side, float(bar["close"]), spread_pct)
            return self._close_position(position, exit_price, ts, "signal_exit", commission, cash, trades)

        if action == SignalAction.ENTER_LONG:
            if position is not None:
                if position.side == "long":
                    return cash, position
                exit_price = self._exit_price(position.side, float(bar["close"]), spread_pct)
                cash, position = self._close_position(
                    position, exit_price, ts, "signal_reverse", commission, cash, trades
                )
            entry = self._entry_price("long", float(bar["close"]), spread_pct)
            units = max(cash, 0.0) / entry if entry > 0 else 0.0
            if units <= 0:
                return cash, None
            return cash, _Position(
                side="long",
                entry_price=entry,
                entry_time=ts,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                units=units,
            )

        if action == SignalAction.ENTER_SHORT:
            if position is not None:
                if position.side == "short":
                    return cash, position
                exit_price = self._exit_price(position.side, float(bar["close"]), spread_pct)
                cash, position = self._close_position(
                    position, exit_price, ts, "signal_reverse", commission, cash, trades
                )
            entry = self._entry_price("short", float(bar["close"]), spread_pct)
            units = max(cash, 0.0) / entry if entry > 0 else 0.0
            if units <= 0:
                return cash, None
            return cash, _Position(
                side="short",
                entry_price=entry,
                entry_time=ts,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                units=units,
            )

        return cash, position

    def _close_position(
        self,
        position: _Position,
        exit_price: float,
        ts: pd.Timestamp,
        reason: str,
        commission: float,
        cash: float,
        trades: list[TradeRecord],
    ) -> tuple[float, None]:
        pnl = self._position_pnl(position, exit_price) - commission
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

    @staticmethod
    def _check_intrabar_exit(position: _Position, bar: pd.Series) -> tuple[float | None, str | None]:
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
    def _entry_price(side: str, close: float, spread_pct: float) -> float:
        half = spread_pct / 2.0
        if side == "long":
            return close * (1 + half)
        return close * (1 - half)

    @staticmethod
    def _exit_price(side: str, close: float, spread_pct: float) -> float:
        half = spread_pct / 2.0
        if side == "long":
            return close * (1 - half)
        return close * (1 + half)

    @staticmethod
    def _position_pnl(position: _Position, exit_price: float) -> float:
        if position.side == "long":
            return (exit_price - position.entry_price) * position.units
        return (position.entry_price - exit_price) * position.units

    @staticmethod
    def _unrealized_pnl(position: _Position, mark: float) -> float:
        if position.side == "long":
            return (mark - position.entry_price) * position.units
        return (position.entry_price - mark) * position.units

    @staticmethod
    def _warmup_bars(strategy: BaseStrategy) -> int:
        nums: list[int] = [2]
        for spec in strategy.parameter_schema:
            if spec.get("type") in ("int", "float"):
                nums.append(int(spec.get("max", spec.get("default", 2))))
        return max(nums) + 5

    @staticmethod
    def _empty_metrics(initial_balance: float) -> dict:
        return {
            "win_rate_pct": 0.0,
            "net_return_pct": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0,
            "trade_count": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "final_balance": initial_balance,
        }

    def _compute_metrics(
        self,
        trades: list[TradeRecord],
        final_balance: float,
        initial_balance: float,
        equity_curve: list[dict],
    ) -> dict:
        closed = len(trades)
        winners = sum(1 for t in trades if t.pnl > 0)
        losers = sum(1 for t in trades if t.pnl <= 0)
        win_rate = (winners / closed * 100.0) if closed else 0.0
        net_return = ((final_balance - initial_balance) / initial_balance * 100.0) if initial_balance else 0.0

        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)

        max_dd = self._max_drawdown_pct(equity_curve, initial_balance)

        return {
            "win_rate_pct": round(win_rate, 2),
            "net_return_pct": round(net_return, 2),
            "profit_factor": round(profit_factor, 4),
            "max_drawdown_pct": round(max_dd, 2),
            "trade_count": closed,
            "winning_trades": winners,
            "losing_trades": losers,
            "final_balance": round(final_balance, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
        }

    @staticmethod
    def _max_drawdown_pct(equity_curve: list[dict], initial_balance: float) -> float:
        if not equity_curve:
            return 0.0
        peak = float(initial_balance)
        max_dd = 0.0
        for point in equity_curve:
            eq = float(point["equity"])
            peak = max(peak, eq)
            if peak > 0:
                dd = (peak - eq) / peak * 100.0
                max_dd = max(max_dd, dd)
        return max_dd
