import pandas as pd
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.backtest.broker import SIZING_FIXED_LOTS, SimulatedBroker
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


class SizingModeTests(SimpleTestCase):
    def _bars(self, n: int = 80) -> pd.DataFrame:
        index = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
        # Steady uptrend so MA crossover takes at least one long.
        close = pd.Series([100.0 + i * 0.5 for i in range(n)], dtype=float, index=index)
        return pd.DataFrame(
            {"open": close, "high": close + 1, "low": close - 1, "close": close},
            index=index,
        )

    def test_fixed_lots_units_and_pnl(self):
        broker = SimulatedBroker(
            sizing_mode=SIZING_FIXED_LOTS,
            lot_size=0.01,
            contract_size=100_000,
        )
        self.assertEqual(broker.size_fixed_lots(), 1000.0)
        self.assertEqual(broker.size_position(cash=10_000, entry=1.10), 1000.0)

        from apps.backtest.types import Position

        pos = Position(
            side="long",
            entry_price=1.1000,
            entry_time=pd.Timestamp("2024-01-01", tz="UTC"),
            stop_loss=None,
            take_profit=None,
            units=1000.0,
        )
        # +10 pips on EURUSD micro lot ≈ $1
        pnl = broker.position_pnl(pos, 1.1010)
        self.assertAlmostEqual(pnl, 1.0, places=6)

    def test_all_in_uses_full_cash(self):
        broker = SimulatedBroker(sizing_mode="all_in")
        self.assertAlmostEqual(broker.size_position(10_000, 100.0), 100.0)

    def test_runner_fixed_lots_records_meta_and_stable_size(self):
        bars = self._bars()
        strategy = MACrossoverStrategy({"fast_period": 3, "slow_period": 8})
        result = BacktestRunner().run(
            strategy,
            bars,
            initial_balance=10_000,
            warmup=15,
            sizing_mode=SIZING_FIXED_LOTS,
            lot_size=0.01,
            contract_size=100_000,
        )
        self.assertEqual(result.metrics["sizing_mode"], SIZING_FIXED_LOTS)
        self.assertEqual(result.metrics["lot_size"], 0.01)
        self.assertEqual(result.metrics["contract_size"], 100_000.0)
        # With fixed lots, units stay constant even as equity changes.
        if result.trades:
            # Reconstruct expected unit size from pnl / price move when move != 0.
            for t in result.trades:
                move = (
                    (t.exit_price - t.entry_price)
                    if t.side == "long"
                    else (t.entry_price - t.exit_price)
                )
                if abs(move) < 1e-12:
                    continue
                units = t.pnl / move  # commission=0
                self.assertAlmostEqual(units, 1000.0, places=4)
                break


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


class SweepHelperTests(SimpleTestCase):
    def test_parse_param_values(self):
        from apps.backtest.sweep import MAX_SWEEP_JOBS, build_override_dicts, parse_param_values

        self.assertEqual(parse_param_values("5, 10, 15"), [5, 10, 15])
        self.assertEqual(parse_param_values("0.01,0.02"), [0.01, 0.02])
        overrides = build_override_dicts("fast_period", [5, 10])
        self.assertEqual(overrides, [{"fast_period": 5}, {"fast_period": 10}])
        with self.assertRaises(ValueError):
            parse_param_values(",".join(str(i) for i in range(MAX_SWEEP_JOBS + 1)))

    def test_run_jobs_multiprocess_sequential(self):
        from apps.backtest.parallel import run_jobs_multiprocess

        results = run_jobs_multiprocess(
            [{"n": 1}, {"n": 2}, {"n": 3}],
            "apps.backtest.tests.test_runner:_sweep_job_double",
            max_workers=1,
        )
        self.assertEqual(results, [2, 4, 6])


def _sweep_job_double(job: dict) -> int:
    return int(job["n"]) * 2


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
