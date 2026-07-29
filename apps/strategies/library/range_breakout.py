from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext
from apps.strategies.signals import Signal, SignalAction


class RangeBreakoutStrategy(BaseStrategy):
    slug = "range_breakout"
    name = "Range breakout"
    description = "Breakout above prior range high (long) or below range low (short)."
    module_path = "apps.strategies.library.range_breakout"

    default_parameters = {"lookback": 20, "buffer_pct": 0.0}
    parameter_schema = [
        {"name": "lookback", "type": "int", "min": 5, "max": 500, "default": 20},
        {"name": "buffer_pct", "type": "float", "min": 0.0, "max": 5.0, "default": 0.0},
    ]

    def on_bar(self, ctx: BarContext) -> Signal | None:
        lookback = int(self.parameters["lookback"])
        buffer_pct = float(self.parameters["buffer_pct"]) / 100.0

        if len(ctx.bars) < lookback + 1:
            return None

        window = ctx.bars.iloc[-(lookback + 1) : -1]
        range_high = float(window["high"].max())
        range_low = float(window["low"].min())
        close = ctx.close

        upper = range_high * (1 + buffer_pct)
        lower = range_low * (1 - buffer_pct)

        if close > upper:
            return Signal(SignalAction.ENTER_LONG)
        if close < lower:
            return Signal(SignalAction.ENTER_SHORT)
        return None
