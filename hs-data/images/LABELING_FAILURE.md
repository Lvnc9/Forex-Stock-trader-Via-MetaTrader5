# Failure chart labeling checklist

Authority: [`docs/HS-FAILURE-TRADE.md`](../../docs/HS-FAILURE-TRADE.md) + `hs-spec.v1.json` `failure` block.

Use rendered charts (`images/rendered/`) or MT5/TradingView on the **same** bar series as `hs-data/bars/`.

## True failure (`trade_kind=failure`, `hard_negative=false`)

- [ ] Structure is a valid H&S (or inverse) with prior trend.
- [ ] Classic confirmation close exists (`confirmation_bar_index`).
- [ ] Adverse move after confirm stays within ~`max_bust_atr` ATR (note estimated ATR).
- [ ] Failure bar: **close beyond head** for v1 gold (`failure_level=head`).
- [ ] Fill `failure_bar_index`, `failure_price`, `failed_extreme_price` (min low / max high from confirm→entry).
- [ ] Set `entry_bar_index` / `entry_price` to failure entry (not classic confirm).
- [ ] `outcome_class`: `failure_success` if continuation after bust; else note.

## Hard negatives for failure detector

| reason / outcome | Meaning |
|------------------|---------|
| `classic_follow_through` | Confirm then deep adverse > max_bust — must **not** emit failure entry |
| `false_break` / invalid structure | Not a real H&S |
| Premature reclaim | Touched head intrabar but no **close** beyond head |

Add `deep_follow_through` to `hard_negative_reason` when using that enum (see schema).

## Coverage goals

| direction | failure_level | count aim |
|-----------|---------------|-----------|
| top | head | ≥15 |
| inverse | head | ≥15 |
| top/inverse | rs or neckline | research A/B only |
| classic_follow_through hard neg | — | ≥20 |
| invalid structure hard neg | — | ≥20 |
