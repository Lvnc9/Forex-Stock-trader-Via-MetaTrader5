# H&S Data Pack — bars, labels, evaluation harness

Evidence pack for proving detector fixes on **recall**, **entry timing**, and **TP hit rates**.  
Schema authority: [`../hs-curriculum/hs-spec.v1.json`](../hs-curriculum/hs-spec.v1.json).  
Bugs under test: [`../hs-curriculum/L0-diagnosis.md`](../hs-curriculum/L0-diagnosis.md).

**Do not** treat Bulkowski stock hit rates as FX truth. This harness computes **our** hit rates from broker (or Dukascopy) bars + hand labels.

Primary symbols: `EURUSD`, `GBPUSD`, `USDJPY`, `XAUUSD`.  
Primary timeframes: `H1`, `H4`, `D1`.

---

## Folder layout

```
hs-data/
  raw/          # Broker/Dukascopy dumps as downloaded (ticks or History Center exports)
  bars/         # Aggregated OHLCV bars used by the harness (CSV)
  labels/       # Hand labels + schema + seed templates
  reports/      # harness output (JSON + Markdown scorecards)
  harness/      # evaluate.py + matching/metrics
  synthetic/    # Unit-test seeds ONLY — never live truth
```

| Path | Purpose |
|------|---------|
| `raw/` | Untouched downloads; keep for audit |
| `bars/` | One CSV per `SYMBOL_TF.csv` (e.g. `EURUSD_H1.csv`) |
| `labels/` | `schema.json`, filled labels, seed examples |
| `images/` | Research chart corpus (rendered/downloaded) + labeling checklist for **failures** |
| `reports/` | Precision/recall/F1, missed IDs, entry match, TP rates, failure gates |
| `harness/` | Drop-in evaluator — no EA source required |
| `synthetic/` | Geometric fake patterns for unit tests (includes failure bust) |

---

## 1. Primary: Broker MT5 History

1. Open MetaTrader 5 → **View → Symbols** → enable the working symbols.
2. **Tools → History Center** (or chart → right-click → **Refresh** after setting Max. bars in Tools → Options → Charts).
3. Download **H1 / H4 / D1** for each symbol (aim for ≥ 5–10 years where the broker allows).
4. Export bars:
   - Chart open → right-click → **Save as** → CSV, **or**
   - Use an MT5 script / Python `MetaTrader5` package on Windows to dump rates.
5. Place exports under `raw/mt5/<SYMBOL>/<TF>/` then normalize into `bars/` (see bar CSV format below).

### Suggested dump via Python (Windows + MT5 terminal)

```python
# Run on the Windows machine that has MetaTrader5 installed.
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

mt5.initialize()
rates = mt5.copy_rates_range("EURUSD", mt5.TIMEFRAME_H1, datetime(2015, 1, 1), datetime(2026, 1, 1))
df = pd.DataFrame(rates)
df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
df.to_csv("EURUSD_H1.csv", index=False)
mt5.shutdown()
```

Copy resulting CSVs into `hs-data/bars/`.

---

## 2. Secondary cross-check: Dukascopy ticks → M1 → aggregate

Use when you want an independent feed vs broker bars (spread/session differences matter for confirmation closes).

1. Download tick CSVs (e.g. Dukascopy Historical Data Feed / community mirrors).
2. Store under `raw/dukascopy/<SYMBOL>/`.
3. Build M1 OHLC from ticks, then aggregate to H1/H4/D1.
4. Write aggregates to `bars/` with a clear filename suffix if comparing feeds, e.g. `EURUSD_H1_duka.csv`.

### Minimal tick → M1 sketch

```python
# Illustrative — adjust column names to your Dukascopy export.
import pandas as pd

ticks = pd.read_csv("raw/dukascopy/EURUSD/ticks.csv", parse_dates=["time"])
ticks = ticks.set_index("time").sort_index()
# mid = (bid + ask) / 2 if both present
m1 = ticks["mid"].resample("1min").ohlc().dropna()
m1["volume"] = ticks["mid"].resample("1min").count()
h1 = m1.resample("1h").agg(
    {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
).dropna()
h1.to_csv("bars/EURUSD_H1_duka.csv")
```

Always keep broker bars as the **primary** evaluation feed unless Agent 3’s detector was trained/run on Dukascopy.

---

## Bar CSV format (`bars/`)

Required columns (header row):

| Column | Notes |
|--------|--------|
| `time` | ISO-8601 UTC preferred (`2019-03-15T14:00:00Z`) or epoch seconds |
| `open` | float |
| `high` | float |
| `low` | float |
| `close` | float |
| `volume` | optional (tick volume OK; soft score only per hs-spec) |

**Bar index** = 0-based row order after sorting by `time` ascending. Labels and detections reference these indices.

Filename convention: `{SYMBOL}_{TF}.csv` — `EURUSD_H1.csv`, `XAUUSD_D1.csv`.

---

## Labels

- Schema: [`labels/schema.json`](labels/schema.json) (extends `hs-spec.v1` `label_schema_expected` with bar indices + outcomes).
- Hand-labeling: [`labels/seed_examples/LABELING_CHECKLIST.md`](labels/seed_examples/LABELING_CHECKLIST.md).
- Target volume: **50–100 true patterns** + **~50 hard negatives**.

Filled labels go in `labels/filled/` (create as you label) as one JSON object per file or a JSON array file.

---

## Run the harness

```bash
cd hs-data
python -m harness.evaluate \
  --bars-dir bars \
  --labels labels/filled \
  --detections path/to/detector_export.json \
  --entry-mode A \
  --outcome-bars 50 \
  --out reports/run_001
```

Produces:

- `reports/run_001/scorecard.json`
- `reports/run_001/scorecard.md`
- Lists: `missed_label_ids`, precision / recall / F1, `entry_bar_match_rate`, `hit_0_5H` / `hit_1_0H` rates (computed on **our** bars, not literature).

See [`harness/README.md`](harness/README.md) and [`HANDOFF-agent3.md`](HANDOFF-agent3.md) for the detector export format.

---

## Synthetic data

[`synthetic/`](synthetic/) generates geometric H&S bars for **unit tests only**. Never mix into gold precision/recall reports.
