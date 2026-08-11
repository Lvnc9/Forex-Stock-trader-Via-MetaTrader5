"""Known instrument slugs, display names, and download defaults."""

from __future__ import annotations

# Dukascopy instrument id → local catalog slug (folder under data/).
FX_MAJORS: dict[str, str] = {
    "eurusd": "eurusd",
    "gbpusd": "gbpusd",
    "usdjpy": "usdjpy",
    "usdchf": "usdchf",
    "audusd": "audusd",
    "usdcad": "usdcad",
    "nzdusd": "nzdusd",
}

METALS: dict[str, str] = {
    "xauusd": "xauusd",
    "xagusd": "xagusd",
}

# Common indices / commodities (slug may differ from MT5 ticker).
INDICES: dict[str, str] = {
    "usa500idxusd": "sp500",
    "usa30idxusd": "dow",
    "deuidxeur": "dax",
    "brentcmdusd": "brent",
}

DOWNLOAD_PRESETS: dict[str, dict[str, str]] = {
    "fx-majors": FX_MAJORS,
    "metals": METALS,
    "indices": INDICES,
}

# Slug → human label for UI (backtest catalog picker, data catalog table).
# Slugs are lowercase folder names; MT5 symbols are usually uppercase.
SLUG_LABELS: dict[str, str] = {
    "eurusd": "EURUSD",
    "gbpusd": "GBPUSD",
    "usdjpy": "USDJPY",
    "usdchf": "USDCHF",
    "audusd": "AUDUSD",
    "usdcad": "USDCAD",
    "nzdusd": "NZDUSD",
    "xauusd": "XAUUSD (gold)",
    "xagusd": "XAGUSD (silver)",
    "silver": "XAGUSD (silver) — legacy slug",
    "brent": "Brent oil",
    "sp500": "S&P 500",
    "spx": "S&P 500 (spx slug)",
    "dow": "Dow Jones",
    "dax": "DAX",
    "dax30": "DAX 30",
}

# Suggested MT5 symbol when auto-seeding SymbolMap (broker may differ).
DEFAULT_MT5_SYMBOLS: dict[str, str] = {
    "eurusd": "EURUSD",
    "gbpusd": "GBPUSD",
    "usdjpy": "USDJPY",
    "usdchf": "USDCHF",
    "audusd": "AUDUSD",
    "usdcad": "USDCAD",
    "nzdusd": "NZDUSD",
    "xauusd": "XAUUSD",
    "xagusd": "XAGUSD",
    "silver": "XAGUSD",
    "brent": "BRENT",
    "sp500": "US500",
    "spx": "US500",
    "dow": "US30",
    "dax": "DE40",
    "dax30": "DE40",
}


def catalog_choice_label(slug: str, dukascopy_id: str | None = None) -> str:
    """Label for backtest/deploy catalog dropdowns."""
    base = SLUG_LABELS.get(slug, slug.upper())
    if dukascopy_id and dukascopy_id.lower() != slug.lower():
        return f"{base} ({dukascopy_id})"
    return base


def dukascopy_id_for_slug(slug: str) -> str:
    """Reverse lookup: slug → dukascopy instrument id."""
    slug = slug.lower()
    for mapping in (FX_MAJORS, METALS, INDICES):
        for inst, s in mapping.items():
            if s == slug:
                return inst
    return slug
