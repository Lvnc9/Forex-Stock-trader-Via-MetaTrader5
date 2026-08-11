# SYNTHETIC — unit-test seeds only

**Not live truth.** Do not mix these bars/labels into gold precision/recall or FX TP calibration.

```bash
cd hs-data
python -m synthetic.generate_synthetic --out synthetic/out --seed 42
```

Writes:

- `synthetic/out/bars/SYNTH_H1.csv`
- `synthetic/out/labels/*.json` — one clean top, one inverse, one hard-negative double-top
- `synthetic/out/detections_perfect.json` — oracle detections (for harness smoke)
- `synthetic/out/detections_miss_one.json` — drops the top (for recall demo)
