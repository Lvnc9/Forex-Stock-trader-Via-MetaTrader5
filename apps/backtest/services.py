from __future__ import annotations

from datetime import datetime, time

from django.conf import settings
from django.utils import timezone

from apps.backtest.models import BacktestRun
from apps.backtest.runner import BacktestRunner, TradeRecord
from apps.marketdata.loader import load_m1_bars, prepare_primary_and_htf
from apps.strategies.loader import instantiate_strategy


def execute_backtest(run: BacktestRun) -> BacktestRun:
    """Load bars (primary + optional HTF), run BacktestRunner, persist metrics."""
    run.status = BacktestRun.Status.RUNNING
    run.error_message = ""
    run.save(update_fields=["status", "error_message"])

    try:
        strategy = instantiate_strategy(run.strategy.module_path, run.strategy.parameters)
        start_dt = timezone.make_aware(datetime.combine(run.start, time.min))
        end_dt = timezone.make_aware(datetime.combine(run.end, time.max))
        m1 = load_m1_bars(
            run.catalog_slug,
            settings.TRADEBOT_DATA_ROOT,
            start=start_dt,
            end=end_dt,
        )
        bars, htf_bars = prepare_primary_and_htf(
            m1,
            run.timeframe,
            run.htf_timeframe or None,
        )
        if bars.empty:
            raise ValueError("No bars in selected date range / timeframe.")

        result = BacktestRunner().run(
            strategy,
            bars,
            htf_bars=htf_bars,
            initial_balance=float(run.initial_balance),
            spread_pct=float(run.spread_pct),
            commission=float(run.commission),
        )

        run.metrics = result.metrics
        run.metrics["intrabar_rule"] = result.intrabar_rule
        if run.htf_timeframe:
            run.metrics["htf_timeframe"] = run.htf_timeframe
        run.equity_curve = result.equity_curve
        run.trades = [_trade_to_dict(t) for t in result.trades]
        run.status = BacktestRun.Status.COMPLETED
        run.completed_at = timezone.now()
        run.save()
        return run
    except Exception as exc:
        run.status = BacktestRun.Status.FAILED
        run.error_message = str(exc)
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "error_message", "completed_at"])
        return run


def _trade_to_dict(trade: TradeRecord) -> dict:
    return {
        "entry_time": trade.entry_time.isoformat(),
        "exit_time": trade.exit_time.isoformat(),
        "side": trade.side,
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "pnl": round(trade.pnl, 4),
        "exit_reason": trade.exit_reason,
    }
