"""Progress helpers for long-running backtests (Celery / HTMX)."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.backtest.constants import ORPHAN_RUNNING_MINUTES


def update_run_progress(run, pct: float, message: str = "") -> None:
    """Persist coarse progress on *run* without clobbering completed status."""
    from apps.backtest.models import BacktestRun

    if run.status not in (BacktestRun.Status.PENDING, BacktestRun.Status.RUNNING):
        return
    run.progress_pct = max(0.0, min(100.0, float(pct)))
    run.progress_message = (message or "")[:240]
    run.save(update_fields=["progress_pct", "progress_message"])


def mark_running(run) -> None:
    from apps.backtest.models import BacktestRun

    run.status = BacktestRun.Status.RUNNING
    run.progress_pct = 0.0
    run.progress_message = "Starting"
    run.error_message = ""
    run.save(update_fields=["status", "progress_pct", "progress_message", "error_message"])


def fail_orphaned_runs(*, older_than_minutes: int | None = None) -> int:
    """Mark stuck pending/running runs as failed. Returns count updated."""
    from apps.backtest.models import BacktestRun

    minutes = older_than_minutes if older_than_minutes is not None else ORPHAN_RUNNING_MINUTES
    qs = BacktestRun.objects.filter(
        status__in=(BacktestRun.Status.PENDING, BacktestRun.Status.RUNNING),
    )
    if minutes > 0:
        cutoff = timezone.now() - timedelta(minutes=minutes)
        qs = qs.filter(created_at__lt=cutoff)
    msg = (
        f"Interrupted or stuck (no completion within {max(minutes, 1)} minutes). "
        "Re-run with a higher timeframe (H1/H4) or a shorter date range. "
        "Head & shoulders must not use multi-year M1."
    )
    return qs.update(
        status=BacktestRun.Status.FAILED,
        error_message=msg,
        progress_message="Failed (orphaned)",
        completed_at=timezone.now(),
    )
