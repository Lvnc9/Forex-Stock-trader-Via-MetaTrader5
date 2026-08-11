"""
Backtest task queue.

Default: CELERY_TASK_ALWAYS_EAGER=True (sync, no Redis needed).
Production async (keeps Django UI responsive on large M1 sets):
  export CELERY_TASK_ALWAYS_EAGER=False
  redis-server
  celery -A config worker -l info --concurrency=4
"""

from __future__ import annotations

from celery import shared_task

from apps.backtest.models import BacktestRun
from apps.backtest.services import execute_backtest


@shared_task(name="backtest.run", bind=True, soft_time_limit=3600, time_limit=3900)
def run_backtest_task(self, run_id: int) -> int:
    run = BacktestRun.objects.get(pk=run_id)
    execute_backtest(run)
    return run_id


@shared_task(name="backtest.sweep", bind=True, soft_time_limit=7200, time_limit=7500)
def run_sweep_task(self, run_ids: list[int]) -> list[int]:
    """Execute independent backtest runs via multiprocess pool (not the bar loop)."""
    from apps.backtest.sweep import execute_sweep_run_ids

    execute_sweep_run_ids(run_ids)
    return list(run_ids)


def enqueue_backtest(run: BacktestRun) -> BacktestRun:
    """Queue (or eagerly run) a backtest. Returns the run after sync eager mode."""
    from django.conf import settings

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", True):
        return execute_backtest(run)
    run_backtest_task.delay(run.pk)
    return run


def enqueue_sweep(runs: list[BacktestRun]) -> list[BacktestRun]:
    """Queue a small parameter sweep; Celery keeps the request path responsive."""
    from django.conf import settings

    run_ids = [r.pk for r in runs]
    if not run_ids:
        return runs
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", True):
        from apps.backtest.sweep import execute_sweep_run_ids

        execute_sweep_run_ids(run_ids)
        return list(BacktestRun.objects.filter(pk__in=run_ids).order_by("id"))
    run_sweep_task.delay(run_ids)
    return runs
