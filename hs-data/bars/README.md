# bars/

Normalized OHLCV used by labels + harness.

Filename: `{SYMBOL}_{TF}.csv`  
Columns: `time,open,high,low,close[,volume]`

Optional cross-check feed: `{SYMBOL}_{TF}_duka.csv` — set `bars_file` on the label if used.
