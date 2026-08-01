"""Backtest intrabar exit rule (see PLAN.md):

If stop-loss and take-profit are both touched within the same bar's OHLC range,
**stop-loss is assumed to trigger first** (conservative).
"""

INTRABAR_RULE = "stop_loss_before_take_profit"

# Equity curve: keep every Nth point (+ first/last) when runs are huge.
EQUITY_CURVE_MAX_POINTS = 2_000
