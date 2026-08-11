"""Tests for HistData import helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from apps.marketdata.catalog import scan_data_root
from apps.marketdata.histdata_import import (
    discover_histdata_csvs,
    import_histdata_to_slug,
    is_histdata_staging_dir,
    read_histdata_m1,
)


class HistDataImportTests(SimpleTestCase):
    def test_staging_dir_detection(self):
        self.assertTrue(is_histdata_staging_dir("HISTDATA_COM_ASCII_XAUUSD_M12025"))
        self.assertFalse(is_histdata_staging_dir("xauusd"))

    def test_read_and_import_small_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging = root / "HISTDATA_COM_ASCII_XAUUSD_M12099"
            staging.mkdir()
            sample = staging / "DAT_ASCII_XAUUSD_M1_2099.csv"
            sample.write_text(
                "20990101 120000;1.0;1.1;0.9;1.05;0\n"
                "20990101 120100;1.05;1.15;1.0;1.1;0\n"
                "20990201 120000;1.1;1.2;1.0;1.15;0\n",
                encoding="utf-8",
            )
            found = discover_histdata_csvs(root, "XAUUSD")
            self.assertEqual(len(found), 1)

            frame = read_histdata_m1(sample)
            self.assertEqual(len(frame), 3)

            result = import_histdata_to_slug(root, slug="xauusd", symbol="XAUUSD")
            self.assertEqual(result.slug, "xauusd")
            self.assertEqual(result.bar_count, 3)
            self.assertEqual(len(result.month_files), 2)

            catalogs = scan_data_root(root)
            slugs = [c.slug for c in catalogs]
            self.assertIn("xauusd", slugs)
            self.assertNotIn("HISTDATA_COM_ASCII_XAUUSD_M12099", slugs)

            shard = root / "xauusd" / "months" / "xauusd-m1-2099-01.csv"
            self.assertTrue(shard.is_file())
            text = shard.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("timestamp,open,high,low,close"))
