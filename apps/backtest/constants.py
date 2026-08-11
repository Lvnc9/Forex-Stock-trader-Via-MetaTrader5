"""Backtest intrabar exit rule (see PLAN.md):

If stop-loss and take-profit are both touched within the same bar's OHLC range,
**stop-loss is assumed to trigger first** (conservative).
"""

INTRABAR_RULE = "stop_loss_before_take_profit"

# Equity curve: keep every Nth point (+ first/last) when runs are huge.
EQUITY_CURVE_MAX_POINTS = 2_000

# Default ceiling allows multi-year M1 (~1.4M) / M5 (~275k). Override via settings/env.
MAX_BACKTEST_BARS = 2_000_000

# Soft wall-clock budget for a single execute_backtest (SIGALRM main-thread only).
# 0 = disabled. Long M1 runs need hours; override via TRADEBOT_BACKTEST_TIMEOUT_SECONDS.
BACKTEST_TIMEOUT_SECONDS = 0

# Mark interrupted eager/worker jobs that never finished.
ORPHAN_RUNNING_MINUTES = 120
