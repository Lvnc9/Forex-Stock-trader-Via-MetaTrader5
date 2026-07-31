"""LiveWorker smoke: library strategy SL/TP reaches the MT5 adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pandas as pd
from django.test import SimpleTestCase

from apps.strategies.signals import Signal, SignalAction


def _ohlc_bars(n: int = 80, freq: str = "5min") -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC")
    close = pd.Series([100.0 + (i % 7) * 0.1 for i in range(n)], index=index)
    return pd.DataFrame(
        {"open": close, "high": close + 0.2, "low": close - 0.2, "close": close},
        index=index,
    )


@dataclass
class _FakeAdapter:
    connected: bool = True
    primary: pd.DataFrame = field(default_factory=pd.DataFrame)
    calls: list[tuple[str, str]] = field(default_factory=list)
    executed: list[dict[str, Any]] = field(default_factory=list)

    def copy_rates_df(self, symbol: str, timeframe: str, count: int = 400):
        self.calls.append((symbol, timeframe))
        return self.primary.copy()

    def open_side_for(self, symbol: str):
        return None

    def execute_signal(self, symbol, action, lot, **kwargs):
        payload = {"symbol": symbol, "action": action, "lot": lot, **kwargs}
        self.executed.append(payload)
        return payload


class LiveWorkerLibrarySlTpSmokeTests(SimpleTestCase):
    def test_passes_stop_loss_and_take_profit_to_adapter(self):
        from agent.live_worker import LiveWorker

        adapter = _FakeAdapter(primary=_ohlc_bars())
        worker = LiveWorker(adapter=adapter)
        signal = Signal(
            SignalAction.ENTER_LONG,
            stop_loss=99.0,
            take_profit=102.0,
        )
        with patch.object(worker.engine, "on_latest_bar", return_value=signal):
            reports = worker.process_deployments(
                [
                    {
                        "id": 7,
                        "mt5_symbol": "EURUSD",
                        "timeframe": "M5",
                        "htf_timeframe": "",
                        "lot_size": 0.02,
                        "module_path": "apps.strategies.library.ma_crossover",
                        "parameters": {
                            "fast_period": 3,
                            "slow_period": 8,
                            "stop_loss_pct": 1.0,
                            "take_profit_pct": 2.0,
                        },
                    }
                ]
            )

        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["status"], "processed")
        self.assertEqual(reports[0]["signal"], "enter_long")
        self.assertEqual(len(adapter.executed), 1)
        order = adapter.executed[0]
        self.assertEqual(order["action"], "enter_long")
        self.assertEqual(order["stop_loss"], 99.0)
        self.assertEqual(order["take_profit"], 102.0)

    def test_ma_crossover_latest_bar_emits_sl_tp_levels(self):
        """End-to-end: library params → on_latest_bar → absolute SL/TP."""
        from apps.strategies.engine import SignalEngine
        from apps.strategies.library.ma_crossover import MACrossoverStrategy

        # Rising series so the last bar is a fresh fast-above-slow cross.
        closes = [100.0] * 15 + [100 + i for i in range(1, 10)]
        bars = _ohlc_bars(len(closes))
        bars["close"] = closes
        bars["open"] = closes
        bars["high"] = [c + 0.2 for c in closes]
        bars["low"] = [c - 0.2 for c in closes]

        strategy = MACrossoverStrategy(
            {
                "fast_period": 3,
                "slow_period": 8,
                "stop_loss_pct": 1.0,
                "take_profit_pct": 2.0,
            }
        )
        engine = SignalEngine()
        # Find a bar that emits long, then confirm on_latest_bar at that prefix.
        events = engine.run(strategy, bars, warmup=10)
        longs = [e for e in events if e.signal.action == SignalAction.ENTER_LONG]
        self.assertTrue(longs)
        i = longs[0].bar_index
        prefix = bars.iloc[: i + 1]
        signal = engine.on_latest_bar(strategy, prefix, warmup=10)
        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal.action, SignalAction.ENTER_LONG)
        entry = float(prefix["close"].iloc[-1])
        self.assertAlmostEqual(signal.stop_loss, entry * 0.99)
        self.assertAlmostEqual(signal.take_profit, entry * 1.02)
