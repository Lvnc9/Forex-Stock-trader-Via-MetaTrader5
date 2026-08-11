"""Smoke tests for harness using synthetic fixtures."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # hs-data/


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return env


class HarnessSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmpdir.name) / "synth"
        r = subprocess.run(
            [sys.executable, "-m", "synthetic.generate_synthetic", "--out", str(cls.out)],
            cwd=ROOT,
            env=_env(),
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0:
            raise RuntimeError(r.stderr or r.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmpdir.cleanup()

    def _evaluate(self, detections: Path, report: Path) -> dict:
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "harness.evaluate",
                "--bars-dir",
                str(self.out / "bars"),
                "--labels",
                str(self.out / "labels"),
                "--detections",
                str(detections),
                "--out",
                str(report),
            ],
            cwd=ROOT,
            env=_env(),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr or r.stdout)
        return json.loads((report / "scorecard.json").read_text())

    def test_perfect_detections_high_f1(self) -> None:
        card = self._evaluate(
            self.out / "detections_perfect.json",
            Path(self.tmpdir.name) / "rep_perfect",
        )
        det = card["detection_metrics"]
        self.assertEqual(det["tp"], 3)
        self.assertEqual(det["fn"], 0)
        self.assertEqual(det["missed_label_ids"], [])
        self.assertAlmostEqual(det["recall"], 1.0)
        self.assertAlmostEqual(det["precision"], 1.0)
        self.assertAlmostEqual(det["entry_bar_match_rate"], 1.0)

    def test_miss_one_lists_missed_id(self) -> None:
        card = self._evaluate(
            self.out / "detections_miss_one.json",
            Path(self.tmpdir.name) / "rep_miss",
        )
        det = card["detection_metrics"]
        self.assertEqual(det["tp"], 1)
        self.assertEqual(det["fn"], 2)
        self.assertIn("SYNTH_H1_top_geom_001", det["missed_label_ids"])
        self.assertIn("SYNTH_H1_top_down_neck_001", det["missed_label_ids"])
        self.assertLess(det["recall"], 1.0)


if __name__ == "__main__":
    unittest.main()
