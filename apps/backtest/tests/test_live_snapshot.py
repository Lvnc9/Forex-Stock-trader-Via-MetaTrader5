"""Live snapshot persistence during backtest runs."""

from __future__ import annotations

from datetime import date

from django.test import TestCase

from apps.backtest.models import BacktestRun
from apps.backtest.progress import update_run_live_snapshot
from apps.strategies.models import Strategy


class LiveSnapshotTests(TestCase):
    def setUp(self) -> None:
        self.strategy = Strategy.objects.create(
            name="Snap",
            slug="snap-strat",
            module_path="apps.strategies.library.ma_crossover",
            parameters={"fast_period": 5, "slow_period": 20},
        )
        self.run = BacktestRun.objects.create(
            strategy=self.strategy,
            catalog_slug="eurusd",
            timeframe="M5",
            start=date(2024, 1, 1),
            end=date(2024, 1, 2),
            initial_balance=10_000,
            status=BacktestRun.Status.RUNNING,
        )

    def test_update_run_live_snapshot_persists_partial_state(self) -> None:
        trades = [
            {
                "entry_time": "2024-01-01T10:00:00+00:00",
                "exit_time": "2024-01-01T11:00:00+00:00",
                "side": "long",
                "entry_price": 1.0,
                "exit_price": 1.01,
                "pnl": 100.0,
                "exit_reason": "signal_exit",
            }
        ]
        metrics = {
            "win_rate_pct": 100.0,
            "net_return_pct": 1.0,
            "profit_factor": 1.0,
            "max_drawdown_pct": 0.0,
            "trade_count": 1,
            "winning_trades": 1,
            "losing_trades": 0,
            "final_balance": 10_100.0,
        }
        equity_tail = [{"t": "2024-01-01T11:00:00+00:00", "equity": 10_100.0}]
        updated = update_run_live_snapshot(
            self.run,
            pct=45.0,
            message="Trade 1",
            trades=trades,
            metrics=metrics,
            equity_curve_tail=equity_tail,
        )
        self.assertTrue(updated)
        self.run.refresh_from_db()
        self.assertEqual(self.run.progress_pct, 45.0)
        self.assertEqual(self.run.progress_message, "Trade 1")
        self.assertEqual(len(self.run.trades), 1)
        self.assertEqual(self.run.metrics["win_rate_pct"], 100.0)
        self.assertEqual(self.run.equity_curve, equity_tail)

    def test_snapshot_skips_completed_run(self) -> None:
        self.run.status = BacktestRun.Status.COMPLETED
        self.run.save(update_fields=["status"])
        updated = update_run_live_snapshot(
            self.run,
            pct=50.0,
            message="Should not apply",
            trades=[],
            metrics={},
            equity_curve_tail=[],
        )
        self.assertFalse(updated)
