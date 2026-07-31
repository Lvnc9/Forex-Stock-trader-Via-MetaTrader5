from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext
from apps.strategies.library.exits import SL_TP_DEFAULTS, SL_TP_SCHEMA, levels_from_pct
from apps.strategies.signals import Signal, SignalAction


class RangeBreakoutStrategy(BaseStrategy):
    slug = "range_breakout"
    name = "Range breakout"
    description = "Breakout above prior range high (long) or below range low (short)."
    module_path = "apps.strategies.library.range_breakout"

    default_parameters = {"lookback": 20, "buffer_pct": 0.0, **SL_TP_DEFAULTS}
    parameter_schema = [
        {"name": "lookback", "type": "int", "min": 5, "max": 500, "default": 20},
        {"name": "buffer_pct", "type": "float", "min": 0.0, "max": 5.0, "default": 0.0},
        *SL_TP_SCHEMA,
    ]

    def on_bar(self, ctx: BarContext) -> Signal | None:
        lookback = int(self.parameters["lookback"])
        buffer_pct = float(self.parameters["buffer_pct"]) / 100.0
        sl_pct = float(self.parameters["stop_loss_pct"])
        tp_pct = float(self.parameters["take_profit_pct"])

        if len(ctx.bars) < lookback + 1:
            return None

        window = ctx.bars.iloc[-(lookback + 1) : -1]
        range_high = float(window["high"].max())
        range_low = float(window["low"].min())
        close = ctx.close

        upper = range_high * (1 + buffer_pct)
        lower = range_low * (1 - buffer_pct)

        if close > upper:
            sl, tp = levels_from_pct(
                close, is_long=True, stop_loss_pct=sl_pct, take_profit_pct=tp_pct
            )
            return Signal(SignalAction.ENTER_LONG, stop_loss=sl, take_profit=tp)
        if close < lower:
            sl, tp = levels_from_pct(
                close, is_long=False, stop_loss_pct=sl_pct, take_profit_pct=tp_pct
            )
            return Signal(SignalAction.ENTER_SHORT, stop_loss=sl, take_profit=tp)
        return None
