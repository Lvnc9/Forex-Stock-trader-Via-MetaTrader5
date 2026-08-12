from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

import pandas as pd
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.strategies.models import Strategy


@override_settings(
    TRADEBOT_BACKTEST_THERMAL_PROFILE="laptop",
    TRADEBOT_BACKTEST_CPU_FRACTION=0.7,
    TRADEBOT_BACKTEST_CORE_RESERVE=2,
)
class BenchmarkCommandTests(TestCase):
    def setUp(self) -> None:
        self.strategy = Strategy.objects.create(
            name="MA",
            slug="ma-bench",
            module_path="apps.strategies.library.ma_crossover",
            parameters={"fast_period": 5, "slow_period": 20},
        )

    @patch("apps.backtest.management.commands.benchmark_backtest.BacktestRunner")
    @patch("apps.backtest.management.commands.benchmark_backtest.BacktestDataHandler")
    def test_benchmark_command_prints_timings(self, handler_cls, runner_cls) -> None:
        idx = pd.date_range("2024-01-01", periods=10, freq="5min", tz="UTC")
        bars = pd.DataFrame(
            {"open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0},
            index=idx,
        )
        handler = MagicMock()
        handler.load.return_value = (bars, None, {"bar_count": 10})
        handler_cls.return_value = handler

        result = MagicMock()
        result.trades = []
        result.metrics = {"win_rate_pct": 0.0}
        runner_cls.return_value.run.return_value = result

        out = StringIO()
        call_command(
            "benchmark_backtest",
            strategy="ma-bench",
            catalog="eurusd",
            timeframe="M5",
            days=10,
            stdout=out,
        )
        text = out.getvalue()
        self.assertIn("benchmark load=", text)
        self.assertIn("compute_workers=8", text)
