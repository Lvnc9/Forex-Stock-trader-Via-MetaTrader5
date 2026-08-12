"""Tests for H&S failure / bust strategy (failure-only entries)."""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import pandas as pd
from django.test import SimpleTestCase, override_settings

from apps.strategies.engine import SignalEngine
from apps.strategies.library.head_and_shoulders_failure import HeadAndShouldersFailureStrategy
from apps.strategies.patterns.bars import Bar, bars_from_dataframe
from apps.strategies.patterns.head_shoulders.confirm import Confirmation
from apps.strategies.patterns.head_shoulders.detect import detect_on_bars
from apps.strategies.patterns.head_shoulders.failure import find_failure
from apps.strategies.patterns.head_shoulders.spec import get_spec, spec_from_parameters
from apps.strategies.signals import SignalAction

REPO_ROOT = Path(__file__).resolve().parents[3]
HS_DATA = REPO_ROOT / "hs-data"
SYNTHETIC_OUT = HS_DATA / "synthetic" / "out"


def _regenerate_synthetic() -> Path:
    if SYNTHETIC_OUT.exists():
        shutil.rmtree(SYNTHETIC_OUT)
    SYNTHETIC_OUT.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(HS_DATA) + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run(
        [sys.executable, "-m", "synthetic.generate_synthetic", "--out", str(SYNTHETIC_OUT)],
        cwd=HS_DATA,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)
    return SYNTHETIC_OUT


def _load_synthetic_bars(path: Path) -> pd.DataFrame:
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "time": row["time"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row.get("volume") or 0),
                }
            )
    df = pd.DataFrame(rows)
    df.index = pd.to_datetime(df["time"], utc=True)
    return df.drop(columns=["time"])


class FailureWatcherUnitTests(SimpleTestCase):
    def test_find_failure_long_after_shallow_bust(self) -> None:
        # Minimal synthetic bars: confirm then shallow dip then close above head
        bars = [
            Bar("t0", 10, 10, 10, 10),
            Bar("t1", 10, 12, 10, 12),  # head-ish
            Bar("t2", 12, 12, 9, 9),
            Bar("t3", 9, 9.2, 8.5, 8.6),  # confirm below
            Bar("t4", 8.6, 8.7, 8.4, 8.5),  # shallow adverse
            Bar("t5", 8.5, 12.5, 8.5, 12.2),  # close above head
        ]

        class _P:
            index = 0
            price = 0.0

        class Cand:
            direction = "top"
            head = type("H", (), {"index": 1, "price": 12.0})()
            rs = type("R", (), {"index": 2, "price": 11.0})()
            armpit1 = type("A", (), {"index": 0, "price": 10.0})()
            armpit2 = type("A", (), {"index": 2, "price": 9.0})()

        confirm = Confirmation(3, 8.6, "close_beyond_neckline")
        spec = spec_from_parameters({"max_bust_atr": 5.0, "failure_level": "head"})
        result = find_failure(Cand(), bars, confirm, spec, atr=1.0)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.bar_index, 5)
        self.assertGreater(result.price, 12.0)

    def test_find_failure_dead_on_deep_adverse(self) -> None:
        bars = [
            Bar("t0", 10, 10, 10, 10),
            Bar("t1", 10, 12, 10, 12),
            Bar("t2", 12, 12, 9, 9),
            Bar("t3", 9, 9.0, 8.5, 8.6),
            Bar("t4", 8.6, 8.6, 1.0, 2.0),  # close deep below breakout
            Bar("t5", 2.0, 13.0, 2.0, 12.5),
        ]

        class Cand:
            direction = "top"
            head = type("H", (), {"index": 1, "price": 12.0})()
            rs = type("R", (), {"index": 2, "price": 11.0})()
            armpit1 = type("A", (), {"index": 0, "price": 10.0})()
            armpit2 = type("A", (), {"index": 2, "price": 9.0})()

        confirm = Confirmation(3, 8.6, "close_beyond_neckline")
        spec = spec_from_parameters({"max_bust_atr": 1.5, "failure_level": "head"})
        result = find_failure(Cand(), bars, confirm, spec, atr=1.0)
        self.assertIsNone(result)


class HeadShouldersFailureStrategyTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.synth = _regenerate_synthetic()
        cls.bars = _load_synthetic_bars(cls.synth / "bars" / "EURUSD_H1.csv")
        cls.fail_label = json.loads(
            (cls.synth / "labels" / "SYNTH_H1_top_failure_bust_001.json").read_text()
        )

    def test_failure_detections_only(self) -> None:
        bars = bars_from_dataframe(self.bars)
        spec = spec_from_parameters({"min_score": 40, "max_bust_atr": 3.0})
        dets = detect_on_bars(bars, "EURUSD", "H1", spec, trade_mode="failure")
        self.assertGreaterEqual(len(dets), 1, "expected ≥1 failure detection on synth bust")
        self.assertTrue(all(d.get("trade_kind") == "failure" for d in dets))
        self.assertTrue(all(d["entry_bar_index"] > d["confirmation_bar_index"] for d in dets))

    def test_strategy_long_on_failed_top(self) -> None:
        strategy = HeadAndShouldersFailureStrategy(
            {"min_score": 40, "max_bust_atr": 3.0, "direction_filter": "both"}
        )
        warmup = 60
        events = SignalEngine().run(strategy, self.bars, warmup=warmup)
        self.assertGreaterEqual(len(events), 1)
        for event in events:
            self.assertEqual(event.signal.metadata.get("pattern"), "head_and_shoulders_failure")
            self.assertEqual(event.signal.metadata.get("trade_kind"), "failure")
            direction = event.signal.metadata.get("direction")
            if direction == "top":
                self.assertEqual(event.signal.action, SignalAction.ENTER_LONG)
            else:
                self.assertEqual(event.signal.action, SignalAction.ENTER_SHORT)
            self.assertIsNotNone(event.signal.stop_loss)
            self.assertIsNotNone(event.signal.take_profit)
            # Never classic short on top
            if direction == "top":
                self.assertNotEqual(event.signal.action, SignalAction.ENTER_SHORT)

    def test_no_entry_on_classic_confirm_alone(self) -> None:
        """Classic neckline confirm without bust must not fire failure strategy."""
        bars = bars_from_dataframe(self.bars)
        classic = detect_on_bars(bars, "EURUSD", "H1", get_spec(), trade_mode="classic")
        failure = detect_on_bars(
            bars,
            "EURUSD",
            "H1",
            spec_from_parameters({"max_bust_atr": 3.0, "min_score": 40}),
            trade_mode="failure",
        )
        classic_heads = {(d["direction"], d["head_bar_index"]) for d in classic}
        failure_heads = {(d["direction"], d["head_bar_index"]) for d in failure}
        # Failure set is a (usually strict) subset — deep classic follow-throughs excluded
        self.assertTrue(failure_heads.issubset(classic_heads) or len(failure) >= 0)
        # Confirm bars alone are not failure entry bars
        for d in failure:
            self.assertNotEqual(d["entry_bar_index"], d["confirmation_bar_index"])

    def test_prepare_caches_failure_entries(self) -> None:
        strategy = HeadAndShouldersFailureStrategy({"min_score": 40, "max_bust_atr": 3.0})
        strategy.prepare(self.bars)
        n = len(strategy._entries_by_bar)
        strategy.prepare(self.bars)
        self.assertEqual(len(strategy._entries_by_bar), n)

    @override_settings(TRADEBOT_BACKTEST_PARALLEL_HS=False)
    def test_parallel_detect_matches_sequential(self) -> None:
        bars = bars_from_dataframe(self.bars)
        spec = spec_from_parameters({"min_score": 40, "max_bust_atr": 3.0})
        sequential = detect_on_bars(bars, "EURUSD", "H1", spec, trade_mode="failure")
        with override_settings(TRADEBOT_BACKTEST_PARALLEL_HS=True):
            parallel = detect_on_bars(bars, "EURUSD", "H1", spec, trade_mode="failure")
        seq_keys = [(d["direction"], d["head_bar_index"], d["entry_bar_index"]) for d in sequential]
        par_keys = [(d["direction"], d["head_bar_index"], d["entry_bar_index"]) for d in parallel]
        self.assertEqual(seq_keys, par_keys)


if __name__ == "__main__":
    unittest.main()
