# H&S harness scorecard

- Generated: `2026-08-11T09:58:07.307262+00:00`
- Entry mode: `A`
- Match tol (bars): `5`
- Outcome bars: `50`

## Detection quality (Bug A — recall)

| Metric | Value |
|--------|-------|
| True labels | 3 |
| TP / FP / FN | 3 / 0 / 0 |
| Precision | 100.0% |
| Recall | 100.0% |
| F1 | 100.0% |

Missed label IDs (0):

- (none)

## Entry timing (Bug B)

- entry_bar_match_rate: **100.0%** (3/3)

## Take-profit hits (Bug C) — OUR FX bars

| Target | Hit rate | Count |
|--------|----------|-------|
| 0.5 × H | 100.0% | 3/3 |
| 0.51 × H (TP2) | 100.0% | 3/3 |
| 1.0 × H | 0.0% | 0/3 |

_Rates computed on OUR bars from label entry; not Bulkowski equity figures._

## Entry premature rate (Bug B — E5)

- premature_entry_rate (labeled tests): **n/a** (0/0)
- detector premature rate (all dets): **0.0%** (0/3)

## Hard-negative false accepts

- (none)
