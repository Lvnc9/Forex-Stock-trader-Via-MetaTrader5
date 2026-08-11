"""Sensible defaults for the backtest create form."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from apps.marketdata.catalog import InstrumentCatalog, scan_data_root

PREFERRED_CATALOG_SLUGS = ("eurusd", "xauusd", "gbpusd", "usdjpy", "spx")


def pick_catalog(catalogs: list[InstrumentCatalog]) -> InstrumentCatalog | None:
    if not catalogs:
        return None
    by_slug = {c.slug.lower(): c for c in catalogs}
    for preferred in PREFERRED_CATALOG_SLUGS:
        if preferred in by_slug:
            return by_slug[preferred]
    return catalogs[0]


def default_backtest_dates(catalog: InstrumentCatalog | None) -> tuple[date | None, date | None]:
    if catalog and catalog.start and catalog.end:
        return catalog.start.date(), catalog.end.date()
    end = date.today()
    return end - timedelta(days=365), end


def backtest_form_defaults(data_root: Path | None) -> dict:
    """Catalog slug + date range from scanned datasets (when available)."""
    if data_root is None or not data_root.is_dir():
        return {}
    catalogs = scan_data_root(data_root)
    catalog = pick_catalog(catalogs)
    if catalog is None:
        return {}
    start, end = default_backtest_dates(catalog)
    out: dict = {"catalog_slug": catalog.slug}
    if start is not None:
        out["start"] = start
    if end is not None:
        out["end"] = end
    return out
