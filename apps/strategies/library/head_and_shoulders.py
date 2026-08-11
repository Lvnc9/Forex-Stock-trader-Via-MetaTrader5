from __future__ import annotations

from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext
from apps.strategies.patterns.bars import bars_from_dataframe
from apps.strategies.patterns.head_shoulders import compute_stops, detect_on_bars, spec_from_parameters
from apps.strategies.signals import Signal, SignalAction


class HeadAndShouldersStrategy(BaseStrategy):
    slug = "head_and_shoulders"
    name = "Head & shoulders"
    description = (
        "Detect head-and-shoulders (top) and inverse patterns; enter on neckline confirmation "
        "with measured-move stop and take profit."
    )
    module_path = "apps.strategies.library.head_and_shoulders"

    default_parameters = {
        "swing_L_short": 3,
        "swing_L_medium": 8,
        "min_score": 60,
        "prior_trend_bars": 50,
        "entry_mode": "A",
        "tp_target": "tp1",
        "tp2_k": 0.51,
        "direction_filter": "both",
    }
    parameter_schema = [
        {"name": "swing_L_short", "type": "int", "min": 2, "max": 12, "default": 3},
        {"name": "swing_L_medium", "type": "int", "min": 4, "max": 24, "default": 8},
        {"name": "min_score", "type": "float", "min": 40, "max": 95, "default": 60},
        {"name": "prior_trend_bars", "type": "int", "min": 10, "max": 200, "default": 50},
        {"name": "entry_mode", "type": "str", "default": "A"},
        {"name": "tp_target", "type": "str", "default": "tp1"},
        {"name": "tp2_k", "type": "float", "min": 0.4, "max": 1.5, "default": 0.51},
        {"name": "direction_filter", "type": "str", "default": "both"},
    ]

    def __init__(self, parameters: dict | None = None) -> None:
        super().__init__(parameters)
        self._traded_heads: set[tuple[str, int]] = set()

    def on_bar(self, ctx: BarContext) -> Signal | None:
        bars = bars_from_dataframe(ctx.bars)
        if len(bars) < 2:
            return None

        spec = spec_from_parameters(self.parameters)
        entry_mode = str(self.parameters.get("entry_mode", "A"))
        direction_filter = str(self.parameters.get("direction_filter", "both"))
        min_score = float(self.parameters.get("min_score", spec.min_score_threshold))
        tp_target = str(self.parameters.get("tp_target", "tp1"))
        tp2_k = float(self.parameters.get("tp2_k", spec.tp2_mult_h))

        detections = detect_on_bars(
            bars,
            symbol="SYMBOL",
            timeframe="TF",
            spec=spec,
            entry_mode=entry_mode,
        )

        current = ctx.bar_index
        for det in detections:
            if det["entry_bar_index"] != current:
                continue
            if float(det["score"]) < min_score:
                continue
            direction = det["direction"]
            if direction_filter == "top" and direction != "top":
                continue
            if direction_filter == "inverse" and direction != "inverse":
                continue

            head_key = (direction, det["head_bar_index"])
            if head_key in self._traded_heads:
                continue
            self._traded_heads.add(head_key)

            stop_loss, take_profit = compute_stops(
                det,
                bars,
                spec,
                tp_target=tp_target,
                tp2_k=tp2_k,
            )
            action = SignalAction.ENTER_SHORT if direction == "top" else SignalAction.ENTER_LONG
            metadata = {
                "pattern": "head_and_shoulders",
                "direction": direction,
                "head_bar_index": det["head_bar_index"],
                "H": det["H"],
                "score": det["score"],
                "confirm_rule": det["confirm_rule"],
                "detection_id": det["detection_id"],
                "entry_mode": det["entry_mode"],
            }
            return Signal(
                action,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata=metadata,
            )

        return None
