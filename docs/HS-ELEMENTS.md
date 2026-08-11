# Head & Shoulders — Pattern Elements

Machine authority: [`hs-curriculum/hs-spec.v1.json`](../hs-curriculum/hs-spec.v1.json).  
Human distill: [`hs-curriculum/L1-distill.md`](../hs-curriculum/L1-distill.md).

All fields marked **TUNABLE** in the spec must be re-estimated on the project FX label set before production freeze.

---

## 1. Prior trend

| Element | Rule | Spec key | Default |
|---------|------|----------|---------|
| Direction | Top requires prior **uptrend**; inverse requires prior **downtrend** | `prior_trend.top_requires` / `inverse_requires` | — |
| Lookback | Measure over N bars on detection timeframe | `prior_trend_bars` | 50 |
| Minimum move | Net directional move ≥ k × ATR | `min_prior_move_atr` | 2.0 |
| Hard fail | Missing prior trend → reject (`valid=false`) | `score.reject_if_hard_fail` | — |

---

## 2. Pivots / swings

| Element | Rule | Spec key | Default |
|---------|------|----------|---------|
| Pivot high | Bar high ≥ highs of L bars left **and** L right | `swing_L_short`, `swing_L_medium` | 3 / 8 |
| Pivot low | Mirror on lows | same | same |
| Dual scale | **Both** short and medium scales must run | `dual_scale_required` | true |
| Head merge | Merge candidates sharing head within N bars | `merge_head_bars` | 3 |
| Min amplitude | Ignore pivots < k × ATR | `min_pivot_atr` | 0.5 |
| Confirmation | Right-side L bars must have closed (confirmed pivot) | L1 chunk 2 | — |

---

## 3. Required pivot sequence

**Top:** `LS_high → left_armpit_low → head_high → right_armpit_low → RS_high`

**Inverse:** `LS_low → left_armpit_high → head_low → right_armpit_high → RS_low`

| Constraint | Top | Inverse |
|------------|-----|---------|
| Head vs shoulders | head > LS and RS | head < LS and RS |
| Armpit order | left armpit before head; right armpit before RS | same |

Missing sequence → hard reject.

---

## 4. Head prominence

| Element | Rule | Spec key | Default |
|---------|------|----------|---------|
| Top | head_high − max(LS, RS) ≥ k × ATR | `head_prominence_atr` | 0.5 |
| Inverse | min(LS, RS) − head_low ≥ k × ATR | same | 0.5 |
| Neckline projection | Head beyond shoulder line by ≥ k × ATR (soft if needed) | `min_atr_mult` | 1.0 |
| Hard fail | Below hard prominence threshold → reject | `score.reject_if_hard_fail` | — |

---

## 5. Shoulder symmetry (tolerance bands)

| Element | Formula | Spec key | Default |
|---------|---------|----------|---------|
| Height | \|HS_left − HS_right\| / ATR ≤ tol | `shoulder_tol` | 1.0 ATR |
| Time | \|bars(LS→head) − bars(head→RS)\| / max ≤ tol | `time_tol` | 0.35 |
| Width | \|width_L − width_R\| / avg_width ≤ tol (optional) | `width_tol` | 0.40 |
| Soft zone | Within 1.25× tolerance → score penalty, not auto-reject | `soft_tol_mult` | 1.25 |

Patterns failing only within TUNABLE soft bands may pass if score ≥ `MinScoreThreshold` (default 60).

---

## 6. Neckline

| Element | Rule | Spec key | Default |
|---------|------|----------|---------|
| Construction | Line through **left armpit** and **right armpit** | `neckline.construct_from` | armpits |
| Slope sign | up / down / flat from armpit price delta | `neckline.slope_sign` | — |
| Flat epsilon | \|Δprice\| ≤ k × ATR → flat | `flat_eps_atr` | 0.1 |
| Max slope | \|Δprice\| / (Δbars × ATR) ≤ max | `max_neckline_slope` | 0.15 |
| Hard fail | Slope exceeds max → reject | `score.reject_if_hard_fail` | — |

---

## 7. Confirmation (bar close only)

| Case | Top | Inverse |
|------|-----|---------|
| Neckline up or flat | Close **below** neckline | Close **above** neckline |
| Neckline down | Close **below** right armpit | Close **above** right armpit |

- Intrabar pierce without close = **not** confirmation (`require_bar_close: true`).
- `confirm_rule` enum: `close_beyond_neckline` \| `close_beyond_right_armpit`.

---

## 8. Entry modes

| Mode | ID | Trigger | Notes |
|------|-----|---------|-------|
| A | `confirmation_close` | Confirmation event | Optional `enter_next_open` (default false) |
| B | `retest_rejection` | Retest confirm level, rejection close | Window: `retest_max_bars` (15) |

**Forbidden:** enter on RS pivot alone; enter on intrabar pierce without close.

---

## 9. Stops and targets

| Element | Rule | Spec key | Default |
|---------|------|----------|---------|
| Measure H | \|head_extreme − neckline_at_head_time\| | `stops_targets.measure_H` | — |
| SL (top) | Above RS_high + buffer × ATR | `sl_atr_buffer` | 0.25 |
| SL (inverse) | Below RS_low − buffer × ATR | same | 0.25 |
| TP1 | k × H from entry | `TP.TP1.mult_H` | 0.5 |
| TP2 | k × H from entry | `TP.TP2.mult_H` | 0.51 (FX pending) |
| Full 1.0×H | **Not** sole default | `full_1H_as_sole_default` | false |
| Trail after TP1 | Optional ATR trail | `optional_trail_after_TP1` | off |

---

## 10. Volume (FX)

- Not required for validity. FX tick volume is soft score only.
- If absent: `volume_weight = 0`; do not reject on volume.

---

## 11. Pattern score (0–100)

| Component | Weight (default) |
|-----------|------------------|
| prior_trend | 15 |
| head_prominence | 20 |
| shoulder_symmetry | 20 |
| time_symmetry | 15 |
| neckline_quality | 15 |
| volume | 10 |
| dual_scale_agreement | 5 |

Emit only if score ≥ `MinScoreThreshold` (60) and no hard fail.

---

## 12. Label / detection field map

Labels use bar indices (`hs-data/labels/schema.json`). Spec time fields map as:

| Spec field | Label / detection field |
|------------|-------------------------|
| LS_time / LS_price | `LS_bar_index`, `LS_price` |
| left_armpit_* | `trough1_*` |
| head_* | `head_*` |
| right_armpit_* | `trough2_*` |
| RS_* | `RS_*` |
| confirm_time / confirm_price | `confirmation_bar_index`, `confirmation_price` |
| H | `H` |

Detector export contract: [`hs-data/HANDOFF-agent3.md`](../hs-data/HANDOFF-agent3.md).
