"""
Backtest task queue.

Default: CELERY_TASK_ALWAYS_EAGER=True (sync, no Redis needed).
Production async: set CELERY_TASK_ALWAYS_EAGER=False and run:
  celery -A config worker -l info
"""

from __future__ import annotations

from celery import shared_task

from apps.backtest.models import BacktestRun
from apps.backtest.services import execute_backtest


@shared_task(name="backtest.run")
def run_backtest_task(run_id: int) -> int:
    run = BacktestRun.objects.get(pk=run_id)
    execute_backtest(run)
    return run_id


def enqueue_backtest(run: BacktestRun) -> BacktestRun:
    """Queue (or eagerly run) a backtest. Returns the run after sync eager mode."""
    from django.conf import settings

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", True):
        return execute_backtest(run)
    run_backtest_task.delay(run.pk)
    return run
