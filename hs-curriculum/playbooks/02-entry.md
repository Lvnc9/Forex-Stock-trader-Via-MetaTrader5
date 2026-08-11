# Playbook 02 — Entry (Bug B)

## Goal
Enter only after confirmation. Mode A = confirmation close; Mode B = retest rejection. Never on RS pivot alone.

## What to load
1. `hs-curriculum/L0-diagnosis.md` (Bug B)
2. `hs-curriculum/L1-distill.md` chunks 5, 7
3. `hs-curriculum/hs-spec.v1.json` → `neckline`, `confirmation`, `entry`
4. Labels with `confirm_time`, `confirm_rule`, optional `entry_mode` / `entry_time`

## What to touch (when MQL / EA code is pointed)
- Confirmation evaluator (bar close vs neckline / right armpit by slope case)
- Signal → order bridge (gate on confirmation event)
- Mode A fill model (`enter_next_open` flag)
- Mode B retest window + rejection close
- State machine: `pattern_detected` ≠ `entry_allowed`

## What NOT to change
- Pivot geometry / recall thresholds (playbook 01) except if confirm level needs armpit prices already stored
- TP staging / measure H (playbook 03)
- Position sizing unrelated to confirm gate
- Do not treat intrabar pierce as confirmation

## Done-when checklist
- [ ] E1: no market entry before confirmation event
- [ ] E2/E3: up/flat vs down neckline rules match spec (top + inverse)
- [ ] Mode A and Mode B both implemented and selectable
- [ ] Forbidden paths blocked: RS-only entry; intrabar-only pierce
- [ ] E5: premature entry rate ≤ cap on labeled set TUNABLE
- [ ] SL still assigned at entry per spec (implementation may live in 03; must not regress)
