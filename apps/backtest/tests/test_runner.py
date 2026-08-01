import pandas as pd
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.backtest.constants import INTRABAR_RULE
from apps.backtest.metrics import downsample_equity
from apps.backtest.parallel import default_worker_count
from apps.backtest.runner import BacktestRunner, _Position
from apps.marketdata.loader import parse_timestamp_column, resample_bars
from apps.marketdata.timeframes import describe_backtest_timeframes, timeframe_minutes
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
        meta = describe_backtest_timeframes("M5")
        result = BacktestRunner().run(
            strategy, bars, initial_balance=10_000, warmup=15, timeframe_meta=meta
        )
        self.assertIn("win_rate_pct", result.metrics)
        self.assertEqual(result.metrics["primary_timeframe"], "M5")
        self.assertEqual(result.metrics["source_timeframe"], "M1")
        self.assertLessEqual(len(result.equity_curve), len(bars))


class TimestampParseTests(SimpleTestCase):
    def test_epoch_ms(self):
        series = pd.Series(["1609804800000", "1609804860000"])
        parsed = parse_timestamp_column(series)
        self.assertTrue(parsed.dt.tz is not None)
        self.assertEqual(parsed.iloc[0].year, 2021)

    def test_iso_strings(self):
        series = pd.Series(["2024-01-01T00:00:00Z", "2024-01-01T00:01:00+00:00"])
        parsed = parse_timestamp_column(series)
        self.assertEqual(len(parsed.dropna()), 2)

    def test_resample_m1_to_m5(self):
        index = pd.date_range("2024-01-01", periods=10, freq="1min", tz="UTC")
        close = pd.Series(range(10), dtype=float, index=index)
        m1 = pd.DataFrame(
            {"open": close, "high": close + 1, "low": close - 1, "close": close},
            index=index,
        )
        m5 = resample_bars(m1, "M5")
        self.assertEqual(timeframe_minutes("M5"), 5)
        self.assertLess(len(m5), len(m1))


class MetricsHelperTests(SimpleTestCase):
    def test_downsample_equity(self):
        curve = [{"t": str(i), "equity": float(i)} for i in range(1000)]
        sampled = downsample_equity(curve, 100)
        self.assertLessEqual(len(sampled), 101)
        self.assertEqual(sampled[-1]["equity"], 999.0)

    def test_default_workers_positive(self):
        self.assertGreaterEqual(default_worker_count(), 1)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class BacktestStatusEndpointTests(TestCase):
    def test_status_requires_login(self):
        from apps.strategies.models import Strategy

        strategy = Strategy.objects.create(
            name="T",
            slug="t-status",
            module_path="apps.strategies.library.ma_crossover",
            parameters={},
        )
        run = strategy.backtest_runs.create(
            catalog_slug="spx",
            timeframe="M5",
            start="2024-01-01",
            end="2024-01-02",
            status="running",
            progress_pct=42.5,
            progress_message="Simulating",
        )
        url = reverse("backtest:status", kwargs={"pk": run.pk})
        self.assertEqual(self.client.get(url).status_code, 302)
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user("u1", password="x")
        self.client.force_login(user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "running")
        self.assertAlmostEqual(data["progress_pct"], 42.5)
        self.assertFalse(data["done"])
