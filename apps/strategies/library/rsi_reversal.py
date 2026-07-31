import pandas as pd

from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext
from apps.strategies.library.exits import SL_TP_DEFAULTS, SL_TP_SCHEMA, levels_from_pct
from apps.strategies.signals import Signal, SignalAction


class RSIReversalStrategy(BaseStrategy):
    slug = "rsi_reversal"
    name = "RSI reversal"
    description = "Mean-reversion entries when RSI leaves oversold/overbought zones."
    module_path = "apps.strategies.library.rsi_reversal"

    default_parameters = {
        "rsi_period": 14,
        "oversold": 30,
        "overbought": 70,
        **SL_TP_DEFAULTS,
    }
    parameter_schema = [
        {"name": "rsi_period", "type": "int", "min": 2, "max": 100, "default": 14},
        {"name": "oversold", "type": "float", "min": 5, "max": 45, "default": 30},
        {"name": "overbought", "type": "float", "min": 55, "max": 95, "default": 70},
        *SL_TP_SCHEMA,
    ]

    def on_bar(self, ctx: BarContext) -> Signal | None:
        period = int(self.parameters["rsi_period"])
        oversold = float(self.parameters["oversold"])
        overbought = float(self.parameters["overbought"])
        sl_pct = float(self.parameters["stop_loss_pct"])
        tp_pct = float(self.parameters["take_profit_pct"])

        rsi = ctx.indicators.rsi(period)
        if len(rsi) < 2:
            return None

        prev, curr = rsi.iloc[-2], rsi.iloc[-1]
        if pd.isna(prev) or pd.isna(curr):
            return None

        if prev <= oversold < curr:
            sl, tp = levels_from_pct(
                ctx.close, is_long=True, stop_loss_pct=sl_pct, take_profit_pct=tp_pct
            )
            return Signal(SignalAction.ENTER_LONG, stop_loss=sl, take_profit=tp)
        if prev >= overbought > curr:
            sl, tp = levels_from_pct(
                ctx.close, is_long=False, stop_loss_pct=sl_pct, take_profit_pct=tp_pct
            )
            return Signal(SignalAction.ENTER_SHORT, stop_loss=sl, take_profit=tp)
        return None
