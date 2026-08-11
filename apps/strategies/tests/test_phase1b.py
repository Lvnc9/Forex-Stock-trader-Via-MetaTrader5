import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from django.test import SimpleTestCase, TestCase

from apps.marketdata.catalog import scan_data_root
from apps.marketdata.loader import load_m1_bars, resample_bars
from apps.strategies.engine import SignalEngine
from apps.strategies.library.ma_crossover import MACrossoverStrategy
from apps.strategies.loader import instantiate_strategy


class CatalogScanTests(SimpleTestCase):
    def test_scan_finds_instrument_and_counts_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slug_dir = root / "demo"
            months = slug_dir / "months"
            months.mkdir(parents=True)
            csv_path = months / "testidx-m1-2025-01.csv"
            csv_path.write_text(
                "timestamp,open,high,low,close\n"
                "1704067200000,1,2,0.5,1.5\n"
                "1704067260000,1.5,2.5,1,2\n",
                encoding="utf-8",
            )

            catalogs = scan_data_root(root)
            self.assertEqual(len(catalogs), 1)
            self.assertEqual(catalogs[0].slug, "demo")
            self.assertEqual(catalogs[0].bar_count, 2)
            self.assertEqual(catalogs[0].dukascopy_id, "testidx")


class LoaderTests(SimpleTestCase):
    def test_load_and_resample(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slug_dir = root / "x"
            months = slug_dir / "months"
            months.mkdir(parents=True)
            path = months / "x-m1-2025-01.csv"
            rows = []
            base_ms = 1704067200000
            for i in range(6):
                ts = base_ms + i * 60_000
                price = 1.0 + i * 0.01
                rows.append(f"{ts},{price},{price},{price},{price}")
            path.write_text("timestamp,open,high,low,close\n" + "\n".join(rows), encoding="utf-8")

            m1 = load_m1_bars("x", root)
            self.assertEqual(len(m1), 6)
            m5 = resample_bars(m1, "M5")
            self.assertGreaterEqual(len(m5), 1)


class SignalEngineTests(SimpleTestCase):
    def test_ma_crossover_runs_and_can_emit_signals(self):
        import math

        index = pd.date_range("2024-01-01", periods=120, freq="min", tz="UTC")
        close = pd.Series(
            [100 + 5 * math.sin(i / 6.0) for i in range(120)],
            dtype=float,
            index=index,
        )
        bars = pd.DataFrame(
            {"open": close, "high": close + 1, "low": close - 1, "close": close},
            index=index,
        )
        strategy = MACrossoverStrategy({"fast_period": 3, "slow_period": 10})
        events = SignalEngine().run(strategy, bars, warmup=12)
        self.assertIsInstance(events, list)


class StrategyLoaderTests(TestCase):
    def test_instantiate_library_module(self):
        strategy = instantiate_strategy(
            "apps.strategies.library.ma_crossover",
            {"fast_period": 5, "slow_period": 20},
        )
        self.assertEqual(strategy.parameters["fast_period"], 5)
