# Backtest performance tuning

Thermal-aware defaults are intended for laptop use first, especially on a 12-core M4 Pro MacBook Pro.

## Recommended `.env` for M4 Pro 14-inch

```bash
TRADEBOT_BACKTEST_THERMAL_PROFILE=laptop
TRADEBOT_BACKTEST_CPU_FRACTION=0.7
TRADEBOT_BACKTEST_CORE_RESERVE=2
TRADEBOT_BACKTEST_LOAD_WORKERS=8
TRADEBOT_BACKTEST_WORKERS=8
TRADEBOT_BACKTEST_BLAS_THREADS=1
TRADEBOT_BACKTEST_PARALLEL_HS=True
TRADEBOT_BACKTEST_VECTOR_RULES=True
```

## Profiles

- `eco`: about 4 workers, best for long unattended runs.
- `laptop`: about 8 workers, recommended balance of speed and heat.
- `max`: about 10 workers, faster but more heat on sustained runs.

## Notes

- CSV and Parquet loading scale with `TRADEBOT_BACKTEST_LOAD_WORKERS`.
- Parameter sweeps and H&S candidate scoring use `TRADEBOT_BACKTEST_WORKERS`.
- BLAS-style thread pools are pinned to `1` to avoid oversubscribing cores.
- The portfolio simulation loop still runs sequentially by design.
