# L1 — Distill (eight agent-ready chunks)

Authority (mental cite only; distill into OUR rules): Edwards & Magee (definition), Bulkowski Encyclopedia (empirics; tops ~51% full-target hit in his 2020 bull-market **stock** sample — **FX must re-estimate**), StockCharts ChartSchool (secondary).

---

## 1. Prior trend requirement

- REQUIRE a clear prior move into the pattern before labeling H&S.
- TOP: prior **uptrend**; INVERSE: prior **downtrend**.
- MEASURE prior trend over lookback `prior_trend_bars` TUNABLE (default **50** bars on detection TF).
- PASS if net directional move ≥ `min_prior_move_atr` × ATR TUNABLE (default **2.0**).
- FAIL → do not emit pattern (score may still compute for diagnostics, but `valid=false`).

---

## 2. Pivot / swing definition

- PIVOT HIGH: bar high ≥ highs of `L` bars left and `L` bars right TUNABLE (`swing_L_short` default **3**, `swing_L_medium` default **8`).
- PIVOT LOW: mirror on lows.
- RUN detection on **two** scales (short + medium); merge candidates that share the same head pivot within `merge_head_bars` TUNABLE (default **3**).
- IGNORE pivots with amplitude < `min_pivot_atr` × ATR TUNABLE (default **0.5**).
- SEQUENCE uses confirmed pivots only (right-side `L` bars must have closed).

---

## 3. Head prominence

- TOP: head high > both shoulder highs by ≥ `head_prominence_atr` × ATR TUNABLE (default **0.5**).
- INVERSE: head low < both shoulder lows by ≥ same threshold.
- ALSO require head beyond neckline projection by ≥ `min_atr_mult` × ATR TUNABLE (default **1.0**) when projecting from shoulder line — use as soft score if geometric neckline not yet fixed.
- FAIL hard prominence → reject; soft miss → score penalty, not auto-accept.

---

## 4. Shoulder symmetry tolerances

- HEIGHT: `|HS_left − HS_right| / ATR ≤ shoulder_tol` TUNABLE (default **1.0** ATR).
- TIME: `|bars(left_shoulder→head) − bars(head→right_shoulder)| / max(left,right) ≤ time_tol` TUNABLE (default **0.35**).
- WIDTH: optional `|width_L − width_R| / avg_width ≤ width_tol` TUNABLE (default **0.40**).
- Prefer **tolerance bands + score** over binary reject when within 1.25× tolerance (soft zone) TUNABLE.

---

## 5. Neckline construction + sloping confirmation

- NECKLINE: line through **left armpit** and **right armpit** (troughs between LS–head and head–RS for tops; peaks for inverse).
- SLOPE: `neckline_slope = Δprice / Δbars`; reject if `|slope| > max_neckline_slope` in price/bar units normalized by ATR: `|Δprice| / (Δbars × ATR) > max_neckline_slope` TUNABLE (default **0.15**).
- CONFIRM TOP, neckline **up-sloping**: wait for **close below** neckline.
- CONFIRM TOP, neckline **down-sloping**: wait for **close below right armpit** (not the extended down-sloping line alone).
- INVERSE: mirror (close above neckline if down-sloping into break; if neckline up-slopes against break, confirm on close above right armpit).
- Intrabar pierce without close = **not** confirmation.

---

## 6. Volume (FX limitations)

- Classic rule: volume often higher on left shoulder / head decline phases; lighter on right shoulder; expansion on breakout (stocks).
- FX spot: **tick volume / broker volume is not real exchange volume** — treat as **optional soft score** only.
- IF volume series present: breakout bar volume ≥ `vol_breakout_mult` × SMA(volume, N) TUNABLE (default mult **1.2**, N **20`) → +score.
- IF absent or FX: set `volume_weight = 0` in score; **do not reject** on volume.

---

## 7. Entry modes (confirmation close vs retest)

- MODE A (`confirmation_close`): enter on confirmation event (E2/E3); optional `enter_next_open` TUNABLE (default false = enter at confirm close price for backtest fill model).
- MODE B (`retest_rejection`): after confirmation, wait for price to retest neckline (or right-armpit level if that was the confirm level) within `retest_max_bars` TUNABLE (default **15**); enter on rejection close back in breakout direction.
- NEVER enter on right-shoulder pivot alone.
- SL set at entry time per spec (beyond right shoulder ± ATR buffer).

---

## 8. Measure rule + statistical TP

- H = vertical distance from **head extreme** to **neckline** (at head’s time), absolute value.
- CLASSIC measure: target ≈ H projected from breakout point.
- STATS: Bulkowski-style full-target hit on H&S **tops** ~**51%** in cited **stock / bull-market** sample — **do not treat as FX truth**; mark `k` TUNABLE.
- OUR DEFAULT STAGING:
  - TP1 = **0.5 × H** (partial)
  - TP2 = **k × H** with **k = 0.51** pending FX calibration
  - Optional trail after TP1: trail by `trail_atr` × ATR TUNABLE (default **1.0**)
- Prefer staged hits over single 1.0×H default.
