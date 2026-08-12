from django.test import override_settings
from django.test import TestCase

from apps.backtest.models import BacktestRun
from apps.backtest.tasks import enqueue_backtest, run_backtest_task
from apps.strategies.models import Strategy


class CeleryEnqueueTests(TestCase):
    def setUp(self):
        self.strategy = Strategy.objects.create(
            name="S",
            slug="s-celery",
            module_path="apps.strategies.library.ma_crossover",
            parameters={"fast": 5, "slow": 20},
        )

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, TRADEBOT_BACKTEST_BLOCKING_EAGER=True)
    def test_eager_enqueue_runs_blocking(self):
        # Will fail data load but should not raise from task plumbing if execute handles it
        run = BacktestRun.objects.create(
            strategy=self.strategy,
            catalog_slug="__missing__",
            timeframe="M5",
            start="2024-01-01",
            end="2024-01-02",
            status=BacktestRun.Status.PENDING,
        )
        result = enqueue_backtest(run, blocking=True)
        result.refresh_from_db()
        self.assertIn(result.status, (BacktestRun.Status.FAILED, BacktestRun.Status.COMPLETED))

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, TRADEBOT_BACKTEST_BLOCKING_EAGER=False)
    def test_eager_enqueue_non_blocking_returns_before_finish(self):
        run = BacktestRun.objects.create(
            strategy=self.strategy,
            catalog_slug="__missing__",
            timeframe="M5",
            start="2024-01-01",
            end="2024-01-02",
            status=BacktestRun.Status.PENDING,
        )
        result = enqueue_backtest(run)
        self.assertEqual(result.pk, run.pk)
        # Thread may finish quickly; at minimum enqueue must not raise.

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_shared_task_callable(self):
        run = BacktestRun.objects.create(
            strategy=self.strategy,
            catalog_slug="__missing__",
            timeframe="M5",
            start="2024-01-01",
            end="2024-01-02",
            status=BacktestRun.Status.PENDING,
        )
        run_backtest_task(run.pk)
        run.refresh_from_db()
        self.assertIn(run.status, (BacktestRun.Status.FAILED, BacktestRun.Status.COMPLETED))
