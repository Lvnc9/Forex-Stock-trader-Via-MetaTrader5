"""Tests for Head & shoulders library strategy and promoted pattern core."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from django.test import SimpleTestCase

from apps.strategies.engine import SignalEngine
from apps.strategies.library.head_and_shoulders import HeadAndShouldersStrategy
from apps.strategies.patterns.bars import bars_from_dataframe
from apps.strategies.patterns.head_shoulders.detect import detect_on_bars
from apps.strategies.patterns.head_shoulders.spec import get_spec
from apps.strategies.signals import SignalAction

REPO_ROOT = Path(__file__).resolve().parents[3]
HS_DATA = REPO_ROOT / "hs-data"
SYNTHETIC_OUT = HS_DATA / "synthetic" / "out"


def _ensure_synthetic_fixtures() -> Path:
    if (SYNTHETIC_OUT / "bars" / "EURUSD_H1.csv").exists():
        return SYNTHETIC_OUT
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


def _load_labels(labels_dir: Path) -> list[dict]:
    out: list[dict] = []
    for path in sorted(labels_dir.glob("*.json")):
        out.append(json.loads(path.read_text(encoding="utf-8")))
    return out


class HeadShouldersPatternTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.synth = _ensure_synthetic_fixtures()
        cls.bars_path = cls.synth / "bars" / "EURUSD_H1.csv"
        cls.labels = _load_labels(cls.synth / "labels")

    def test_detect_on_synthetic_true_labels(self) -> None:
        bars = bars_from_dataframe(_load_synthetic_bars(self.bars_path))
        detections = detect_on_bars(bars, "EURUSD", "H1", get_spec(), entry_mode="A")
        self.assertGreaterEqual(len(detections), 2)
        directions = {d["direction"] for d in detections}
        self.assertIn("top", directions)
        self.assertIn("inverse", directions)
        for det in detections:
            self.assertIn("head_bar_index", det)
            self.assertIn("entry_bar_index", det)
            self.assertGreaterEqual(float(det["score"]), get_spec().min_score_threshold)

    def test_harness_parity_with_hs_data_detector(self) -> None:
        bars = bars_from_dataframe(_load_synthetic_bars(self.bars_path))
        promoted = detect_on_bars(bars, "EURUSD", "H1", get_spec(), entry_mode="A")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(HS_DATA) + os.pathsep + env.get("PYTHONPATH", "")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            out_path = Path(tmp.name)
        try:
            r = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "detector.run",
                    "--bars",
                    str(self.bars_path),
                    "--symbol",
                    "EURUSD",
                    "--timeframe",
                    "H1",
                    "--out",
                    str(out_path),
                ],
                cwd=HS_DATA,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r.returncode, 0, r.stderr or r.stdout)
            cli = json.loads(out_path.read_text(encoding="utf-8"))
        finally:
            out_path.unlink(missing_ok=True)

        promoted_keys = {
            (d["direction"], d["head_bar_index"], d["entry_bar_index"]) for d in promoted
        }
        cli_keys = {(d["direction"], d["head_bar_index"], d["entry_bar_index"]) for d in cli}
        self.assertEqual(promoted_keys, cli_keys)


class HeadShouldersStrategyTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.synth = _ensure_synthetic_fixtures()
        cls.bars = _load_synthetic_bars(cls.synth / "bars" / "EURUSD_H1.csv")
        cls.labels = _load_labels(cls.synth / "labels")

    def test_emits_entry_signals_on_confirmation_bars(self) -> None:
        strategy = HeadAndShouldersStrategy({"min_score": 50, "direction_filter": "both"})
        warmup = int(strategy.parameters["prior_trend_bars"]) + int(strategy.parameters["swing_L_medium"]) + 5
        events = SignalEngine().run(strategy, self.bars, warmup=warmup)

        entry_bars = {e.bar_index for e in events}
        bars = bars_from_dataframe(self.bars)
        detections = detect_on_bars(bars, "EURUSD", "H1", get_spec(), entry_mode="A")
        expected_entries = {d["entry_bar_index"] for d in detections if float(d["score"]) >= 50}
        self.assertEqual(entry_bars, expected_entries)

        for event in events:
            self.assertIn(
                event.signal.action,
                (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT),
            )
            self.assertIsNotNone(event.signal.stop_loss)
            self.assertIsNotNone(event.signal.take_profit)
            self.assertEqual(event.signal.metadata.get("pattern"), "head_and_shoulders")

    def test_no_duplicate_entries_for_same_head(self) -> None:
        strategy = HeadAndShouldersStrategy({"min_score": 50})
        warmup = 60
        events = SignalEngine().run(strategy, self.bars, warmup=warmup)
        heads = [e.signal.metadata["head_bar_index"] for e in events if e.signal.metadata]
        self.assertEqual(len(heads), len(set(heads)))

    def test_direction_filter_top_only(self) -> None:
        strategy = HeadAndShouldersStrategy({"min_score": 50, "direction_filter": "top"})
        warmup = 60
        events = SignalEngine().run(strategy, self.bars, warmup=warmup)
        for event in events:
            self.assertEqual(event.signal.action, SignalAction.ENTER_SHORT)
            self.assertEqual(event.signal.metadata.get("direction"), "top")

    def test_prepare_detects_once_then_on_bar_is_lookup(self) -> None:
        strategy = HeadAndShouldersStrategy({"min_score": 50})
        strategy.prepare(self.bars)
        self.assertGreater(len(strategy._entries_by_bar), 0)
        # Second prepare replaces the cache (idempotent, not additive).
        n = len(strategy._entries_by_bar)
        strategy.prepare(self.bars)
        self.assertEqual(len(strategy._entries_by_bar), n)

    def test_engine_run_finishes_quickly_on_synthetic(self) -> None:
        import time

        strategy = HeadAndShouldersStrategy({"min_score": 50})
        t0 = time.perf_counter()
        events = SignalEngine().run(strategy, self.bars, warmup=60)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 5.0, f"H&S SignalEngine took {elapsed:.2f}s — prepare/on_bar regression?")
        self.assertGreaterEqual(len(events), 1)


if __name__ == "__main__":
    unittest.main()
