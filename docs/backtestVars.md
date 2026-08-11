# Backtest variables reference

Reference for **BacktestRun** inputs, persisted outputs, status polling, and the detail-page context.  
Form: `/backtest/new/` · Results: `/backtest/<pk>/`

---

## URLs

| Name | Path | Role |
|------|------|------|
| `backtest:list` | `/backtest/` | Run history |
| `backtest:create` | `/backtest/new/` | Create form (`?strategy=<pk>` pre-fills strategy) |
| `backtest:detail` | `/backtest/<pk>/` | Full results page (progress → KPIs → chart → trades) |
| `backtest:status` | `/backtest/<pk>/status/` | JSON poll while pending/running |
| `backtest:sweep_create` | `/backtest/sweep/` | Parameter sweep enqueue |
| `backtest:compare` | `/backtest/compare/?ids=` | Compare completed runs |

---

## Flow

1. Strategy page **Run backtest →** → `/backtest/new/?strategy=<pk>` (strategy pre-selected).
2. POST creates `BacktestRun` (`status=pending`, progress “Queued”).
3. `enqueue_backtest(run)`:
   - **Eager (default):** runs inline; detail opens already `completed`/`failed`.
   - **Async:** queues Celery; detail shows live progress via HTMX poll of `backtest:status`.
4. Worker loads M1 → resamples → simulates → writes `metrics`, `equity_curve`, `trades`.
5. Browser is on **`/backtest/<pk>/`** for the full run experience.

---

## Async progress (live % bar)

Default `CELERY_TASK_ALWAYS_EAGER=True` finishes before redirect — you see results immediately, **not** a progress bar.

To watch status / % update live:

```bash
export CELERY_TASK_ALWAYS_EAGER=False
redis-server
celery -A config worker -l info --concurrency=4
python manage.py runserver
```

If the detail page stays on **Queued**, Redis or the worker is not running.

### Safety rails

| Guard | Default | Behavior |
|-------|---------|----------|
| `TRADEBOT_MAX_BACKTEST_BARS` | **2_000_000** | Fail if primary bars exceed (covers ~1.4M M1). Set `0` to disable. |
| `TRADEBOT_BACKTEST_TIMEOUT_SECONDS` | **0** (off) | SIGALRM on main thread only; workers ignore |
| `TRADEBOT_ORPHAN_RUNNING_MINUTES` | **120** | Pending/running older than this → `failed` |

```bash
# Example: hard-cap still allows full multi-year M1
export TRADEBOT_MAX_BACKTEST_BARS=2000000
export TRADEBOT_ORPHAN_RUNNING_MINUTES=240
```

Clear stuck runs:

```bash
python manage.py fail_orphaned_backtests --all-stuck
```

Multi-year M1/M5 is supported after H&S `prepare()` (one-shot detect). Prefer Celery async so the UI stays responsive during long runs.
---

## BacktestRun inputs (form fields)

| Field | Type | Default / notes |
|-------|------|-----------------|
| `strategy` | FK → `Strategy` | Required. Pre-filled from `?strategy=`. |
| `catalog_slug` | slug | Dataset under `TRADEBOT_DATA_ROOT/<slug>/`. |
| `timeframe` | str | Primary TF after M1 resample. Default `M5`. |
| `htf_timeframe` | str | Optional HTF. Blank if unused. |
| `start` / `end` | date | Inclusive range. |
| `initial_balance` | decimal | Default `10000`. |
| `spread_pct` | float | Fraction of price (e.g. `0.0002`). |
| `commission` | float | Flat per closed trade. |
| `sizing_mode` | choice | `all_in` \| `fixed_lots`. |
| `lot_size` | float | Used when `fixed_lots`. Default `0.01`. |
| `contract_size` | float | Units per lot. Default `100000`. |
| `parameter_overrides` | JSON | Sweep overrides. Default `{}`. |

Worker-owned: `status`, `progress_pct`, `progress_message`, `metrics`, `equity_curve`, `trades`, `error_message`, `completed_at`.

---

## Outputs after run

### Row fields

| Field | Content |
|-------|---------|
| `status` | `pending` → `running` → `completed` \| `failed` |
| `progress_pct` | 0–100 while running |
| `progress_message` | Human status text |
| `metrics` | Summary dict |
| `equity_curve` | Account-balance series (see below) |
| `trades` | Closed trade list |
| `error_message` | Set when failed |

### `metrics` keys

| Key | Meaning |
|-----|---------|
| `win_rate_pct` | Winning trades / total × 100 |
| `net_return_pct` | (final − initial) / initial × 100 |
| `profit_factor` | gross_profit / gross_loss |
| `max_drawdown_pct` | Peak-to-trough on equity curve |
| `trade_count` | Closed trades |
| `winning_trades` / `losing_trades` | Counts |
| `final_balance` | Ending cash |
| `gross_profit` / `gross_loss` | Sums |
| `bar_count` | Primary bars |
| `primary_label` / `htf_label` | Human TF labels |
| `intrabar_rule` | e.g. `stop_loss_before_take_profit` |
| `primary_timeframe` / `source_timeframe` | Codes (`source` = `M1`) |

### `equity_curve[]` (account balance chart)

```json
[{ "t": "2024-01-02T14:00:00+00:00", "equity": 10012.5 }, ...]
```

| Key | Type | Meaning |
|-----|------|---------|
| `t` | ISO-8601 | Bar time |
| `equity` | float | Mark-to-market account balance |

Detail page downsamples to ≤ ~500 points for Chart.js (“Account balance”).

### `trades[]` keys

| Key | Meaning |
|-----|---------|
| `entry_time` / `exit_time` | ISO timestamps |
| `side` | `long` \| `short` |
| `entry_price` / `exit_price` | Fills |
| `pnl` | Realized PnL |
| `exit_reason` | `stop_loss`, `take_profit`, `signal`, … |

---

## Status JSON (`GET /backtest/<pk>/status/`)

```json
{
  "id": 12,
  "status": "running",
  "progress_pct": 42.5,
  "progress_message": "Simulating",
  "error_message": "",
  "win_rate_pct": null,
  "initial_balance": 10000.0,
  "final_balance": null,
  "done": false
}
```

| Key | Notes |
|-----|-------|
| `done` | `true` when `completed` or `failed` → detail page reloads |
| `final_balance` | From `metrics.final_balance` when available |
| `initial_balance` | From `run.initial_balance` |

---

## Detail page context (`BacktestDetailView`)

| Context var | Source |
|-------------|--------|
| `run` | `BacktestRun` |
| `metrics` | `run.metrics` or `{}` |
| `trade_rows` | `run.trades` or `[]` |
| `equity_chart_json` | Downsampled `equity_curve` as JSON string |
| `final_balance` | `metrics.final_balance` (or `None`) |
| `strategy_params` | Strategy parameters (+ overrides badge) |
| `strategy_edit_url` | Link back to parameters / rule builder / custom edit |
| `celery_eager` | `True` when progress bar will not appear (sync mode) |
| `is_in_progress` | `status` in `pending` \| `running` |

**Page sections:** Strategy identity → Progress (if in progress) → Balance strip → KPIs → Account balance chart → Trades. Failed runs show an error panel instead of KPIs/chart.

---

## Code map

| Piece | Module |
|-------|--------|
| Create form | `apps/backtest/forms.py` |
| Defaults | `apps/backtest/defaults.py` |
| Views | `apps/backtest/views.py` |
| Model | `apps/backtest/models.py` |
| Queue | `apps/backtest/tasks.py` |
| Progress writes | `apps/backtest/progress.py` |
| Execute | `apps/backtest/services.py` → `runner.py` |
| Templates | `templates/backtest/form.html`, `detail.html` |
