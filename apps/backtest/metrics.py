"""Backtest performance metrics."""

from __future__ import annotations

from apps.backtest.types import TradeRecord


def empty_metrics(initial_balance: float) -> dict:
    return {
        "win_rate_pct": 0.0,
        "net_return_pct": 0.0,
        "profit_factor": 0.0,
        "max_drawdown_pct": 0.0,
        "trade_count": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "final_balance": initial_balance,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
    }


def max_drawdown_pct(equity_curve: list[dict], initial_balance: float) -> float:
    if not equity_curve:
        return 0.0
    peak = float(initial_balance)
    max_dd = 0.0
    for point in equity_curve:
        eq = float(point["equity"])
        peak = max(peak, eq)
        if peak > 0:
            dd = (peak - eq) / peak * 100.0
            max_dd = max(max_dd, dd)
    return max_dd


def compute_metrics(
    trades: list[TradeRecord],
    final_balance: float,
    initial_balance: float,
    equity_curve: list[dict],
) -> dict:
    closed = len(trades)
    winners = sum(1 for t in trades if t.pnl > 0)
    losers = sum(1 for t in trades if t.pnl <= 0)
    win_rate = (winners / closed * 100.0) if closed else 0.0
    net_return = (
        ((final_balance - initial_balance) / initial_balance * 100.0) if initial_balance else 0.0
    )

    gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
    gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
    profit_factor = (
        (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
    )

    return {
        "win_rate_pct": round(win_rate, 2),
        "net_return_pct": round(net_return, 2),
        "profit_factor": round(profit_factor, 4),
        "max_drawdown_pct": round(max_drawdown_pct(equity_curve, initial_balance), 2),
        "trade_count": closed,
        "winning_trades": winners,
        "losing_trades": losers,
        "final_balance": round(final_balance, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
    }


def downsample_equity(equity_curve: list[dict], max_points: int) -> list[dict]:
    if max_points <= 0 or len(equity_curve) <= max_points:
        return equity_curve
    step = max(len(equity_curve) // max_points, 1)
    sampled = equity_curve[::step]
    if sampled[-1] is not equity_curve[-1]:
        sampled.append(equity_curve[-1])
    return sampled
