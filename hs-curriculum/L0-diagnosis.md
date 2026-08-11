# L0 — Diagnosis: three H&S bugs

Scope: classical Head & Shoulders (top + inverse). Treat each bug separately. Do not “fix entry” by loosening detection, or “fix TP” by delaying entry.

---

## Bug A — Recall (misses real H&S)

### Symptom
Labeled H&S (human or gold set) never fire, or fire only on textbook-perfect cases. Many valid patterns with mild asymmetry, sloping necklines, or dual-scale structure are dropped.

### Likely causes (rules, not code)
1. Single swing scale only (misses short-scale shoulders / medium-scale head).
2. Hard equality on shoulder heights / widths instead of tolerances.
3. Neckline slope rejected too aggressively.
4. Prior-trend filter too strict or wrong lookback.
5. MinScoreThreshold too high relative to scoring weights.

### Acceptance criteria
| ID | Criterion | Pass |
|----|-----------|------|
| R1 | Dual-scale detection (short + medium) is required and both scales run | yes/no |
| R2 | On gold label set: recall ≥ **0.70** TUNABLE | measured |
| R3 | On same set: precision ≥ **0.40** TUNABLE (floor; do not “buy” recall below this) | measured |
| R4 | F1 vs baseline improves; false positives do not increase > **+25%** relative TUNABLE | measured |
| R5 | Patterns failing only shoulder_tol / time_tol within TUNABLE bands are accepted if score ≥ MinScoreThreshold | yes/no |

### Outcome target
**Raise recall without exploding false positives.** Prefer dual scales + tolerances + score gate over deleting filters.

---

## Bug B — Entry (wrong time)

### Symptom
Orders fire at pattern “completion” of pivots (e.g. right shoulder print) instead of after **neckline confirmation**, or enter on the break without waiting for mode A/B rules. Whipsaws on early breaks; late entries after move already ran.

### Likely causes
1. Entry tied to pivot detection, not confirmation close / retest.
2. Up-sloping neckline uses wrong confirm level; down-sloping neckline ignores right-armpit rule.
3. No bar-close requirement (intrabar pierce treated as signal).
4. Entry mode A and B conflated.

### Acceptance criteria
| ID | Criterion | Pass |
|----|-----------|------|
| E1 | No market entry before confirmation event defined in `hs-spec.v1.json` | yes/no |
| E2 | Up-sloping neckline: confirm = **close beyond neckline** (top: below; inverse: above) | yes/no |
| E3 | Down-sloping neckline (top): confirm = **close below right armpit**; inverse mirrored | yes/no |
| E4 | Mode A: entry at confirmation close (or next open if configured); Mode B: entry only after retest rejection | yes/no |
| E5 | On labeled “premature entry” cases: premature rate ≤ **0.10** TUNABLE | measured |

### Outcome target
**Enter only after confirmation** (mode A or B). Pivot completion alone is never an entry.

---

## Bug C — Take-profit (too far)

### Symptom
TP set at full measured move (1.0 × H) or beyond; many trades reverse before hit. Hit rate poor vs literature (~51% full-target on Bulkowski stock H&S tops in a 2020 bull-market sample — **FX must re-estimate**).

### Likely causes
1. Single TP at 1.0 × H (or neckline height mis-measured).
2. No partials / staging.
3. H measured from wrong points (not head extreme → neckline).
4. No trail after TP1.

### Acceptance criteria
| ID | Criterion | Pass |
|----|-----------|------|
| T1 | Default staging: **TP1 = 0.5 × H**, **TP2 = k × H** with **k = 0.51** default pending FX calibration TUNABLE | yes/no |
| T2 | On OOS / label set: TP1 hit rate ≥ **0.65** TUNABLE; TP2 hit rate tracked separately (expect ~0.45–0.55 until FX calib) | measured |
| T3 | Full 1.0 × H is **not** the default sole target | yes/no |
| T4 | SL = beyond right shoulder ± ATR buffer per spec; R-multiple at TP1 ≥ **0.5** typical path documented | yes/no |
| T5 | Optional trail after TP1 does not move SL against trade | yes/no |

### Outcome target
**Improve TP hit rate with smaller/staged targets** (and optional trail), not by widening stops.

---

## Cross-bug rules
- Fix order for coding agents: **Recall → Entry → TP** (playbooks 01 → 02 → 03), then **04-regression**.
- Each PR/slice maps to one bug ID (A/B/C).
- All numeric gates marked TUNABLE must be re-fit on the project’s labeled FX set before production freeze.
