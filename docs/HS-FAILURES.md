# Head & Shoulders — Failure Modes

Cross-reference: [`hs-curriculum/L0-diagnosis.md`](../hs-curriculum/L0-diagnosis.md) (three bugs), playbooks 01–04.

Fix order for implementation: **Recall (A) → Entry (B) → TP (C) → Regression (04)**.

---

## Bug A — Recall (misses real H&S)

### Symptom
Gold/silver labels never fire, or only textbook-perfect cases match. Valid patterns with mild asymmetry, sloping necklines, or dual-scale structure are dropped.

### Root causes (rules)

| ID | Cause | Spec / playbook touchpoint |
|----|-------|---------------------------|
| A1 | Single swing scale only | `pivots.dual_scale_required` — PB01 |
| A2 | Hard equality on shoulder heights | `geometry.shoulder_tol` — use ATR bands |
| A3 | Hard equality on time/width symmetry | `time_tol`, `width_tol`, `soft_tol_mult` |
| A4 | Neckline slope rejected too aggressively | `max_neckline_slope` |
| A5 | Prior-trend filter too strict | `prior_trend_bars`, `min_prior_move_atr` |
| A6 | MinScoreThreshold too high vs weights | `score.MinScoreThreshold`, weights |
| A7 | Hard fail conflated with soft miss | prominence / symmetry should score-penalize in soft zone |

### Acceptance gates (TUNABLE on FX labels)

| ID | Gate | Target |
|----|------|--------|
| R1 | Dual-scale detection runs both scales | yes/no |
| R2 | Recall on gold set | ≥ 0.70 |
| R3 | Precision floor | ≥ 0.40 |
| R4 | FP increase vs baseline | ≤ +25% relative |
| R5 | Soft-tolerance patterns pass if score ≥ threshold | yes/no |

### Fix strategy
Raise recall via dual scales + tolerances + score gate. **Do not** delete prior-trend or prominence hard fails to buy recall.

---

## Bug B — Entry (wrong time)

### Symptom
Orders at RS pivot or intrabar pierce; wrong confirm level for sloping necklines; whipsaws and late entries.

### Root causes

| ID | Cause | Spec touchpoint |
|----|-------|-----------------|
| B1 | Entry tied to pivot completion, not confirmation | `entry.forbidden` |
| B2 | Up-sloping neckline uses wrong confirm level | `confirmation.top.neckline_up_or_flat` |
| B3 | Down-sloping neckline ignores right-armpit rule | `confirmation.top.neckline_down` |
| B4 | No bar-close requirement | `confirmation.require_bar_close` |
| B5 | Mode A and B conflated | `entry.modes` |
| B6 | `pattern_detected` treated as `entry_allowed` | state machine — PB02 |

### Acceptance gates

| ID | Gate | Target |
|----|------|--------|
| E1 | No entry before confirmation event | yes/no |
| E2 | Up/flat neckline: close beyond neckline | yes/no |
| E3 | Down neckline: close beyond right armpit (mirrored inverse) | yes/no |
| E4 | Mode A and B implemented and selectable | yes/no |
| E5 | Premature entry rate on labeled cases | ≤ 0.10 |

### Premature entry (E5) definition
A detection is **premature** when `entry_bar_index < confirmation_bar_index`, or entry occurs on RS bar without confirm close. Harness tracks rate on labels tagged `premature_entry_test: true` (see `labels/schema` notes field).

### Fix strategy
Gate orders on confirmation close (mode A) or retest rejection (mode B). Never enter on RS pivot alone.

---

## Bug C — Take-profit (too far)

### Symptom
Single TP at 1.0×H; poor hit rate vs staged targets. Bulkowski ~51% full-target on **stock** H&S tops — **not FX truth**.

### Root causes

| ID | Cause | Spec touchpoint |
|----|-------|-----------------|
| C1 | Sole TP at 1.0×H | `TP.full_1H_as_sole_default: false` |
| C2 | No partials / staging | `TP.staging_required` |
| C3 | H mis-measured | `measure_H` head → neckline at head time |
| C4 | No separate TP2 tracking | `TP.TP2.mult_H` (k = 0.51 default) |

### Acceptance gates

| ID | Gate | Target |
|----|------|--------|
| T1 | TP1 = 0.5×H, TP2 = k×H (k = 0.51 default) | yes/no |
| T2 | TP1 hit rate on label set | ≥ 0.65; TP2 tracked separately |
| T3 | Full 1.0×H not sole default | yes/no |
| T4 | SL beyond RS ± ATR buffer | yes/no |
| T5 | Trail after TP1 never moves SL against trade | yes/no |

### Fix strategy
Stage targets; calibrate k on FX labels. Do not widen SL to fake hit rate.

---

## Hard-negative label reasons (must NOT detect)

Used in `hs-data/labels/schema.json` → `hard_negative_reason`:

| Reason | Description |
|--------|-------------|
| `double_top` | Two peaks, no higher head |
| `double_bottom` | Inverse double bottom |
| `broadening` | Expanding swings |
| `range_three_peak` | Three similar peaks in range |
| `false_break` | Break fails / no valid confirm close |
| `missing_prior_trend` | No prior trend |
| `no_head_prominence` | Head not beyond shoulders |
| `broken_sequence` | Wrong pivot order |
| `excessive_neckline_slope` | Slope above spec max |
| `other` | Document in `notes` |

Matched detection on hard negative → **false accept** (counts as FP).

---

## Cross-bug regression (Playbook 04)

After any fix, re-run fixture matrix:

- Top & inverse; up / down / flat necklines
- Mode A & B entries
- Dual-scale head merge
- Hard-reject cases (prior trend, prominence, slope, sequence)
- Metrics vs baseline: recall↑ or stable with FP cap; premature↓; TP1 hit↑

Validation loop:

```bash
cd hs-data
python -m synthetic.generate_synthetic --out synthetic/out
python -m detector.run --bars synthetic/out/bars --out synthetic/out/detections.json
python -m harness.evaluate \
  --bars-dir synthetic/out/bars \
  --labels synthetic/out/labels \
  --detections synthetic/out/detections.json \
  --out reports/run_XXX
```

---

## Diagnostic checklist (quick)

| Observation | Likely bug | First check |
|-------------|------------|-------------|
| Known gold label never matches | A (recall) | dual scale, tolerances, score threshold |
| Detection head OK but entry bar wrong | B (entry) | confirm_rule vs neckline slope |
| Entry at RS bar | B (entry) | forbidden path; confirmation gate |
| TP never hit in backtest | C (TP) | H measure, TP1/TP2 staging, k calibration |
| Hard negative matched | A (precision) | tighten score or hard fails |
| Recall up, FP +40% | A overfit | R4 cap; do not loosen all filters |
