"""Tests for optional library strategy SL/TP percentage parameters."""

from __future__ import annotations

import pandas as pd
from django.test import SimpleTestCase

from apps.strategies.context import BarContext
from apps.strategies.engine import SignalEngine
from apps.strategies.indicators.registry import IndicatorRegistry
from apps.strategies.library.exits import levels_from_pct
from apps.strategies.library.ma_crossover import MACrossoverStrategy
from apps.strategies.library.range_breakout import RangeBreakoutStrategy
from apps.strategies.library.rsi_reversal import RSIReversalStrategy
from apps.strategies.signals import SignalAction


def _bars(closes: list[float], *, high_pad: float = 0.0, low_pad: float = 0.0) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(closes), freq="min", tz="UTC")
    close = pd.Series(closes, dtype=float, index=index)
    return pd.DataFrame(
        {
            "open": close,
            "high": close + high_pad,
            "low": close - low_pad,
            "close": close,
        },
        index=index,
    )


def _ctx(bars: pd.DataFrame, parameters: dict) -> BarContext:
    return BarContext(
        bar_index=len(bars) - 1,
        timestamp=bars.index[-1],
        bars=bars,
        parameters=parameters,
        indicators=IndicatorRegistry(bars),
    )


class LevelsFromPctTests(SimpleTestCase):
    def test_long_and_short_levels(self):
        sl, tp = levels_from_pct(100.0, is_long=True, stop_loss_pct=1.0, take_profit_pct=2.0)
        self.assertAlmostEqual(sl, 99.0)
        self.assertAlmostEqual(tp, 102.0)
        sl, tp = levels_from_pct(100.0, is_long=False, stop_loss_pct=1.0, take_profit_pct=2.0)
        self.assertAlmostEqual(sl, 101.0)
        self.assertAlmostEqual(tp, 98.0)

    def test_zero_pct_omits_levels(self):
        sl, tp = levels_from_pct(100.0, is_long=True, stop_loss_pct=0.0, take_profit_pct=0.0)
        self.assertIsNone(sl)
        self.assertIsNone(tp)


class LibraryStrategySlTpTests(SimpleTestCase):
    def test_ma_crossover_emits_sl_tp_on_long(self):
        # Slow SMA lags; rising closes produce a fast-above-slow cross near the end.
        closes = [100.0] * 12 + [100 + i for i in range(1, 9)]
        bars = _bars(closes)
        strategy = MACrossoverStrategy(
            {"fast_period": 3, "slow_period": 8, "stop_loss_pct": 1.0, "take_profit_pct": 2.0}
        )
        events = SignalEngine().run(strategy, bars, warmup=10)
        longs = [e for e in events if e.signal.action == SignalAction.ENTER_LONG]
        self.assertTrue(longs)
        sig = longs[0].signal
        entry = float(bars["close"].iloc[longs[0].bar_index])
        self.assertAlmostEqual(sig.stop_loss, entry * 0.99)
        self.assertAlmostEqual(sig.take_profit, entry * 1.02)

    def test_ma_crossover_default_omits_sl_tp(self):
        closes = [100.0] * 12 + [100 + i for i in range(1, 9)]
        bars = _bars(closes)
        strategy = MACrossoverStrategy({"fast_period": 3, "slow_period": 8})
        events = SignalEngine().run(strategy, bars, warmup=10)
        self.assertTrue(any(e.signal.action == SignalAction.ENTER_LONG for e in events))
        for e in events:
            self.assertIsNone(e.signal.stop_loss)
            self.assertIsNone(e.signal.take_profit)

    def test_rsi_reversal_emits_sl_tp_on_long(self):
        # Deep dip then bounce so RSI leaves oversold.
        closes = [50.0] * 20 + [40 - i for i in range(15)] + [26, 28, 32, 36]
        bars = _bars(closes)
        strategy = RSIReversalStrategy(
            {
                "rsi_period": 5,
                "oversold": 30,
                "overbought": 70,
                "stop_loss_pct": 1.5,
                "take_profit_pct": 3.0,
            }
        )
        events = SignalEngine().run(strategy, bars, warmup=10)
        longs = [e for e in events if e.signal.action == SignalAction.ENTER_LONG]
        self.assertTrue(longs)
        sig = longs[-1].signal
        entry = float(bars["close"].iloc[longs[-1].bar_index])
        self.assertAlmostEqual(sig.stop_loss, entry * (1 - 0.015))
        self.assertAlmostEqual(sig.take_profit, entry * (1 + 0.03))

    def test_range_breakout_emits_sl_tp_on_short(self):
        # Flat range then break strictly below prior range low.
        closes = [100.0] * 10 + [98.5]
        highs = [101.0] * 10 + [99.0]
        lows = [99.0] * 10 + [98.0]
        index = pd.date_range("2024-01-01", periods=11, freq="min", tz="UTC")
        bars = pd.DataFrame(
            {"open": closes, "high": highs, "low": lows, "close": closes},
            index=index,
        )
        strategy = RangeBreakoutStrategy(
            {"lookback": 10, "buffer_pct": 0.0, "stop_loss_pct": 1.0, "take_profit_pct": 2.0}
        )
        ctx = _ctx(bars, strategy.parameters)
        signal = strategy.on_bar(ctx)
        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal.action, SignalAction.ENTER_SHORT)
        self.assertAlmostEqual(signal.stop_loss, 98.5 * 1.01)
        self.assertAlmostEqual(signal.take_profit, 98.5 * 0.98)

    def test_warmup_ignores_float_schema_max(self):
        strategy = MACrossoverStrategy()
        # fast max 200, slow max 400 → warmup 405; float SL/TP max must not inflate further.
        self.assertEqual(SignalEngine._warmup_bars(strategy), 405)
