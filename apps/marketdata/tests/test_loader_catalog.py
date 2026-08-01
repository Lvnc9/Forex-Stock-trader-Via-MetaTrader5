"""Loader / catalog unit tests (no bulk CSV reads into assertions)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from django.test import SimpleTestCase

from apps.marketdata.catalog import _collect_csv_files, _parse_ts_ms, file_covers_range


class CatalogCollectTests(SimpleTestCase):
    def test_prefers_months_over_yearly(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            months = root / "months"
            months.mkdir()
            (months / "x-m1-2024-01.csv").write_text(
                "timestamp,open,high,low,close\n1704067200000,1,1,1,1\n"
            )
            (root / "2024.csv").write_text(
                "timestamp,open,high,low,close\n1704067200000,1,1,1,1\n"
            )
            files = _collect_csv_files(root)
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].kind, "monthly")

    def test_parse_iso_and_ms(self):
        self.assertIsNotNone(_parse_ts_ms("1704067200000"))
        self.assertIsNotNone(_parse_ts_ms("2024-01-01T00:00:00+00:00"))

    def test_file_covers_range(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.csv"
            path.write_text(
                "timestamp,open,high,low,close\n"
                "1704067200000,1,1,1,1\n"
                "1704153600000,1,1,1,1\n"
            )
            start = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end = datetime(2024, 1, 2, tzinfo=timezone.utc)
            self.assertTrue(file_covers_range(path, start, end))
            far = datetime(2030, 1, 1, tzinfo=timezone.utc)
            self.assertFalse(file_covers_range(path, far, far))


class ParquetCacheTests(SimpleTestCase):
    def test_roundtrip_and_legacy_pkl_migration(self):
        import tempfile

        import pandas as pd

        from apps.marketdata.loader import (
            CACHE_EXT,
            _load_frame_cache,
            _save_frame_cache,
        )

        index = pd.date_range("2024-01-01", periods=3, freq="1min", tz="UTC")
        frame = pd.DataFrame(
            {
                "open": [1.0, 2.0, 3.0],
                "high": [1.1, 2.1, 3.1],
                "low": [0.9, 1.9, 2.9],
                "close": [1.05, 2.05, 3.05],
            },
            index=index,
        )
        with tempfile.TemporaryDirectory() as tmp:
            parquet_path = Path(tmp) / f"m1-deadbeef{CACHE_EXT}"
            _save_frame_cache(parquet_path, frame)
            self.assertTrue(parquet_path.is_file())
            loaded = _load_frame_cache(parquet_path)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(len(loaded), 3)
            self.assertAlmostEqual(float(loaded["close"].iloc[-1]), 3.05)

            # Legacy .pkl with same stem is migrated then removed.
            legacy = parquet_path.with_suffix(".pkl")
            parquet_path.unlink()
            frame.to_pickle(legacy)
            migrated = _load_frame_cache(parquet_path)
            self.assertIsNotNone(migrated)
            self.assertTrue(parquet_path.is_file())
            self.assertFalse(legacy.exists())
