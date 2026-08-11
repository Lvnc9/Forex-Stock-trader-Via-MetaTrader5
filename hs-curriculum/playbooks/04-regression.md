# Playbook 04 — Regression

## Goal
Prove recall / entry / TP fixes do not regress each other. Spec-locked fixtures beat anecdotal chart screenshots.

## What to load
1. All of `hs-curriculum/` (L0, L1, `hs-spec.v1.json`, playbooks 01–03)
2. Fixture set: gold labels + synthetic bars covering:
   - top & inverse
   - up-sloping and down-sloping necklines
   - mode A and mode B entries
   - dual-scale head merge
   - hard-reject cases (no prior trend, flat shoulders, slope > max)
3. Baseline metrics snapshot (recall, precision, premature entry rate, TP1/TP2 hit)

## What to touch (when test harness / MQL is pointed)
- Unit tests for sequence, prominence, tolerances, confirmation matrix
- Integration tests: detect → confirm → enter → SL/TP staging
- Golden-file or JSON fixture runner comparing emissions to labels
- Metric report generator (R2–R5, E1–E5, T1–T5)

## What NOT to change
- Spec defaults in `hs-spec.v1.json` without documenting TUNABLE calibration and updating L0 acceptance numbers
- Production magic numbers that bypass the spec
- Do not disable hard rejects to greenwash recall tests

## Done-when checklist
- [ ] Fixture matrix covers confirmation slope cases (top/inverse × up/down/flat)
- [ ] Dual-scale required: test fails if only one scale runs
- [ ] Entry forbidden cases assert no order
- [ ] TP staging asserts TP1/TP2 prices from H within epsilon
- [ ] Metrics vs baseline: recall↑ or stable with FP cap; premature↓; TP1 hit↑
- [ ] Any threshold change logged as TUNABLE calibration (old → new, dataset id)
- [ ] Handoff fields in `label_schema_expected` present on all gold rows
