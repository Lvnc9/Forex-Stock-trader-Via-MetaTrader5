from __future__ import annotations

from typing import Any, ClassVar

import pandas as pd

from apps.strategies.context import BarContext
from apps.strategies.signals import Signal


class BaseStrategy:
    """Subclass for library and user strategies (see PLAN.md)."""

    slug: ClassVar[str] = ""
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    module_path: ClassVar[str] = ""

    default_parameters: ClassVar[dict[str, Any]] = {}
    parameter_schema: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, parameters: dict[str, Any] | None = None) -> None:
        merged = {**self.default_parameters, **(parameters or {})}
        self.parameters = self.validate_parameters(merged)

    def validate_parameters(self, parameters: dict[str, Any]) -> dict[str, Any]:
        validated = dict(parameters)
        for spec in self.parameter_schema:
            key = spec["name"]
            if key not in validated:
                if "default" in spec:
                    validated[key] = spec["default"]
                continue
            value = validated[key]
            expected = spec.get("type")
            if expected == "int":
                validated[key] = int(value)
            elif expected == "float":
                validated[key] = float(value)
            if "min" in spec:
                validated[key] = max(spec["min"], validated[key])
            if "max" in spec:
                validated[key] = min(spec["max"], validated[key])
        return validated

    def prepare(
        self,
        bars: pd.DataFrame,
        *,
        htf_bars: pd.DataFrame | None = None,
    ) -> None:
        """Optional one-shot precompute before the bar loop (backtest + batch).

        Pattern strategies (e.g. H&S) should detect once here and look up signals
        in ``on_bar``. Default is a no-op so MA/RSI strategies stay unchanged.
        """

    def on_bar(self, ctx: BarContext) -> Signal | None:
        raise NotImplementedError
