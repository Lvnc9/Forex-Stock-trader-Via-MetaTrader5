"""Event-driven backtest runner: SignalEngine + Portfolio + Broker."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from apps.backtest.broker import SimulatedBroker
from apps.backtest.constants import EQUITY_CURVE_MAX_POINTS, INTRABAR_RULE
from apps.backtest.metrics import compute_metrics, downsample_equity, empty_metrics
from apps.backtest.portfolio import Portfolio
from apps.backtest.types import BacktestResult, Position, TradeRecord
from apps.strategies.base import BaseStrategy
from apps.strategies.engine import SignalEngine

# Backward-compatible aliases used by existing tests / services.
_Position = Position
__all__ = ["BacktestRunner", "BacktestResult", "TradeRecord", "Position", "_Position"]


class BacktestRunner:
    """Applies SignalEngine events with intrabar SL/TP and equity tracking.

    Timeframe contract: *bars* must already be resampled to the strategy's
    primary timeframe (M1 source → M5/H1/…). Optional *htf_bars* are a coarser
    series aligned by timestamp (no lookahead: engine slices ``htf.loc[:ts]``).
    """

    def __init__(self, engine: SignalEngine | None = None) -> None:
        self.engine = engine or SignalEngine()

    def run(
        self,
        strategy: BaseStrategy,
        bars: pd.DataFrame,
        *,
        htf_bars: pd.DataFrame | None = None,
        initial_balance: float = 10_000.0,
        spread_pct: float = 0.0,
        commission: float = 0.0,
        warmup: int | None = None,
        progress_callback: Callable[[float, str], None] | None = None,
        timeframe_meta: dict | None = None,
    ) -> BacktestResult:
        if bars.empty:
            result = BacktestResult(metrics=empty_metrics(initial_balance))
            if timeframe_meta:
                result.metrics.update(timeframe_meta)
            return result

        min_bars = warmup if warmup is not None else SignalEngine._warmup_bars(strategy)
        n = len(bars)

        def report(pct: float, message: str) -> None:
            if progress_callback is not None:
                progress_callback(pct, message)

        report(5.0, "Generating signals")
        events = self.engine.run(
            strategy,
            bars,
            htf_bars=htf_bars,
            warmup=min_bars,
            progress_callback=(
                (lambda p, m: report(5.0 + p * 0.55, m)) if progress_callback else None
            ),
        )
        signals_by_bar = {event.bar_index: event.signal for event in events}

        report(60.0, "Simulating portfolio")
        broker = SimulatedBroker(spread_pct=spread_pct, commission=commission)
        portfolio = Portfolio(broker, initial_balance=initial_balance)
        equity_curve: list[dict] = []

        # Progress stride for long runs (avoid DB write storms from callers).
        stride = max(n // 20, 1)

        for i in range(n):
            bar = bars.iloc[i]
            ts = bars.index[i]
            ready = i + 1 >= min_bars

            if ready:
                portfolio.maybe_intrabar_exit(bar, ts)
                signal = signals_by_bar.get(i)
                if signal is not None:
                    portfolio.apply_signal(signal, bar, ts)

            equity_curve.append(
                {"t": ts.isoformat(), "equity": round(portfolio.equity(float(bar["close"])), 4)}
            )

            if progress_callback is not None and (i % stride == 0 or i == n - 1):
                report(60.0 + (i + 1) / n * 35.0, f"Bar {i + 1}/{n}")

        if portfolio.position is not None:
            last_bar = bars.iloc[-1]
            ts = bars.index[-1]
            portfolio.force_close(last_bar, ts, "end_of_data")
            if equity_curve:
                equity_curve[-1]["equity"] = round(portfolio.cash, 4)

        report(96.0, "Computing metrics")
        curve = downsample_equity(equity_curve, EQUITY_CURVE_MAX_POINTS)
        metrics = compute_metrics(
            portfolio.trades, portfolio.cash, initial_balance, equity_curve
        )
        metrics["intrabar_rule"] = INTRABAR_RULE
        metrics["equity_points_stored"] = len(curve)
        metrics["equity_points_full"] = len(equity_curve)
        if timeframe_meta:
            metrics.update(timeframe_meta)

        report(100.0, "Done")
        return BacktestResult(
            trades=portfolio.trades,
            equity_curve=curve,
            metrics=metrics,
        )

    # --- Compat helpers for unit tests that call private methods ---

    @staticmethod
    def _check_intrabar_exit(position: Position, bar: pd.Series) -> tuple[float | None, str | None]:
        return SimulatedBroker.check_intrabar_exit(position, bar)
