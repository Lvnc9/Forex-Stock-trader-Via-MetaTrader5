# Market data downloads (Phase 4)

Local CSVs live under `data/` (gitignored). Agents should not ingest CSV contents into chat.

## FX — `download_bars`

Requires Node.js / `npx` and `dukascopy-node`.

```bash
python manage.py download_bars --fx-majors --from 2024-01-01 --to 2024-01-31 --dry-run
python manage.py download_bars --instrument eurusd --slug eurusd --from 2024-01-01 --to 2024-01-07
```

Writes under `data/<slug>/months/` plus `download_meta.json`.

## Stocks — `download_stocks`

Uses **yfinance**. Daily/intraday history is **not** equivalent to Dukascopy M1 CFD data; prefer MT5 `copy_rates` on the Windows agent for broker-accurate equity history.

```bash
python manage.py download_stocks --ticker AAPL --slug aapl --period 2y --interval 1d --dry-run
```

## Schema

Prefer columns `timestamp,open,high,low,close` (epoch ms). Loader also accepts common dukascopy-node CSV layouts.
