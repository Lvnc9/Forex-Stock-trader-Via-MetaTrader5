from __future__ import annotations

from datetime import datetime, time

from django.conf import settings
from django.utils import timezone

from apps.backtest.data_handler import BacktestDataHandler
from apps.backtest.models import BacktestRun
from apps.backtest.progress import mark_running, update_run_progress
from apps.backtest.runner import BacktestRunner, TradeRecord
from apps.strategies.loader import instantiate_strategy


def execute_backtest(run: BacktestRun) -> BacktestRun:
    """Load bars (primary + optional HTF), run BacktestRunner, persist metrics."""
    mark_running(run)

    try:
        strategy = instantiate_strategy(run.strategy.module_path, run.strategy.runtime_parameters())
        start_dt = timezone.make_aware(datetime.combine(run.start, time.min))
        end_dt = timezone.make_aware(datetime.combine(run.end, time.max))

        update_run_progress(run, 2.0, "Loading market data")
        handler = BacktestDataHandler(
            settings.TRADEBOT_DATA_ROOT,
            max_workers=int(getattr(settings, "TRADEBOT_BACKTEST_LOAD_WORKERS", 4)),
            use_cache=bool(getattr(settings, "TRADEBOT_BACKTEST_CACHE", True)),
        )
        bars, htf_bars, tf_meta = handler.load(
            run.catalog_slug,
            run.timeframe,
            htf_timeframe=run.htf_timeframe or None,
            start=start_dt,
            end=end_dt,
        )
        if bars.empty:
            raise ValueError("No bars in selected date range / timeframe.")

        update_run_progress(run, 8.0, f"Loaded {len(bars)} {run.timeframe} bars")

        # Throttle DB progress writes (every ~5%).
        last_saved = [-1.0]

        def on_progress(pct: float, message: str) -> None:
            mapped = 8.0 + pct * 0.9
            if mapped - last_saved[0] >= 5.0 or mapped >= 99.0:
                update_run_progress(run, mapped, message)
                last_saved[0] = mapped

        result = BacktestRunner().run(
            strategy,
            bars,
            htf_bars=htf_bars,
            initial_balance=float(run.initial_balance),
            spread_pct=float(run.spread_pct),
            commission=float(run.commission),
            sizing_mode=run.sizing_mode,
            lot_size=float(run.lot_size),
            contract_size=float(run.contract_size),
            progress_callback=on_progress,
            timeframe_meta=tf_meta,
        )

        run.metrics = result.metrics
        run.metrics["intrabar_rule"] = result.intrabar_rule
        if run.htf_timeframe:
            run.metrics["htf_timeframe"] = run.htf_timeframe
        run.equity_curve = result.equity_curve
        run.trades = [_trade_to_dict(t) for t in result.trades]
        run.status = BacktestRun.Status.COMPLETED
        run.progress_pct = 100.0
        run.progress_message = "Completed"
        run.completed_at = timezone.now()
        run.error_message = ""
        run.save()
        return run
    except Exception as exc:
        run.status = BacktestRun.Status.FAILED
        run.error_message = str(exc)
        run.progress_message = "Failed"
        run.completed_at = timezone.now()
        run.save(
            update_fields=[
                "status",
                "error_message",
                "progress_message",
                "completed_at",
            ]
        )
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
