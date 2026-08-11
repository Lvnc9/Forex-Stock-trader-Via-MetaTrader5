from apps.strategies.library.head_and_shoulders import HeadAndShouldersStrategy
from apps.strategies.library.ma_crossover import MACrossoverStrategy
from apps.strategies.library.range_breakout import RangeBreakoutStrategy
from apps.strategies.library.rsi_reversal import RSIReversalStrategy

LIBRARY_STRATEGIES = [
    MACrossoverStrategy,
    RSIReversalStrategy,
    RangeBreakoutStrategy,
    HeadAndShouldersStrategy,
]

LIBRARY_BY_SLUG = {cls.slug: cls for cls in LIBRARY_STRATEGIES}
