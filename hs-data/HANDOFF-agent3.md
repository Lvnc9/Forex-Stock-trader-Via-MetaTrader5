# Handoff — Agent 3 (Detector export contract)

Agent 2 delivers bars/labels/harness. Agent 3 wires the H&S detector/EA to emit exports the harness can score **without reading EA source**.

Do **not** change label schema without bumping `labels/schema.json` and this file.

---

## Detector export formats

Accept either **JSON** (preferred) or **CSV**. One row/object per detected pattern that the EA would trade or would show as a valid signal.

### JSON

```json
[
  {
    "detection_id": "EURUSD_H1_top_h125_s3",
    "symbol": "EURUSD",
    "timeframe": "H1",
    "direction": "top",
    "LS_bar_index": 100,
    "LS_price": 1.1020,
    "trough1_bar_index": 110,
    "trough1_price": 1.0950,
    "head_bar_index": 125,
    "head_price": 1.1100,
    "trough2_bar_index": 140,
    "trough2_price": 1.0970,
    "RS_bar_index": 155,
    "RS_price": 1.1010,
    "neckline_left_bar_index": 110,
    "neckline_left_price": 1.0950,
    "neckline_right_bar_index": 140,
    "neckline_right_price": 1.0970,
    "confirmation_bar_index": 162,
    "confirmation_price": 1.0940,
    "confirm_rule": "close_beyond_neckline",
    "entry_mode": "A",
    "entry_bar_index": 162,
    "entry_price": 1.0940,
    "retest_bar_index": null,
    "H": 0.014,
    "score": 72.5,
    "scale": "medium"
  }
]
```

Also accepted: `{ "detections": [ ... ] }` wrapper.

### CSV columns (header required)

| Column | Required | Notes |
|--------|----------|--------|
| `detection_id` | no | Auto-built from symbol/TF/direction/head if omitted |
| `symbol` | **yes** | `EURUSD` / `GBPUSD` / `USDJPY` / `XAUUSD` |
| `timeframe` | **yes** | `H1` / `H4` / `D1` |
| `direction` | **yes** | `top` \| `inverse` |
| `head_bar_index` | **yes** | 0-based index into the **same** bars CSV the labels use |
| `LS_bar_index`, `LS_price` | recommended | |
| `trough1_bar_index`, `trough1_price` | recommended | = left armpit |
| `trough2_bar_index`, `trough2_price` | recommended | = right armpit |
| `RS_bar_index`, `RS_price` | recommended | |
| `neckline_left_bar_index`, `neckline_left_price` | recommended | |
| `neckline_right_bar_index`, `neckline_right_price` | recommended | |
| `confirmation_bar_index`, `confirmation_price` | **yes for entry metrics** | Bar of confirming **close** |
| `confirm_rule` | recommended | `close_beyond_neckline` \| `close_beyond_right_armpit` |
| `entry_mode` | recommended | `A` \| `B` |
| `entry_bar_index`, `entry_price` | **yes for entry metrics** | Mode A ≈ confirm; Mode B ≈ retest reject |
| `retest_bar_index` | Mode B | |
| `H` | recommended | Measured move height |
| `score` | optional | 0–100 |
| `scale` | optional | `short` \| `medium` |

### Accepted aliases

`left_armpit_*` → `trough1_*`, `right_armpit_*` → `trough2_*`,  
`confirm_bar_index` → `confirmation_bar_index`, `entry_bar` → `entry_bar_index`,  
`id` / `pattern_id` → `detection_id`.

---

## Bar index contract

- Indices are **0-based** into `hs-data/bars/{SYMBOL}_{TF}.csv` after sort by `time` ascending.
- Detector must run on (or map to) that exact series — broker primary; Dukascopy only if labels used the Duka file (`bars_file` override).

---

## Matching rules (harness)

A detection matches a true label when:

1. Same `symbol`, `timeframe`, `direction`
2. `|detection.head_bar_index − label.head_bar_index| ≤ match_tol_bars` (default **5**)

Unmatched detections → FP. Unmatched true labels → FN (`missed_label_ids`).  
Hard-negative labels matched by a detection → false accepts (count as FP).

`entry_bar_match_rate`: among matches with both sides having an entry bar,  
`|det.entry_bar_index − label_entry| ≤ match_tol_bars`  
(label_entry = `entry_bar_index` or Mode A confirmation / Mode B retest).

---

## Smoke command for Agent 3

```bash
cd hs-data
python -m synthetic.generate_synthetic --out synthetic/out
python -m harness.evaluate \
  --bars-dir synthetic/out/bars \
  --labels synthetic/out/labels \
  --detections synthetic/out/detections_perfect.json \
  --out reports/synth_perfect
```

Expect recall/precision ≈ 1.0 on the two true synthetic labels; hard negative unmatched.

Then point `--detections` at **your** EA export over real `bars/` + `labels/filled/`.

---

## Out of scope for Agent 3 (this handoff)

- Do not rewrite the label schema.
- Do not treat synthetic patterns as production truth.
- Fix order remains Recall → Entry → TP per `hs-curriculum/L0-diagnosis.md`.
