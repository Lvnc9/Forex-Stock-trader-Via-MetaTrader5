# H&S harness scorecard

- Generated: `2026-08-10T14:22:27.988715+00:00`
- Entry mode: `A`
- Match tol (bars): `5`
- Outcome bars: `50`

## Detection quality (Bug A — recall)

| Metric | Value |
|--------|-------|
| True labels | 2 |
| TP / FP / FN | 1 / 0 / 1 |
| Precision | 100.0% |
| Recall | 50.0% |
| F1 | 66.7% |

Missed label IDs (1):

- `SYNTH_H1_top_geom_001`

## Entry timing (Bug B)

- entry_bar_match_rate: **100.0%** (1/1)

## Take-profit hits (Bug C) — OUR FX bars

| Target | Hit rate | Count |
|--------|----------|-------|
| 0.5 × H | 100.0% | 2/2 |
| 1.0 × H | 0.0% | 0/2 |

_Rates computed on OUR bars from label entry; not Bulkowski equity figures._

## Hard-negative false accepts

- (none)
