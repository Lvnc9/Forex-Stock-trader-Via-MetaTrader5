"""RuleStrategy runtime — same SignalEngine path as Python strategies."""

from __future__ import annotations

from typing import Any, ClassVar

import pandas as pd
from django.conf import settings

from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext
from apps.strategies.engine import SignalEvent, _CachedIndicatorRegistry
from apps.strategies.indicators.registry import IndicatorRegistry
from apps.strategies.rules.expr import compute_indicators, eval_rule_group, eval_rule_group_mask
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

    def generate_signal_events(
        self,
        bars: pd.DataFrame,
        *,
        htf_bars: pd.DataFrame | None = None,
        warmup: int = 0,
        indicator_cache: dict | None = None,
        htf_indicator_cache: dict | None = None,
    ) -> list[SignalEvent] | None:
        if not bool(getattr(settings, "TRADEBOT_BACKTEST_VECTOR_RULES", True)):
            return None
        if bars.empty:
            return []

        primary_specs = [i for i in self.rule_spec["indicators"] if i.get("source", "primary") != "htf"]
        htf_specs = [i for i in self.rule_spec["indicators"] if i.get("source") == "htf"]
        primary_registry = _CachedIndicatorRegistry(bars, len(bars) - 1, indicator_cache or {})
        computed = compute_indicators(primary_specs, primary_registry, self.parameters)
        htf_index_lookup: dict[pd.Timestamp, int] = {}
        htf_masks: dict[str, pd.Series] = {}
        if htf_specs:
            if htf_bars is None or htf_bars.empty:
                return []
            htf_registry: IndicatorRegistry = _CachedIndicatorRegistry(
                htf_bars,
                len(htf_bars) - 1,
                htf_indicator_cache or {},
            )
            computed.update(compute_indicators(htf_specs, htf_registry, self.parameters))
            htf_masks = {
                "entry_long": eval_rule_group_mask(
                    self.rule_spec["entry_long"],
                    indicators=htf_registry,
                    computed=computed,
                    parameters=self.parameters,
                ),
                "entry_short": eval_rule_group_mask(
                    self.rule_spec["entry_short"],
                    indicators=htf_registry,
                    computed=computed,
                    parameters=self.parameters,
                ),
                "exit_long": eval_rule_group_mask(
                    self.rule_spec["exit_long"],
                    indicators=htf_registry,
                    computed=computed,
                    parameters=self.parameters,
                ),
                "exit_short": eval_rule_group_mask(
                    self.rule_spec["exit_short"],
                    indicators=htf_registry,
                    computed=computed,
                    parameters=self.parameters,
                ),
            }
            htf_index_lookup = {ts: i for i, ts in enumerate(htf_bars.index)}

        masks = {
            "entry_long": eval_rule_group_mask(
                self.rule_spec["entry_long"],
                indicators=primary_registry,
                computed=computed,
                parameters=self.parameters,
            ),
            "entry_short": eval_rule_group_mask(
                self.rule_spec["entry_short"],
                indicators=primary_registry,
                computed=computed,
                parameters=self.parameters,
            ),
            "exit_long": eval_rule_group_mask(
                self.rule_spec["exit_long"],
                indicators=primary_registry,
                computed=computed,
                parameters=self.parameters,
            ),
            "exit_short": eval_rule_group_mask(
                self.rule_spec["exit_short"],
                indicators=primary_registry,
                computed=computed,
                parameters=self.parameters,
            ),
        }

        events: list[SignalEvent] = []
        for i in range(max(0, warmup - 1), len(bars)):
            htf_window = None
            htf_indicators = None
            if htf_specs:
                ts = bars.index[i]
                htf_window = htf_bars.loc[:ts]
                if htf_window.empty:
                    continue
                htf_indicators = _CachedIndicatorRegistry(
                    htf_bars,
                    len(htf_window) - 1,
                    htf_indicator_cache or {},
                )
                htf_i = htf_index_lookup.get(htf_window.index[-1])
                if htf_i is None:
                    continue
                if not any(bool(htf_masks[name].iloc[htf_i]) for name in htf_masks):
                    continue
            if masks["exit_long"].iloc[i] or masks["exit_short"].iloc[i]:
                events.append(
                    SignalEvent(
                        bar_index=i,
                        timestamp=bars.index[i],
                        signal=Signal(SignalAction.EXIT),
                    )
                )
                continue
            ctx = BarContext(
                bar_index=i,
                timestamp=bars.index[i],
                bars=bars.iloc[: i + 1],
                parameters=self.parameters,
                indicators=_CachedIndicatorRegistry(bars, i, indicator_cache or {}),
                htf_bars=htf_window,
                htf_indicators_value=htf_indicators,
            )
            if masks["entry_long"].iloc[i]:
                sl, tp = self._levels("long", ctx)
                events.append(
                    SignalEvent(
                        bar_index=i,
                        timestamp=bars.index[i],
                        signal=Signal(SignalAction.ENTER_LONG, stop_loss=sl, take_profit=tp),
                    )
                )
            elif masks["entry_short"].iloc[i]:
                sl, tp = self._levels("short", ctx)
                events.append(
                    SignalEvent(
                        bar_index=i,
                        timestamp=bars.index[i],
                        signal=Signal(SignalAction.ENTER_SHORT, stop_loss=sl, take_profit=tp),
                    )
                )
        return events

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
