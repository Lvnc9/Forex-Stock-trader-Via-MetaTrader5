# Market data downloads (Phase 4)

Local CSVs live under `data/` (gitignored). Agents should not ingest CSV contents into chat.

## FX — `download_bars`

Requires Node.js / `npx` and `dukascopy-node`.

```bash
python manage.py download_bars --fx-majors --from 2024-01-01 --to 2024-01-31 --dry-run
python manage.py download_bars --metals --from 2024-01-01 --to 2024-01-31 --dry-run
python manage.py download_bars --instrument xauusd --slug xauusd --from 2024-01-01 --to 2024-01-31
python manage.py download_bars --instrument eurusd --slug eurusd --from 2024-01-01 --to 2024-01-07
python manage.py seed_symbol_maps
```

**Catalog slugs** are lowercase folder names under `data/` (e.g. `xauusd`, not `XAUUSD`). The backtest/deploy dropdown shows friendly labels like **XAUUSD (gold)** when data exists.

**Metals:** `--metals` downloads `xauusd` (gold) and `xagusd` (silver). Legacy folder `data/silver/` (XAGUSD) is labeled in the UI; prefer slug `xagusd` for new downloads.

**HistData staging folders:** If you have `data/HISTDATA_*` zip extracts (semicolon M1 CSVs), merge into a catalog slug:

```bash
python manage.py import_histdata --slug xauusd --symbol XAUUSD
```

This writes `data/xauusd/months/xauusd-m1-YYYY-MM.csv` and hides `HISTDATA_*` from the catalog picker.

Writes under `data/<slug>/months/` plus `download_meta.json` or `import_meta.json`.

## Stocks — `download_stocks`

Uses **yfinance**. Daily/intraday history is **not** equivalent to Dukascopy M1 CFD data; prefer MT5 `copy_rates` on the Windows agent for broker-accurate equity history.

```bash
python manage.py download_stocks --ticker AAPL --slug aapl --period 2y --interval 1d --dry-run
```

## Schema

Prefer columns `timestamp,open,high,low,close` (epoch ms). Loader also accepts common dukascopy-node CSV layouts.
