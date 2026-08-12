"""Backtest safety rails: max bars, orphan cleanup."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from apps.backtest.models import BacktestRun
from apps.backtest.progress import fail_orphaned_runs
from apps.backtest.services import _can_use_sigalrm, execute_backtest
from apps.strategies.models import Strategy


class SigalrmGuardTests(SimpleTestCase):
    def test_sigalrm_skipped_when_timeout_disabled(self) -> None:
        with override_settings(TRADEBOT_BACKTEST_TIMEOUT_SECONDS=0):
            self.assertFalse(_can_use_sigalrm())

    def test_sigalrm_skipped_on_worker_thread(self) -> None:
        import threading

        results: list[bool] = []

        def worker() -> None:
            with override_settings(TRADEBOT_BACKTEST_TIMEOUT_SECONDS=60):
                results.append(_can_use_sigalrm())

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        self.assertEqual(results, [False])


class OrphanCleanupTests(TestCase):
    def setUp(self) -> None:
        self.strategy = Strategy.objects.create(
            name="S",
            slug="orphan-s",
            module_path="apps.strategies.library.ma_crossover",
            parameters={},
        )

    def test_fail_orphaned_runs_marks_old_running(self) -> None:
        run = BacktestRun.objects.create(
            strategy=self.strategy,
            catalog_slug="eurusd",
            timeframe="M1",
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
            status=BacktestRun.Status.RUNNING,
            progress_pct=12.5,
            progress_message="Generating signals",
        )
        BacktestRun.objects.filter(pk=run.pk).update(
            created_at=timezone.now() - timedelta(minutes=60)
        )
        count = fail_orphaned_runs(older_than_minutes=30)
        self.assertEqual(count, 1)
        run.refresh_from_db()
        self.assertEqual(run.status, BacktestRun.Status.FAILED)
        self.assertIn("stuck", run.error_message.lower())

    def test_fail_all_stuck_ignores_age(self) -> None:
        run = BacktestRun.objects.create(
            strategy=self.strategy,
            catalog_slug="eurusd",
            timeframe="M5",
            start=date(2024, 1, 1),
            end=date(2024, 1, 2),
            status=BacktestRun.Status.PENDING,
        )
        count = fail_orphaned_runs(older_than_minutes=0)
        self.assertGreaterEqual(count, 1)
        run.refresh_from_db()
        self.assertEqual(run.status, BacktestRun.Status.FAILED)


class MaxBarsGuardTests(SimpleTestCase):
    @override_settings(TRADEBOT_MAX_BACKTEST_BARS=1_000)
    @patch("apps.backtest.services.BacktestDataHandler")
    @patch("apps.backtest.services.instantiate_strategy")
    def test_execute_rejects_too_many_bars(self, _inst, handler_cls) -> None:
        n = 1_010
        idx = pd.date_range("2024-01-01", periods=n, freq="min", tz="UTC")
        bars = pd.DataFrame(
            {
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
            },
            index=idx,
        )
        handler = MagicMock()
        handler.load.return_value = (bars, None, {"primary_label": "M1", "bar_count": n})
        handler_cls.return_value = handler

        run = MagicMock()
        run.strategy.runtime_parameters.return_value = {}
        run.parameter_overrides = {}
        run.catalog_slug = "xauusd"
        run.timeframe = "M1"
        run.htf_timeframe = ""
        run.start = date(2022, 1, 1)
        run.end = date(2025, 12, 31)
        run.initial_balance = 10_000
        run.spread_pct = 0.0
        run.commission = 0.0
        run.sizing_mode = "all_in"
        run.lot_size = 0.01
        run.contract_size = 100_000
        run.status = BacktestRun.Status.PENDING

        with patch("apps.backtest.services.fail_orphaned_runs"), patch(
            "apps.backtest.services.mark_running"
        ), patch("apps.backtest.services.update_run_progress"), patch(
            "apps.backtest.services._run_exists", return_value=True
        ), patch(
            "apps.backtest.services.timezone"
        ) as tz:
            tz.make_aware.side_effect = lambda dt: dt
            tz.now.return_value = timezone.now()
            result = execute_backtest(run)

        self.assertEqual(result.status, BacktestRun.Status.FAILED)
        self.assertIn("Too many bars", result.error_message)
