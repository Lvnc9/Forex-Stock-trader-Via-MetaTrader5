"""RuleStrategy runtime — same SignalEngine path as Python strategies."""

from __future__ import annotations

from typing import Any, ClassVar

from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext
from apps.strategies.rules.expr import compute_indicators, eval_rule_group
from apps.strategies.rules.schema import empty_spec, validate_spec
from apps.strategies.signals import Signal, SignalAction

RULE_SPEC_KEY = "_rule_spec"


class RuleStrategy(BaseStrategy):
    slug = "rule_strategy"
    name = "Rule strategy"
    description = "JSON rule-spec strategy (builder / templates)."
    module_path = "apps.strategies.rules.runtime"

    default_parameters: ClassVar[dict[str, Any]] = {}
    parameter_schema: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, parameters: dict[str, Any] | None = None) -> None:
        raw = dict(parameters or {})
        spec_raw = raw.pop(RULE_SPEC_KEY, None) or empty_spec()
        self.rule_spec = validate_spec(spec_raw)
        self.parameter_schema = [
            {
                "name": p["name"],
                "type": p["type"],
                "default": p.get("default", 0),
                **({k: p[k] for k in ("min", "max") if k in p}),
            }
            for p in self.rule_spec["parameters"]
        ]
        self.default_parameters = {p["name"]: p.get("default", 0) for p in self.rule_spec["parameters"]}
        merged = {**self.default_parameters, **raw}
        self.parameters = self.validate_parameters(merged)

    def on_bar(self, ctx: BarContext) -> Signal | None:
        primary_specs = [i for i in self.rule_spec["indicators"] if i.get("source", "primary") != "htf"]
        htf_specs = [i for i in self.rule_spec["indicators"] if i.get("source") == "htf"]

        computed = compute_indicators(primary_specs, ctx.indicators, self.parameters)
        if htf_specs:
            if ctx.htf_indicators is None:
                # HTF required by spec but unavailable — no trade.
                return None
            computed.update(compute_indicators(htf_specs, ctx.htf_indicators, self.parameters))

        if eval_rule_group(
            self.rule_spec["exit_long"],
            indicators=ctx.indicators,
            computed=computed,
            parameters=self.parameters,
        ) or eval_rule_group(
            self.rule_spec["exit_short"],
            indicators=ctx.indicators,
            computed=computed,
            parameters=self.parameters,
        ):
            return Signal(SignalAction.EXIT)

        if eval_rule_group(
            self.rule_spec["entry_long"],
            indicators=ctx.indicators,
            computed=computed,
            parameters=self.parameters,
        ):
            sl, tp = self._levels("long", ctx)
            return Signal(SignalAction.ENTER_LONG, stop_loss=sl, take_profit=tp)

        if eval_rule_group(
            self.rule_spec["entry_short"],
            indicators=ctx.indicators,
            computed=computed,
            parameters=self.parameters,
        ):
            sl, tp = self._levels("short", ctx)
            return Signal(SignalAction.ENTER_SHORT, stop_loss=sl, take_profit=tp)

        return None

    def _levels(self, side: str, ctx: BarContext) -> tuple[float | None, float | None]:
        entry = ctx.close
        sl_cfg = self.rule_spec.get("stop_loss")
        tp_cfg = self.rule_spec.get("take_profit")
        stop = None
        if sl_cfg:
            if sl_cfg["type"] == "pct":
                pct = float(sl_cfg["value"]) / 100.0
                stop = entry * (1 - pct) if side == "long" else entry * (1 + pct)
            elif sl_cfg["type"] == "atr":
                atr = ctx.indicators.atr(int(sl_cfg.get("period", 14)))
                atr_v = ctx.indicators.value(atr)
                if atr_v is not None:
                    dist = atr_v * float(sl_cfg.get("mult", 1.5))
                    stop = entry - dist if side == "long" else entry + dist

        take = None
        if tp_cfg:
            if tp_cfg["type"] == "pct":
                pct = float(tp_cfg["value"]) / 100.0
                take = entry * (1 + pct) if side == "long" else entry * (1 - pct)
            elif tp_cfg["type"] == "rr" and stop is not None:
                risk = abs(entry - stop)
                ratio = float(tp_cfg.get("ratio", 2.0))
                take = entry + risk * ratio if side == "long" else entry - risk * ratio
        return stop, take
