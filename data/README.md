# Local market data (not in git)

OHLC CSVs for backtesting. **Agents:** use this file for layout — do not load full CSVs into context.

## Layout

```text
data/
  {symbol}/           # e.g. eurusd, spx, aapl
    YYYY.csv          # optional merged year file
    months/           # dukascopy-node shards
    download_meta.json
```

## CSV schema (Dukascopy / TradeBot loader)

- Columns: `timestamp,open,high,low,close`
- `timestamp`: epoch **milliseconds** (UTC) when produced by our normalizer; dukascopy-node may write datetime strings that the loader accepts

## Download commands

**FX majors (M1 via dukascopy-node — needs Node/`npx`):**

```bash
python manage.py download_bars --fx-majors --from 2024-01-01 --to 2024-01-31 --dry-run
python manage.py download_bars --instrument eurusd --slug eurusd --from 2024-01-01 --to 2024-01-07
```

**Stocks / ETFs (yfinance — daily or short intraday; not equivalent to Dukascopy M1 CFDs):**

```bash
python manage.py download_stocks --ticker AAPL --slug aapl --period 2y --interval 1d --dry-run
```

Prefer MT5 `copy_rates` on the Windows agent for broker-accurate history when trading equities.
