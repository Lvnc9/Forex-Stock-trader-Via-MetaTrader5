# TradeBot progress (`untilNow`)

Handoff file for the **next agent chat**. Update at the end of every session.

## Plan reference

- Full spec: [PLAN.md](./PLAN.md)

## Current state (last updated: 2026-07-29)

| Area | Status |
| ---- | ------ |
| Phase 1a (scaffold + auth + UI shell) | **Done** |
| Phase 1b (strategies + marketdata) | **Done** |
| Phase 1c (backtest + results UI) | Not started |

## Phase 1 checklist (PLAN)

| Item | 1a | 1b | 1c |
| ---- | -- | -- | -- |
| Django project + app layout | ✓ | | |
| Auth + Tailwind/HTMX shell | ✓ | | |
| `BaseStrategy` + `IndicatorRegistry` + `SignalEngine` + loader | | ✓ | |
| 3 library strategies (MA, RSI, range breakout) | | ✓ | |
| `Strategy` model + `seed_library_strategies` | | ✓ | |
| Market data catalog scan + M1 loader/resampler + `SymbolMap` | | ✓ | |
| UI: `/strategies/`, `/data/` | | ✓ | |
| Backtest runner + results UI | | | ○ |

## Completed this session (Phase 1b)

- **Strategies:** `BaseStrategy`, `Signal`, `BarContext`, `IndicatorRegistry` (SMA/EMA/RSI/MACD/BB/ATR, cross helpers), `SignalEngine`, module loader
- **Library:** `ma_crossover`, `rsi_reversal`, `range_breakout` under `apps/strategies/library/`
- **Marketdata:** `scan_data_root()`, `load_m1_bars()`, `resample_bars()`, `align_htf()`, `SymbolMap` model
- **UI:** Strategies list, Data catalog table; dashboard shows dataset count
- **Tests:** `apps/strategies/tests/test_phase1b.py` (catalog, loader, engine, loader)
- **Deps:** `pandas` in `requirements.txt`

## How to run

```bash
cd tradeBot
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_library_strategies
python manage.py createsuperuser   # if needed
python manage.py runserver
```

- http://127.0.0.1:8000/strategies/
- http://127.0.0.1:8000/data/
- Admin: `/admin/` → **Symbol map** for MT5 names

## Last commit

- (update after commit)

## Next session (Phase 1c)

New chat with `@PLAN.md`, `@untilNow.md`.

> Phase **1c** only: `BacktestRun` model, `BacktestRunner` (bar loop, SL/TP rule per PLAN), optional Celery stub, results UI with **win rate %** and equity chart. Wire strategies + `load_m1_bars` / resample. Do **not** start MT5 agent (Phase 3).

## Decisions / notes

- Indicators implemented in pure pandas (no `pandas-ta` yet).
- Catalog bar counts sum CSV line counts (can be slow on first `/data/` load for huge trees; optimize in 1c if needed).
- `TRADEBOT_DATA_ROOT` = `BASE_DIR / "data"` in settings.
