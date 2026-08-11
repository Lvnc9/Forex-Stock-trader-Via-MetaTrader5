# Playbook 01 — Recall (Bug A)

## Goal
Raise H&S recall without exploding false positives. Dual swing scales + tolerances + score gate.

## What to load
1. `hs-curriculum/L0-diagnosis.md` (Bug A)
2. `hs-curriculum/L1-distill.md` chunks 1–5
3. `hs-curriculum/hs-spec.v1.json` → `pivots`, `prior_trend`, `geometry`, `required_pivot_sequence`, `score`
4. Gold/silver label set conforming to `label_schema_expected`

## What to touch (when MQL / detector code is pointed)
- Pivot / swing detectors (short + medium `L`)
- Pattern assembler (sequence LS → armpit → head → armpit → RS)
- Shoulder / time / width tolerance checks
- Neckline slope max check
- Pattern score + `MinScoreThreshold`
- Dual-scale merge on shared head

## What NOT to change
- Entry timing / confirmation logic (playbook 02)
- SL/TP / measure-rule staging (playbook 03)
- Unrelated indicators, UI chrome, broker I/O
- Do not delete prior-trend or prominence hard fails to “buy” recall

## Done-when checklist
- [ ] Dual-scale detection required and both scales execute
- [ ] `shoulder_tol`, `time_tol`, `head_prominence_atr`, `max_neckline_slope` read from spec (or mirrored constants tagged TUNABLE)
- [ ] R2 recall ≥ threshold on gold set TUNABLE
- [ ] R3 precision floor held TUNABLE
- [ ] R4 FP increase ≤ cap TUNABLE
- [ ] Hard rejects still fire for missing sequence / hard prominence / prior trend / slope max
- [ ] Regression suite in playbook 04 still green for entry/TP fixtures
