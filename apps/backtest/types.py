from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from apps.backtest.constants import INTRABAR_RULE


@dataclass
class TradeRecord:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    side: str
    entry_price: float
    exit_price: float
    pnl: float
    exit_reason: str


@dataclass
class BacktestResult:
    trades: list[TradeRecord] = field(default_factory=list)
    equity_curve: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    intrabar_rule: str = INTRABAR_RULE


@dataclass
class Position:
    side: str
    entry_price: float
    entry_time: pd.Timestamp
    stop_loss: float | None
    take_profit: float | None
    units: float
