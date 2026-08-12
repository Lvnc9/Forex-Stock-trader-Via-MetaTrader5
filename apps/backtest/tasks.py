"""
Backtest task queue.

Default: CELERY_TASK_ALWAYS_EAGER=True (non-blocking thread in dev, no Redis needed).
Production async (keeps Django UI responsive on large M1 sets):
  export CELERY_TASK_ALWAYS_EAGER=False
  redis-server
  celery -A config worker -l info --concurrency=4
"""

from __future__ import annotations

import threading

from celery import shared_task

from apps.backtest.models import BacktestRun
from apps.backtest.services import execute_backtest


@shared_task(name="backtest.run", bind=True, soft_time_limit=14_400, time_limit=14_700)
def run_backtest_task(self, run_id: int) -> int:
    run = BacktestRun.objects.get(pk=run_id)
    execute_backtest(run)
    return run_id


@shared_task(name="backtest.sweep", bind=True, soft_time_limit=28_800, time_limit=29_100)
def run_sweep_task(self, run_ids: list[int]) -> list[int]:
    """Execute independent backtest runs via multiprocess pool (not the bar loop)."""
    from apps.backtest.sweep import execute_sweep_run_ids

    execute_sweep_run_ids(run_ids)
    return list(run_ids)


def _blocking_eager(blocking: bool | None) -> bool:
    from django.conf import settings

    if blocking is not None:
        return blocking
    return bool(getattr(settings, "TRADEBOT_BACKTEST_BLOCKING_EAGER", False))


def _execute_backtest_thread(run: BacktestRun) -> None:
    from django.db import close_old_connections

    close_old_connections()
    execute_backtest(run)


def enqueue_backtest(run: BacktestRun, *, blocking: bool | None = None) -> BacktestRun:
    """Queue (or eagerly run) a backtest. Returns immediately unless blocking=True."""
    from django.conf import settings

    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", True)
    if eager:
        if _blocking_eager(blocking):
            return execute_backtest(run)
        threading.Thread(target=_execute_backtest_thread, args=(run,), daemon=True).start()
        return run
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
