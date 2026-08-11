# H&S failure chart image corpus

Research-only images for **human labeling** of head-and-shoulders failures.  
Live trading uses bar OHLC + [`failure.py`](../apps/strategies/patterns/head_shoulders/failure.py) — not CV inference.

## Layout

```
hs-data/images/
  README.md                 # this file
  metadata/                 # committed JSON descriptors (no bulk pixels)
  downloaded/               # gitignored — optional illustrative charts from open pages
  rendered/                 # gitignored — candlestick renders from our bar CSVs
  tools/                    # download / render / rank helpers
  LABELING_FAILURE.md       # human checklist for failure labels
```

## Rules

1. Prefer **rendered** charts from our own `hs-data/bars/*.csv` (clean IP, exact bar indices).
2. Optional downloads: educational pages only; store URL + license note in metadata. **Do not** scrape Bulkowski for training images.
3. Never commit PNG/JPEG bulk. Metadata JSON is OK.
4. CV ranker only **prioritizes** candidates for human review — humans own gold labels.

## Quick start

```bash
cd hs-data
# Render a candlestick window from bars (no network):
python -m images.tools.render_candles \
  --bars bars/EURUSD_H1.csv \
  --start 100 --end 220 \
  --out images/rendered/EURUSD_H1_100_220.png \
  --meta-out images/metadata/EURUSD_H1_100_220.json

# Rank rendered images by simple contour/peak heuristic (optional assist):
python -m images.tools.rank_candidates --rendered-dir images/rendered --out images/metadata/rank.json

# Optional: download illustrative open-web charts listed in sources.json:
python -m images.tools.download_illustrations --sources images/tools/sources.json --out images/downloaded
```

Targets: ≥40 true failures + ≥40 hard negatives once hand-labeled into `labels/filled/` (bar indices, not pixels).
