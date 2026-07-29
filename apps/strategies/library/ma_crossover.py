from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext
from apps.strategies.signals import Signal, SignalAction


class MACrossoverStrategy(BaseStrategy):
    slug = "ma_crossover"
    name = "MA crossover"
    description = "Enter long when fast SMA crosses above slow SMA; short on cross below."
    module_path = "apps.strategies.library.ma_crossover"

    default_parameters = {"fast_period": 10, "slow_period": 30}
    parameter_schema = [
        {"name": "fast_period", "type": "int", "min": 2, "max": 200, "default": 10},
        {"name": "slow_period", "type": "int", "min": 3, "max": 400, "default": 30},
    ]

    def on_bar(self, ctx: BarContext) -> Signal | None:
        fast = int(self.parameters["fast_period"])
        slow = int(self.parameters["slow_period"])
        if fast >= slow:
            return None

        ind = ctx.indicators
        fast_sma = ind.sma(fast)
        slow_sma = ind.sma(slow)
        if ind.crossed_above(fast_sma, slow_sma):
            return Signal(SignalAction.ENTER_LONG)
        if ind.crossed_below(fast_sma, slow_sma):
            return Signal(SignalAction.ENTER_SHORT)
        return None
