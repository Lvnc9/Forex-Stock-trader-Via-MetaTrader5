# Hand-labeling checklist — H&S gold / hard negatives

Target: **50–100 true patterns** + **~50 hard negatives** across `EURUSD`, `GBPUSD`, `USDJPY`, `XAUUSD` × `H1`/`H4`/`D1`.

Authority: `hs-curriculum/hs-spec.v1.json` + `L1-distill.md`.  
Schema: `labels/schema.json`. Do **not** paste copyrighted chart images into the repo — pivots + indices only.

---

## Workflow

1. Load broker bars into a charting tool (MT5 / TradingView / custom).
2. Find candidates; measure pivots on the **same** bar series that will live in `hs-data/bars/`.
3. Copy `template.json` → `true_patterns/<label_id>.json` or `hard_negatives/<label_id>.json`.
4. Fill every required field; leave `outcomes` empty (harness computes them).
5. When you have a batch, move completed files into `labels/filled/` (create folder).
6. Run harness against detector export.

`label_id` convention: `{SYMBOL}_{TF}_{top|inverse|neg}_{YYYY-MM-DD}_{nnn}`

---

## True pattern (hard_negative = false)

Mark `label_quality`: `gold` if textbook + clear prior trend; `silver` if valid but asymmetric / soft tolerances.

### Geometry
- [ ] Prior trend present (top: uptrend; inverse: downtrend) over ~50 bars, ≥ ~2 ATR move.
- [ ] Sequence complete: LS → trough1 → Head → trough2 → RS (indices strictly increasing).
- [ ] Head more extreme than both shoulders (≥ ~0.5 ATR prominence).
- [ ] Shoulder height |LS−RS| / ATR ≤ ~1.0 (soft zone up to ~1.25× OK → silver).
- [ ] Time symmetry within ~0.35 relative (soft zone OK → silver).
- [ ] Neckline through trough1 & trough2; |slope| not wild vs ATR (spec max ~0.15).

### Confirmation (required)
- [ ] **Not** entry on RS pivot alone.
- [ ] Neckline up/flat (top): confirmation = first **close below** neckline → `confirm_rule=close_beyond_neckline`.
- [ ] Neckline down (top): confirmation = first **close below right armpit** → `confirm_rule=close_beyond_right_armpit`.
- [ ] Inverse: mirror (close above neckline or above right armpit per slope).
- [ ] Set `confirmation_bar_index` / `confirmation_price` to that close.
- [ ] `H = abs(head_price − neckline_price_at_head_bar)` (linear interpolate neckline at head index).

### Entry (optional but needed for entry metrics)
- [ ] Mode A: `entry_mode=A`, `entry_bar_index=confirmation_bar_index` (or next open if you document that).
- [ ] Mode B: fill `retest_bar_index` = rejection close after retest; `entry_bar_index` = same.

### Coverage goals (true set)
Aim for at least one of each confirmation branch:

| direction | neckline slope | confirm_rule |
|-----------|----------------|--------------|
| top | up/flat | close_beyond_neckline |
| top | down | close_beyond_right_armpit |
| inverse | down/flat | close_beyond_neckline |
| inverse | up | close_beyond_right_armpit |

Spread across symbols/TFs; avoid stuffing only EURUSD H1.

---

## Hard negatives (hard_negative = true)

Set `label_quality=reject` and a `hard_negative_reason`. Still fill pivot-ish points so the harness can score false accepts (detector fired on this region).

| reason | What to mark |
|--------|----------------|
| `double_top` | Two peaks, no clear higher head |
| `double_bottom` | Inverse of above |
| `broadening` | Expanding swings, not H&S |
| `range_three_peak` | Three similar peaks in a box |
| `false_break` | Looks like H&S but break fails / no valid confirm close |
| `missing_prior_trend` | Geometry OK-ish, no prior trend |
| `no_head_prominence` | “Head” not beyond shoulders |
| `broken_sequence` | Wrong pivot order |
| `excessive_neckline_slope` | Armpits imply absurd slope |
| `other` | Explain in `notes` |

For hard negatives, `confirmation_*` may be the **would-be** false break bar (document in `notes`). Detector must **not** count these as true positives.

---

## Empty slots ready to fill

- `true_patterns/_slot_001.json` … `_slot_005.json` — copy/rename as you go (create more as needed).
- `hard_negatives/_slot_001.json` … `_slot_005.json` — same.

Keep originals as blank templates; duplicate for each real label.
