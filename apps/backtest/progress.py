"""Progress helpers for long-running backtests (Celery / HTMX)."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.backtest.constants import ORPHAN_RUNNING_MINUTES

LIVE_EQUITY_TAIL_MAX = 300


def _active_run_qs(pk: int):
    from apps.backtest.models import BacktestRun

    return BacktestRun.objects.filter(
        pk=pk,
        status__in=(BacktestRun.Status.PENDING, BacktestRun.Status.RUNNING),
    )


def update_run_progress(run, pct: float, message: str = "") -> bool:
    """Persist coarse progress on *run* without clobbering completed status."""
    updated = _active_run_qs(run.pk).update(
        progress_pct=max(0.0, min(100.0, float(pct))),
        progress_message=(message or "")[:240],
    )
    if updated:
        run.progress_pct = max(0.0, min(100.0, float(pct)))
        run.progress_message = (message or "")[:240]
    return bool(updated)


def update_run_live_snapshot(
    run,
    *,
    pct: float,
    message: str,
    trades: list[dict],
    metrics: dict,
    equity_curve_tail: list[dict],
) -> bool:
    """Persist partial trades/metrics/equity while a run is active."""
    tail = equity_curve_tail[-LIVE_EQUITY_TAIL_MAX:]
    updated = _active_run_qs(run.pk).update(
        progress_pct=max(0.0, min(100.0, float(pct))),
        progress_message=(message or "")[:240],
        trades=trades,
        metrics=metrics,
        equity_curve=tail,
    )
    if updated:
        run.progress_pct = max(0.0, min(100.0, float(pct)))
        run.progress_message = (message or "")[:240]
        run.trades = trades
        run.metrics = metrics
        run.equity_curve = tail
    return bool(updated)


def mark_running(run) -> None:
    from apps.backtest.models import BacktestRun

    if not BacktestRun.objects.filter(pk=run.pk).exists():
        return
    run.status = BacktestRun.Status.RUNNING
    run.progress_pct = 0.0
    run.progress_message = "Starting"
    run.error_message = ""
    run.save(update_fields=["status", "progress_pct", "progress_message", "error_message"])


def fail_orphaned_runs(*, older_than_minutes: int | None = None) -> int:
    """Mark stuck pending/running runs as failed. Returns count updated."""
    from django.conf import settings

    from apps.backtest.models import BacktestRun

    if older_than_minutes is None:
        minutes = int(
            getattr(settings, "TRADEBOT_ORPHAN_RUNNING_MINUTES", ORPHAN_RUNNING_MINUTES)
        )
    else:
        minutes = older_than_minutes
    qs = BacktestRun.objects.filter(
        status__in=(BacktestRun.Status.PENDING, BacktestRun.Status.RUNNING),
    )
    if minutes > 0:
        cutoff = timezone.now() - timedelta(minutes=minutes)
        qs = qs.filter(created_at__lt=cutoff)
    msg = (
        f"Interrupted or stuck (no completion within {max(minutes, 1)} minutes). "
        "Re-run; for multi-year M1 use Celery async and expect a long wait. "
        "Raise TRADEBOT_ORPHAN_RUNNING_MINUTES if the job is still legitimately running."
    )
    return qs.update(
        status=BacktestRun.Status.FAILED,
        error_message=msg,
        progress_message="Failed (orphaned)",
        completed_at=timezone.now(),
    )
