import pandas as pd
from django.test import SimpleTestCase

from apps.backtest.constants import INTRABAR_RULE
from apps.backtest.runner import BacktestRunner, _Position
from apps.strategies.library.ma_crossover import MACrossoverStrategy


class IntrabarExitTests(SimpleTestCase):
    def test_long_stop_loss_before_take_profit_when_both_hit(self):
        pos = _Position(
            side="long",
            entry_price=100.0,
            entry_time=pd.Timestamp("2024-01-01", tz="UTC"),
            stop_loss=98.0,
            take_profit=102.0,
            units=1.0,
        )
        bar = pd.Series({"open": 100, "high": 103, "low": 97, "close": 101})
        price, reason = BacktestRunner._check_intrabar_exit(pos, bar)
        self.assertEqual(price, 98.0)
        self.assertEqual(reason, "stop_loss")

    def test_intrabar_rule_documented(self):
        self.assertEqual(INTRABAR_RULE, "stop_loss_before_take_profit")


class BacktestRunnerTests(SimpleTestCase):
    def test_runner_produces_metrics_and_equity(self):
        index = pd.date_range("2024-01-01", periods=200, freq="5min", tz="UTC")
        close = pd.Series([100 + (i % 20) for i in range(200)], dtype=float, index=index)
        bars = pd.DataFrame(
            {
                "open": close,
                "high": close + 2,
                "low": close - 2,
                "close": close,
            },
            index=index,
        )
        strategy = MACrossoverStrategy({"fast_period": 3, "slow_period": 8})
        result = BacktestRunner().run(strategy, bars, initial_balance=10_000, warmup=15)
        self.assertIn("win_rate_pct", result.metrics)
        self.assertEqual(len(result.equity_curve), len(bars))
