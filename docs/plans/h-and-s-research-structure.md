# Plan 1 — H&S Research Structure

**Status:** Implemented (Agent 3, Aug 2026)  
**Scope:** `hs-curriculum/` and `hs-data/` only — **no** `apps/strategies/` or Django UI until gates pass on real FX labels.

---

## Goal

Define, validate, and calibrate Head & Shoulders pattern elements and failure modes **before** any TradeBot Django strategy code.

---

## Source of truth (read first)

| Resource | Path |
|----------|------|
| Machine spec | `hs-curriculum/hs-spec.v1.json` |
| Three bugs (Recall, Entry, TP) | `hs-curriculum/L0-diagnosis.md` |
| Fix order playbooks | `hs-curriculum/playbooks/01-recall.md` … `04-regression.md` |
| Detector export contract | `hs-data/HANDOFF-agent3.md` |
| Label format | `hs-data/labels/schema.json` |
| Scoring harness | `hs-data/harness/evaluate.py` |

Human-readable distill: `docs/HS-ELEMENTS.md`, `docs/HS-FAILURES.md`.

---

## Deliverables (in order)

| Phase | Deliverable | Path / command |
|-------|-------------|----------------|
| R0–R1 | Element + failure docs | `docs/HS-ELEMENTS.md`, `docs/HS-FAILURES.md` |
| R2 | Real FX bars + filled labels (50+ true, 30+ hard neg) | `hs-data/bars/export_bars.py`, `hs-data/labels/generate_corpus.py` → `bars/`, `labels/filled/` |
| R3 | Detector (pivots, assembler, geometry, confirm, entry, export, CLI) | `hs-data/detector/` |
| R3+ | Harness: E5 premature entry + TP2 at k×H | `hs-data/harness/` (`--tp2-mult-h`, premature metrics) |
| R4–R5 | Synthetic fixture matrix + tunable calibration | `hs-data/synthetic/generate_synthetic.py`; meet gates R2/R3/E5/T2 |

---

## Fix order

**Recall (PB01) → Entry (PB02) → TP (PB03) → Regression (PB04)**

Do not fix entry by loosening detection, or TP by delaying entry.

---

## Acceptance gates (TUNABLE on FX labels)

| ID | Gate | Target |
|----|------|--------|
| R2 | Recall (gold set) | ≥ 0.70 |
| R3 | Precision floor | ≥ 0.40 |
| E5 | Premature entry rate | ≤ 0.10 |
| T2 | TP1 hit rate | ≥ 0.65 (TP2 tracked at k×H, default k=0.51) |

**Corpus calibration (auto-labels):** recall/precision/E5 met. **TP1** still needs hand labels on real bars.

---

## Validation loop

```bash
cd hs-data
python bars/export_bars.py --out-dir bars
python labels/generate_corpus.py
python -m synthetic.generate_synthetic --out synthetic/out
python -m detector.run --bars bars/EURUSD_H1_corpus.csv --symbol EURUSD --timeframe H1 --out reports/corpus_detections.json
python -m harness.evaluate \
  --bars-dir bars \
  --labels labels/filled \
  --detections reports/corpus_detections.json \
  --out reports/run_corpus
python -m unittest harness.tests.test_harness_smoke -v
```

---

## Out of scope (this plan)

- Django strategy / UI (`apps/strategies/`)
- Treating synthetic or auto-corpus as production truth
- Bulkowski stock hit rates as FX truth

---

## Next slice (after this plan)

1. Hand-label true H&S on real `bars/EURUSD_H1.csv` (yfinance or MT5).
2. Re-run harness for R2/T2 on hand labels.
3. Wire detector into Django strategy only when gates stable on real FX.

See `untilNow.md` for session handoff.
