"""
Download equity / ETF daily (or intraday where available) via yfinance.

Limitations vs Dukascopy M1 forex/CFD data:
- yfinance daily bars lack true M1 OHLC quality for forex CFDs
- Intraday history is short and vendor-throttled
- Prefer MT5 copy_rates on the Windows agent for broker-accurate history

Example:
  python manage.py download_stocks --ticker AAPL --slug aapl --period 2y
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Download stock/ETF OHLCV via yfinance into data/<slug>/ (documented Phase 4 path)."

    def add_arguments(self, parser):
        parser.add_argument("--ticker", required=True, help="Yahoo ticker, e.g. AAPL")
        parser.add_argument("--slug", help="Local folder name (default: lower ticker)")
        parser.add_argument("--period", default="2y", help="yfinance period (default 2y)")
        parser.add_argument("--interval", default="1d", help="yfinance interval (default 1d)")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        ticker = options["ticker"].strip().upper()
        slug = (options.get("slug") or ticker.lower()).strip().lower()
        period = options["period"]
        interval = options["interval"]
        data_root = Path(settings.TRADEBOT_DATA_ROOT)
        out_dir = data_root / slug
        out_path = out_dir / f"{slug}_{interval}.csv"

        self.stdout.write(
            f"yfinance {ticker} period={period} interval={interval} → {out_path}"
        )
        if options["dry_run"]:
            return

        try:
            import yfinance as yf
        except ImportError as exc:
            raise CommandError("Install yfinance: pip install yfinance") from exc

        frame = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
        if frame is None or frame.empty:
            raise CommandError(f"No data returned for {ticker}")

        # Normalize to timestamp,open,high,low,close (epoch ms) for catalog familiarity
        frame = frame.reset_index()
        time_col = "Datetime" if "Datetime" in frame.columns else "Date"
        frame["timestamp"] = (frame[time_col].astype("int64") // 10**6).astype("int64")
        # Flatten multiindex columns if present
        cols = {c: str(c).lower() if not isinstance(c, tuple) else str(c[0]).lower() for c in frame.columns}
        frame = frame.rename(columns=cols)
        keep = ["timestamp", "open", "high", "low", "close"]
        for col in keep:
            if col not in frame.columns:
                raise CommandError(f"Missing column {col} in yfinance frame: {list(frame.columns)}")
        out_dir.mkdir(parents=True, exist_ok=True)
        frame[keep].to_csv(out_path, index=False)
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(frame)} rows → {out_path}"))
        self.stdout.write(
            self.style.WARNING(
                "Note: stock daily/intraday from yfinance is not equivalent to Dukascopy M1 CFD data."
            )
        )
