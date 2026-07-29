"""
Celery integration stub — backtests run synchronously in the web process for Phase 1c.

When Celery is configured later, replace the call site to delay ``run_backtest_task``.
"""

from apps.backtest.models import BacktestRun
from apps.backtest.services import execute_backtest


def run_backtest_task(run_id: int) -> int:
    run = BacktestRun.objects.get(pk=run_id)
    execute_backtest(run)
    return run_id


def enqueue_backtest(run: BacktestRun) -> BacktestRun:
    """Run now (sync). Swap for ``run_backtest_task.delay(run.pk)`` when Celery is enabled."""
    return execute_backtest(run)
