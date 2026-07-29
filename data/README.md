# Local M1 market data (not in git)

OHLC CSVs for backtesting. **Agents:** use this file for layout — do not load full CSVs into context.

## Layout

```text
data/
  {symbol}/           # e.g. spx, dax, dow, silver, brent, sp500
    YYYY.csv          # merged year file
    months/           # optional per-month shards (dukascopy-node)
```

## CSV schema

- Columns: `timestamp,open,high,low,close`
- `timestamp`: epoch **milliseconds** (UTC)

## Population

Download/history scripts and logs may live here; see `PLAN.md` (market data / Phase 4). Large folders and `*.csv` are excluded via `.gitignore` and `.cursorignore`.
