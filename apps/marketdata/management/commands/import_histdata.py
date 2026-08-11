"""Merge HistData.com staging folders into a standard catalog slug (e.g. xauusd)."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.marketdata.histdata_import import discover_histdata_csvs, import_histdata_to_slug


class Command(BaseCommand):
    help = (
        "Import HistData DAT_ASCII M1 CSVs from data/HISTDATA_* folders into "
        "data/<slug>/months/ (TradeBot catalog layout)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            required=True,
            help="Catalog folder name (e.g. xauusd)",
        )
        parser.add_argument(
            "--symbol",
            help="HistData symbol in filenames (default: slug uppercased, e.g. XAUUSD)",
        )
        parser.add_argument(
            "--source",
            action="append",
            default=[],
            help="Explicit HistData CSV path (repeatable). Default: auto-discover under data/HISTDATA_*",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            default=True,
            help="Replace existing month shards (default: on).",
        )
        parser.add_argument(
            "--no-overwrite",
            action="store_false",
            dest="overwrite",
            help="Skip month shards that already exist with equal or more rows.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List sources only; do not write shards.",
        )

    def handle(self, *args, **options):
        data_root = Path(settings.TRADEBOT_DATA_ROOT)
        slug = options["slug"].strip().lower()
        symbol = (options.get("symbol") or slug).upper()

        if options["source"]:
            sources = [Path(p) for p in options["source"]]
        else:
            sources = discover_histdata_csvs(data_root, symbol)

        if not sources:
            raise CommandError(
                f"No HistData files for {symbol}. Expected data/HISTDATA_*{symbol}*/DAT_ASCII_{symbol}_M1_*.csv"
            )

        self.stdout.write(f"Sources ({len(sources)}):")
        for path in sources:
            self.stdout.write(f"  {path}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run — no files written."))
            return

        result = import_histdata_to_slug(
            data_root,
            slug=slug,
            symbol=symbol,
            source_paths=sources,
            overwrite=options["overwrite"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {result.bar_count:,} bars → {data_root / slug / 'months'} "
                f"({len(result.month_files)} month files)"
            )
        )
        if result.start and result.end:
            self.stdout.write(f"  Range: {result.start.date()} → {result.end.date()}")
