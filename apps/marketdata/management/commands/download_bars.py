"""
Download M1 OHLC bars via dukascopy-node into data/<slug>/.

Requires Node.js + npx. Example:

  python manage.py download_bars --instrument eurusd --slug eurusd --from 2024-01-01 --to 2024-01-31
  python manage.py download_bars --fx-majors --from 2024-01-01 --to 2024-01-07 --dry-run
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# Dukascopy instrument id → local catalog slug (FX majors first).
FX_MAJORS: dict[str, str] = {
    "eurusd": "eurusd",
    "gbpusd": "gbpusd",
    "usdjpy": "usdjpy",
    "usdchf": "usdchf",
    "audusd": "audusd",
    "usdcad": "usdcad",
    "nzdusd": "nzdusd",
}


class Command(BaseCommand):
    help = "Download M1 bars with dukascopy-node into TRADEBOT_DATA_ROOT."

    def add_arguments(self, parser):
        parser.add_argument("--instrument", help="Dukascopy instrument id (e.g. eurusd)")
        parser.add_argument("--slug", help="Local catalog folder name (default: instrument)")
        parser.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD")
        parser.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD")
        parser.add_argument(
            "--fx-majors",
            action="store_true",
            help="Download all FX majors in FX_MAJORS (ignores --instrument).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print commands without running dukascopy-node.",
        )
        parser.add_argument(
            "--timeframe",
            default="m1",
            help="Dukascopy timeframe (default m1).",
        )

    def handle(self, *args, **options):
        date_from = self._parse_date(options["date_from"])
        date_to = self._parse_date(options["date_to"])
        if date_to < date_from:
            raise CommandError("--to must be on or after --from")

        data_root = Path(settings.TRADEBOT_DATA_ROOT)
        data_root.mkdir(parents=True, exist_ok=True)

        jobs: list[tuple[str, str]] = []
        if options["fx_majors"]:
            jobs = list(FX_MAJORS.items())
        else:
            instrument = (options.get("instrument") or "").strip().lower()
            if not instrument:
                raise CommandError("Provide --instrument or --fx-majors")
            slug = (options.get("slug") or instrument).strip().lower()
            jobs = [(instrument, slug)]

        npx = shutil.which("npx")
        if not options["dry_run"] and not npx:
            raise CommandError("npx not found. Install Node.js to use dukascopy-node.")

        for instrument, slug in jobs:
            self._download_one(
                npx=npx,
                data_root=data_root,
                instrument=instrument,
                slug=slug,
                date_from=date_from,
                date_to=date_to,
                timeframe=options["timeframe"],
                dry_run=options["dry_run"],
            )

        self.stdout.write(self.style.SUCCESS(f"Done ({len(jobs)} instrument(s))."))

    def _download_one(
        self,
        *,
        npx: str | None,
        data_root: Path,
        instrument: str,
        slug: str,
        date_from: date,
        date_to: date,
        timeframe: str,
        dry_run: bool,
    ) -> None:
        out_dir = data_root / slug / "months"
        out_dir.mkdir(parents=True, exist_ok=True)
        # dukascopy-node writes files; use folder as volume destination
        cmd = [
            npx or "npx",
            "--yes",
            "dukascopy-node",
            "-i",
            instrument,
            "-from",
            date_from.isoformat(),
            "-to",
            date_to.isoformat(),
            "-t",
            timeframe,
            "-f",
            "csv",
            "-v",
            str(out_dir),
            "-date-format",
            "YYYY-MM-DD HH:mm:ss",
        ]
        self.stdout.write(" ".join(cmd))
        if dry_run:
            return
        assert npx is not None
        result = subprocess.run(cmd, cwd=str(data_root), capture_output=True, text=True)
        if result.returncode != 0:
            raise CommandError(
                f"dukascopy-node failed for {instrument}:\n{result.stderr or result.stdout}"
            )
        meta = {
            "instrument": instrument,
            "slug": slug,
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
            "timeframe": timeframe,
        }
        (data_root / slug / "download_meta.json").write_text(json.dumps(meta, indent=2))
        self.stdout.write(self.style.SUCCESS(f"  → {slug}/months"))

    @staticmethod
    def _parse_date(value: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise CommandError(f"Invalid date {value!r}; use YYYY-MM-DD") from exc
