# Head & Shoulders Failure — Trade Spec Distill

**Product rule:** Take positions **only** on H&S **failure / bust**, never on classic neckline reversal entries.

Authority for v1: Bulkowski busted H&S (head reclaim), adapted to FX with ATR. Secondary sources used for labeling rubrics and soft filters only.

Do **not** scrape Bulkowski site assets for model training. Rules below are manually distilled; labels use our own FX bars / rendered charts.

---

## Ranked sources (failure trading)

| Rank | Source | Role in this product |
|------|--------|----------------------|
| 1 | [Bulkowski — Busted H&S Top](https://www.thepatternsite.com/BustHST.html) | Operational bust definition + entry above head + stats |
| 2 | [Bulkowski — Busted Patterns](https://thepatternsite.com/Busted.html) | Shared bust framework for tops and bottoms |
| 3 | [Daily Price Action — H&S](https://dailypriceaction.com/blog/head-and-shoulders-pattern/) | FX continuation framing; HTF close confirmation of failure |
| 4 | [StockGro — Failed H&S](https://www.stockgro.club/blogs/trading/failed-head-and-shoulder-pattern/) | Checklist / RS-level labeling rubric (research A/B) |
| 5 | [WhaleEmpire — Why H&S Fails](https://whaleempire.com/2025/06/14/why-head-and-shoulders-pattern-fails/) | Soft filters (low-volume break, volume on reclaim) |

Machine-checkable twin: [`hs-curriculum/hs-spec.v1.json`](../hs-curriculum/hs-spec.v1.json) → `failure` block.

---

## Locked v1 definition (Bulkowski head-break)

### Precondition (structure + classic confirm — not a trade)

1. Valid H&S geometry (prior trend, prominence, sequence, neckline) per existing detector.
2. **Confirmation close** beyond neckline (or right armpit when neckline slopes against the break) — same as classic confirm.
3. Classic neckline entry is **`trade: false`**. Confirmation only arms the failure watcher.

### Bust / failure (the only trade)

For a **top** (classic would short):

1. After confirm, track adverse excursion from breakout price (confirm close).
2. If adverse **close** from breakout exceeds `max_bust_atr × ATR` **before** failure confirmation → **dead** (classic follow-through). No trade. (Wick extremes still recorded for stop placement.)
3. Else if a bar **closes above the head high** → **failure confirmed**.
4. **ENTER LONG** at that close (or next open if `enter_next_open`).
5. **Stop:** below the failed-breakdown extreme (min low from confirm through entry) minus `sl_atr_buffer × ATR`.
6. **Targets:** project `H` upward from entry — TP1 = `0.5×H`, TP2 = `k×H` (same staging idea as classic, mirrored).

Mirror for **inverse** H&S failure → ENTER SHORT on close below head low, with adverse capped above the breakout.

### FX adaptation note

Bulkowski stock rule uses ≤10% adverse from breakout. That is not FX-native. Spec uses `max_bust_atr` (default **1.5**, tunable). Calibrate on labeled FX failures.

### Research-only variants (harness A/B — not live default)

| Variant | Failure level | Use |
|---------|---------------|-----|
| `head` | Close beyond head (v1 default) | Live + primary gates |
| `rs` | Close beyond right shoulder | Precision/recall comparison |
| `neckline` | Close back beyond neckline | Earlier entries; more false busts |

---

## Soft score / filters (optional)

From sources 4–5 — soft penalties, not hard rejects unless calibrated:

- Low relative volume on classic breakdown → slightly higher failure prior.
- Expanding volume on reclaim / head break → quality boost.
- Strong prior trend (continuation regime) → favor failure trades.

FX tick volume is not exchange volume; keep volume weight soft (`volume.required: false`).

---

## Acceptance gates (failure-only)

| Gate | Target |
|------|--------|
| Classic neckline entries emitted by failure strategy | **0** |
| Failure precision on gold set | ≥ 0.45 (tunable) |
| Failure recall on gold set | ≥ 0.55 (tunable) |
| Premature failure entry (before confirm or before head reclaim) | ≤ 0.10 |
| TP1 (0.5×H opposite) hit rate | Track; calibrate before claiming edge |

---

## State machine

```
Structure → Confirmed → Watching
Watching → Dead     (adverse > max_bust)
Watching → Failed   (close beyond head)
Failed   → Enter opposite of classic
```

---

## Related paths

| Path | Role |
|------|------|
| `apps/strategies/patterns/head_shoulders/failure.py` | Bust watcher |
| `apps/strategies/library/head_and_shoulders_failure.py` | Library strategy |
| `hs-data/images/` | Research chart corpus (bulk gitignored) |
| `hs-data/labels/schema.json` | Failure label fields |
