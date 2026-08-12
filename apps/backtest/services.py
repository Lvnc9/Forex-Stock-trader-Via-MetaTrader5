from __future__ import annotations

import signal
import threading
from datetime import datetime, time

from django.conf import settings
from django.utils import timezone

from apps.backtest.constants import BACKTEST_TIMEOUT_SECONDS, MAX_BACKTEST_BARS
from apps.backtest.data_handler import BacktestDataHandler
from apps.backtest.metrics import compute_metrics, downsample_equity
from apps.backtest.models import BacktestRun
from apps.backtest.portfolio import Portfolio
from apps.backtest.progress import (
    fail_orphaned_runs,
    mark_running,
    update_run_live_snapshot,
    update_run_progress,
)
from apps.backtest.runner import BacktestRunner, TradeRecord
from apps.strategies.loader import instantiate_strategy


class BacktestTimeoutError(TimeoutError):
    """Raised when a single backtest exceeds the configured wall-clock limit."""


def _max_bars() -> int:
    return int(getattr(settings, "TRADEBOT_MAX_BACKTEST_BARS", MAX_BACKTEST_BARS))


def _timeout_seconds() -> int:
    return int(getattr(settings, "TRADEBOT_BACKTEST_TIMEOUT_SECONDS", BACKTEST_TIMEOUT_SECONDS))


def _timeout_handler(signum, frame) -> None:  # noqa: ARG001
    secs = _timeout_seconds()
    raise BacktestTimeoutError(
        f"Backtest exceeded {secs}s wall-clock limit. "
        "Raise TRADEBOT_BACKTEST_TIMEOUT_SECONDS or use a higher timeframe."
    )


def _can_use_sigalrm() -> bool:
    """SIGALRM is main-thread only; Celery / runserver worker threads must skip it."""
    if not hasattr(signal, "SIGALRM"):
        return False
    if _timeout_seconds() <= 0:
        return False
    return threading.current_thread() is threading.main_thread()


def _run_exists(pk: int) -> bool:
    return BacktestRun.objects.filter(pk=pk).exists()


def trade_to_dict(trade: TradeRecord) -> dict:
    return {
        "entry_time": trade.entry_time.isoformat(),
        "exit_time": trade.exit_time.isoformat(),
        "side": trade.side,
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "pnl": round(trade.pnl, 4),
        "exit_reason": trade.exit_reason,
    }


def open_position_dict(portfolio: Portfolio, mark: float) -> dict | None:
    position = portfolio.position
    if position is None:
        return None
    unrealized = portfolio.broker.unrealized_pnl(position, mark)
    return {
        "side": position.side,
        "entry_price": position.entry_price,
        "entry_time": position.entry_time.isoformat(),
        "units": position.units,
        "unrealized_pnl": round(unrealized, 4),
        "mark_price": mark,
    }


def execute_backtest(run: BacktestRun) -> BacktestRun:
    """Load bars (primary + optional HTF), run BacktestRunner, persist metrics."""
    if not _run_exists(run.pk):
        return run

    fail_orphaned_runs()
    mark_running(run)

    alarm_set = False
    try:
        timeout_secs = _timeout_seconds()
        if _can_use_sigalrm():
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(int(timeout_secs))
            alarm_set = True

        if not _run_exists(run.pk):
            return run

        params = run.strategy.runtime_parameters()
        overrides = dict(run.parameter_overrides or {})
        if overrides:
            params.update(overrides)
        strategy = instantiate_strategy(run.strategy.module_path, params)
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

        n_bars = len(bars)
        max_bars = _max_bars()
        if max_bars > 0 and n_bars > max_bars:
            raise ValueError(
                f"Too many bars ({n_bars:,} > {max_bars:,}). "
                "Raise TRADEBOT_MAX_BACKTEST_BARS, shorten the date range, "
                "or use a higher timeframe (H1/H4)."
            )

        update_run_progress(run, 8.0, f"Loaded {n_bars} {run.timeframe} bars")

        last_saved = [-1.0]
        initial_balance = float(run.initial_balance)

        def on_progress(pct: float, message: str) -> None:
            mapped = 8.0 + pct * 0.9
            if mapped - last_saved[0] >= 5.0 or mapped >= 99.0:
                if update_run_progress(run, mapped, message):
                    last_saved[0] = mapped

        def on_snapshot(
            pct: float,
            message: str,
            portfolio: Portfolio,
            equity_curve: list[dict],
            mark: float,
            *,
            force: bool = False,
        ) -> None:
            mapped = 8.0 + pct * 0.9
            if not force and mapped - last_saved[0] < 5.0 and mapped < 99.0:
                return
            current_equity = portfolio.equity(mark)
            metrics = compute_metrics(
                portfolio.trades,
                current_equity,
                initial_balance,
                equity_curve,
            )
            metrics["open_position"] = open_position_dict(portfolio, mark)
            if tf_meta:
                metrics.update(tf_meta)
            tail = downsample_equity(equity_curve, 300)
            if update_run_live_snapshot(
                run,
                pct=mapped,
                message=message,
                trades=[trade_to_dict(t) for t in portfolio.trades],
                metrics=metrics,
                equity_curve_tail=tail,
            ):
                last_saved[0] = mapped

        result = BacktestRunner().run(
            strategy,
            bars,
            htf_bars=htf_bars,
            initial_balance=initial_balance,
            spread_pct=float(run.spread_pct),
            commission=float(run.commission),
            sizing_mode=run.sizing_mode,
            lot_size=float(run.lot_size),
            contract_size=float(run.contract_size),
            progress_callback=on_progress,
            snapshot_callback=on_snapshot,
            timeframe_meta=tf_meta,
        )

        if not _run_exists(run.pk):
            return run

        run.metrics = result.metrics
        run.metrics["intrabar_rule"] = result.intrabar_rule
        if run.htf_timeframe:
            run.metrics["htf_timeframe"] = run.htf_timeframe
        if overrides:
            run.metrics["parameter_overrides"] = overrides
        run.equity_curve = result.equity_curve
        run.trades = [trade_to_dict(t) for t in result.trades]
        run.status = BacktestRun.Status.COMPLETED
        run.progress_pct = 100.0
        run.progress_message = "Completed"
        run.completed_at = timezone.now()
        run.error_message = ""
        run.save()
        return run
    except Exception as exc:
        if not _run_exists(run.pk):
            return run
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
    finally:
        if alarm_set:
            signal.alarm(0)


def _trade_to_dict(trade: TradeRecord) -> dict:
    """Backward-compatible alias for internal callers."""
    return trade_to_dict(trade)
