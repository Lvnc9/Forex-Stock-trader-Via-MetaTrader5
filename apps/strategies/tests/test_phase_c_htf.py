"""Phase C: HTF bars wiring + SignalEngine / BacktestRunner unification."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from django.test import SimpleTestCase, TestCase

from apps.backtest.forms import BacktestRunForm
from apps.backtest.runner import BacktestRunner
from apps.marketdata.loader import prepare_primary_and_htf
from apps.marketdata.timeframes import is_higher_timeframe, normalize_timeframe
from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext
from apps.strategies.engine import SignalEngine
from apps.strategies.library.ma_crossover import MACrossoverStrategy
from apps.strategies.signals import Signal, SignalAction
from apps.trading.forms import DeploymentDraftForm


def _ohlc_bars(periods: int = 120, freq: str = "5min") -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=periods, freq=freq, tz="UTC")
    close = pd.Series(
        [100 + 5 * math.sin(i / 6.0) for i in range(periods)],
        dtype=float,
        index=index,
    )
    return pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close},
        index=index,
    )


class HtfUsesStrategy(BaseStrategy):
    """Emits long only when HTF close is above its SMA."""

    slug = "htf_uses"
    name = "HTF uses"
    description = "test"
    module_path = "tests.htf_uses"
    default_parameters = {"htf_sma": 3}
    parameter_schema = [
        {"name": "htf_sma", "type": "int", "min": 2, "max": 50, "default": 3},
    ]

    def on_bar(self, ctx: BarContext) -> Signal | None:
        ind = ctx.htf_indicators
        if ind is None:
            return None
        period = int(self.parameters["htf_sma"])
        sma = ind.sma(period)
        if len(sma.dropna()) < 1:
            return None
        if ctx.htf_bars is None or ctx.htf_bars.empty:
            return None
        if float(ctx.htf_bars["close"].iloc[-1]) > float(sma.iloc[-1]):
            return Signal(SignalAction.ENTER_LONG)
        return Signal(SignalAction.ENTER_SHORT)


class TimeframeHelperTests(SimpleTestCase):
    def test_is_higher_timeframe(self):
        self.assertTrue(is_higher_timeframe("H1", "M5"))
        self.assertFalse(is_higher_timeframe("M5", "H1"))
        self.assertFalse(is_higher_timeframe("M5", "M5"))
        self.assertEqual(normalize_timeframe(" m15 "), "M15")


class PreparePrimaryAndHtfTests(SimpleTestCase):
    def test_prepare_without_htf(self):
        m1 = _ohlc_bars(60, freq="min")
        primary, htf = prepare_primary_and_htf(m1, "M5", None)
        self.assertFalse(primary.empty)
        self.assertIsNone(htf)

    def test_prepare_with_htf(self):
        m1 = _ohlc_bars(180, freq="min")
        primary, htf = prepare_primary_and_htf(m1, "M5", "H1")
        self.assertGreater(len(primary), len(htf))
        self.assertFalse(htf.empty)

    def test_rejects_non_higher_htf(self):
        m1 = _ohlc_bars(60, freq="min")
        with self.assertRaises(ValueError):
            prepare_primary_and_htf(m1, "H1", "M5")


class SignalEngineHtfTests(SimpleTestCase):
    def test_htf_window_passed_to_strategy(self):
        primary = _ohlc_bars(80, freq="5min")
        htf = primary.resample("1h").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}
        ).dropna()
        strategy = HtfUsesStrategy()
        events = SignalEngine().run(strategy, primary, htf_bars=htf, warmup=10)
        self.assertTrue(any(e.signal.action == SignalAction.ENTER_LONG for e in events))

    def test_on_latest_bar_matches_run_last_event(self):
        bars = _ohlc_bars(100)
        strategy = MACrossoverStrategy({"fast_period": 3, "slow_period": 8})
        engine = SignalEngine()
        events = engine.run(strategy, bars, warmup=12)
        latest = engine.on_latest_bar(strategy, bars, warmup=12)
        if events and events[-1].bar_index == len(bars) - 1:
            self.assertIsNotNone(latest)
            self.assertEqual(latest.action, events[-1].signal.action)
        else:
            self.assertIsNone(latest)


class BacktestRunnerUnificationTests(SimpleTestCase):
    def test_runner_uses_signal_engine_events(self):
        bars = _ohlc_bars(150)
        strategy = MACrossoverStrategy({"fast_period": 3, "slow_period": 8})
        result = BacktestRunner().run(strategy, bars, initial_balance=10_000, warmup=15)
        self.assertIn("win_rate_pct", result.metrics)
        self.assertEqual(len(result.equity_curve), len(bars))

    def test_runner_with_htf_strategy(self):
        primary = _ohlc_bars(200, freq="5min")
        htf = primary.resample("1h").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}
        ).dropna()
        strategy = HtfUsesStrategy()
        result = BacktestRunner().run(
            strategy, primary, htf_bars=htf, initial_balance=10_000, warmup=20
        )
        self.assertGreaterEqual(result.metrics["trade_count"], 1)


class BacktestFormHtfTests(TestCase):
    def test_rejects_htf_not_higher(self):
        form = BacktestRunForm(
            data={
                "strategy": "",
                "catalog_slug": "demo",
                "timeframe": "H1",
                "htf_timeframe": "M5",
                "start": "2024-01-01",
                "end": "2024-01-10",
                "initial_balance": "10000",
                "spread_pct": "0",
                "commission": "0",
            },
            data_root=None,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("htf_timeframe", form.errors)


class DeploymentFormHtfTests(TestCase):
    def test_accepts_blank_htf(self):
        form = DeploymentDraftForm(data_root=None)
        self.assertIn("htf_timeframe", form.fields)
        self.assertFalse(form.fields["htf_timeframe"].required)


@dataclass
class _FakeAdapter:
    connected: bool = True
    primary: pd.DataFrame = field(default_factory=pd.DataFrame)
    htf: pd.DataFrame = field(default_factory=pd.DataFrame)
    calls: list[tuple[str, str]] = field(default_factory=list)
    executed: list[dict[str, Any]] = field(default_factory=list)

    def copy_rates_df(self, symbol: str, timeframe: str, count: int = 400):
        self.calls.append((symbol, timeframe))
        if timeframe.upper() in {"H1", "H4", "D1"}:
            return self.htf.copy()
        return self.primary.copy()

    def open_side_for(self, symbol: str):
        return None

    def execute_signal(self, symbol, action, lot, **kwargs):
        payload = {"symbol": symbol, "action": action, "lot": lot, **kwargs}
        self.executed.append(payload)
        return payload


class LiveWorkerHtfTests(SimpleTestCase):
    def test_fetches_htf_and_uses_signal_engine(self):
        from agent.live_worker import LiveWorker

        primary = _ohlc_bars(80, freq="5min")
        htf = primary.resample("1h").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}
        ).dropna()
        adapter = _FakeAdapter(primary=primary, htf=htf)
        worker = LiveWorker(adapter=adapter)
        reports = worker.process_deployments(
            [
                {
                    "id": 1,
                    "mt5_symbol": "EURUSD",
                    "timeframe": "M5",
                    "htf_timeframe": "H1",
                    "lot_size": 0.01,
                    "module_path": "apps.strategies.library.ma_crossover",
                    "parameters": {"fast_period": 3, "slow_period": 8},
                }
            ]
        )
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["status"], "processed")
        self.assertIn(("EURUSD", "M5"), adapter.calls)
        self.assertIn(("EURUSD", "H1"), adapter.calls)
        self.assertEqual(reports[0].get("htf_timeframe"), "H1")
