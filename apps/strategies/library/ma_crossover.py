from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext
from apps.strategies.library.exits import SL_TP_DEFAULTS, SL_TP_SCHEMA, levels_from_pct
from apps.strategies.signals import Signal, SignalAction


class MACrossoverStrategy(BaseStrategy):
    slug = "ma_crossover"
    name = "MA crossover"
    description = "Enter long when fast SMA crosses above slow SMA; short on cross below."
    module_path = "apps.strategies.library.ma_crossover"

    default_parameters = {"fast_period": 10, "slow_period": 30, **SL_TP_DEFAULTS}
    parameter_schema = [
        {"name": "fast_period", "type": "int", "min": 2, "max": 200, "default": 10},
        {"name": "slow_period", "type": "int", "min": 3, "max": 400, "default": 30},
        *SL_TP_SCHEMA,
    ]

    def on_bar(self, ctx: BarContext) -> Signal | None:
        fast = int(self.parameters["fast_period"])
        slow = int(self.parameters["slow_period"])
        if fast >= slow:
            return None

        ind = ctx.indicators
        fast_sma = ind.sma(fast)
        slow_sma = ind.sma(slow)
        sl_pct = float(self.parameters["stop_loss_pct"])
        tp_pct = float(self.parameters["take_profit_pct"])
        if ind.crossed_above(fast_sma, slow_sma):
            sl, tp = levels_from_pct(
                ctx.close, is_long=True, stop_loss_pct=sl_pct, take_profit_pct=tp_pct
            )
            return Signal(SignalAction.ENTER_LONG, stop_loss=sl, take_profit=tp)
        if ind.crossed_below(fast_sma, slow_sma):
            sl, tp = levels_from_pct(
                ctx.close, is_long=False, stop_loss_pct=sl_pct, take_profit_pct=tp_pct
            )
            return Signal(SignalAction.ENTER_SHORT, stop_loss=sl, take_profit=tp)
        return None
