"""Progress helpers for long-running backtests (Celery / HTMX)."""

from __future__ import annotations

from django.utils import timezone


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
