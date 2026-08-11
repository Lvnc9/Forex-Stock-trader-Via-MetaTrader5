# H&S evaluation harness

Stdlib-only. Run from `hs-data/`:

```bash
python -m harness.evaluate \
  --bars-dir bars \
  --labels labels/filled \
  --detections detections/export.json \
  --entry-mode A \
  --outcome-bars 50 \
  --match-tol-bars 5 \
  --out reports/run_001
```

## Inputs

| Input | Format |
|-------|--------|
| Bars | `bars/{SYMBOL}_{TF}.csv` — columns `time,open,high,low,close[,volume]` |
| Labels | Directory of `.json` objects, or one `.json` / `.jsonl` array/lines |
| Detections | CSV or JSON — see [`../HANDOFF-agent3.md`](../HANDOFF-agent3.md) |

## Outputs (`--out` directory)

- `scorecard.json` — machine-readable metrics
- `scorecard.md` — human summary
- `missed_label_ids.json` — true labels with no matching detection
- `false_accept_ids.json` — hard negatives matched by a detection
- `per_label_outcomes.json` — hit_0_5H / hit_1_0H / mfe / mae

## Metrics

- **Precision / recall / F1** on non-`hard_negative` labels vs detections (match by symbol, TF, direction, head proximity).
- **missed_label_ids** — gold/silver true patterns unmatched.
- **entry_bar_match_rate** — fraction of matched pairs where `|det.entry_bar − label_entry| ≤ match-tol-bars` (Mode A → confirmation; Mode B → retest).
- **TP hit rates** — fraction of true matched (or all true with bars) hitting 0.5H and 1.0H within `--outcome-bars` — **computed on our bars**, not Bulkowski.

Hard negatives that match a detection count as false positives (hurt precision).
