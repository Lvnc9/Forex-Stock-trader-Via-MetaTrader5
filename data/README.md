# Local market data (not in git)

OHLC CSVs for backtesting. **Agents:** use this file for layout — do not load full CSVs into context.

## Layout

```text
data/
  {symbol}/           # e.g. eurusd, spx, aapl
    YYYY.csv          # optional merged year file
    months/           # preferred: dukascopy-node M1 shards (*-m1-YYYY-MM.csv)
    download_meta.json
  .cache/             # auto-built pickle cache (gitignored) — M1 + resampled TFs
```

When both `months/` and `YYYY.csv` exist, the loader **uses months only** (avoids double RAM).

## CSV schema (Dukascopy / TradeBot loader)

- Columns: `timestamp,open,high,low,close`
- `timestamp`: epoch **milliseconds** (UTC) preferred; ISO datetime strings are also accepted
- Granularity on disk: **M1** (1-minute bars). Strategy timeframes (M5–D1) are resampled at backtest time.

## Backtest timeframes

| TF | Meaning | Built from |
| -- | ------- | ---------- |
| M1 | 1 minute | source CSV |
| M5 / M15 / M30 | 5 / 15 / 30 minutes | resample M1 |
| H1 / H4 | 1 / 4 hours | resample M1 |
| D1 | 1 day | resample M1 |

Optional HTF must be **coarser** than primary (e.g. primary M5 + HTF H1).

## Performance knobs

- Parallel CSV reads: `TRADEBOT_BACKTEST_LOAD_WORKERS` (default 4)
- Disk cache: `TRADEBOT_BACKTEST_CACHE=True` → `data/.cache/`
- Async UI: `CELERY_TASK_ALWAYS_EAGER=False` + Redis + `celery -A config worker --concurrency=N`

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
