"""Rule-strategy expression language (Phase A)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from apps.strategies.indicators.registry import IndicatorRegistry

PRICE_FIELDS = frozenset({"open", "high", "low", "close"})
INDICATOR_FNS = frozenset({"sma", "ema", "rsi", "atr", "macd", "bollinger"})
COMPARE_OPS = frozenset({">", ">=", "<", "<=", "==", "cross_above", "cross_below"})
ARITH_OPS = frozenset({"+", "-", "*", "/"})


class ExprError(ValueError):
    """Invalid expression / rule-spec reference."""


def _require_dict(node: Any, label: str) -> dict:
    if not isinstance(node, dict):
        raise ExprError(f"{label} must be an object")
    return node


def resolve_expr(
    node: Any,
    *,
    indicators: IndicatorRegistry,
    computed: dict[str, pd.Series],
    parameters: dict[str, Any],
) -> float | pd.Series:
    """Resolve an expression node to a scalar or Series."""
    if isinstance(node, (int, float)):
        return float(node)

    node = _require_dict(node, "expression")
    kind = node.get("ref") or node.get("type")
    if not kind:
        raise ExprError(f"Expression missing ref/type: {node}")

    if kind == "value":
        return float(node["value"])

    if kind == "param":
        name = node.get("name")
        if name not in parameters:
            raise ExprError(f"Unknown param ref: {name}")
        return float(parameters[name])

    if kind == "price":
        field = node.get("field", "close")
        if field not in PRICE_FIELDS:
            raise ExprError(f"Unknown price field: {field}")
        return indicators.bars[field]

    if kind == "indicator":
        ind_id = node.get("id")
        if ind_id not in computed:
            raise ExprError(f"Unknown indicator ref: {ind_id}")
        series = computed[ind_id]
        output = node.get("output")
        if output:
            # reserved for multi-output indicators stored as dict of series
            if not isinstance(series, dict) or output not in series:
                raise ExprError(f"Indicator {ind_id} has no output {output}")
            return series[output]
        if isinstance(series, dict):
            raise ExprError(f"Indicator {ind_id} requires output=...")
        return series

    if kind == "pct_offset":
        base = resolve_expr(node["base"], indicators=indicators, computed=computed, parameters=parameters)
        pct = float(resolve_expr(node["pct"], indicators=indicators, computed=computed, parameters=parameters))
        return base * (1.0 + pct / 100.0)

    if kind == "arith":
        op = node.get("op")
        if op not in ARITH_OPS:
            raise ExprError(f"Unsupported arithmetic op: {op}")
        left = resolve_expr(node["left"], indicators=indicators, computed=computed, parameters=parameters)
        right = resolve_expr(node["right"], indicators=indicators, computed=computed, parameters=parameters)
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        return left / right

    raise ExprError(f"Unsupported expression kind: {kind}")


def _as_series(value: float | pd.Series, index: pd.Index) -> pd.Series:
    if isinstance(value, pd.Series):
        return value
    return pd.Series(float(value), index=index)


def eval_compare(
    op: str,
    left: float | pd.Series,
    right: float | pd.Series,
    indicators: IndicatorRegistry,
) -> bool:
    if op in ("cross_above", "cross_below"):
        left_s = _as_series(left, indicators.bars.index)
        right_s = _as_series(right, indicators.bars.index)
        if op == "cross_above":
            return indicators.crossed_above(left_s, right_s)
        return indicators.crossed_below(left_s, right_s)

    left_v = indicators.value(left) if isinstance(left, pd.Series) else float(left)
    right_v = indicators.value(right) if isinstance(right, pd.Series) else float(right)
    if left_v is None or right_v is None:
        return False
    if op == ">":
        return left_v > right_v
    if op == ">=":
        return left_v >= right_v
    if op == "<":
        return left_v < right_v
    if op == "<=":
        return left_v <= right_v
    if op == "==":
        return left_v == right_v
    raise ExprError(f"Unsupported compare op: {op}")


def compute_indicators(
    specs: list[dict],
    indicators: IndicatorRegistry,
    parameters: dict[str, Any],
) -> dict[str, pd.Series | dict[str, pd.Series]]:
    computed: dict[str, pd.Series | dict[str, pd.Series]] = {}
    for spec in specs:
        ind_id = spec.get("id")
        fn = spec.get("fn")
        if not ind_id or not fn:
            raise ExprError("Each indicator needs id and fn")
        if fn not in INDICATOR_FNS:
            raise ExprError(f"Unknown indicator fn: {fn}")
        args = dict(spec.get("args") or {})
        resolved_args: dict[str, Any] = {}
        for key, raw in args.items():
            if isinstance(raw, dict) and (raw.get("ref") or raw.get("type")):
                val = resolve_expr(raw, indicators=indicators, computed=computed, parameters=parameters)
                resolved_args[key] = int(val) if key in {"period", "fast", "slow", "signal"} else float(val)
            else:
                resolved_args[key] = raw

        if fn == "sma":
            computed[ind_id] = indicators.sma(int(resolved_args.get("period", 14)), resolved_args.get("column", "close"))
        elif fn == "ema":
            computed[ind_id] = indicators.ema(int(resolved_args.get("period", 14)), resolved_args.get("column", "close"))
        elif fn == "rsi":
            computed[ind_id] = indicators.rsi(int(resolved_args.get("period", 14)), resolved_args.get("column", "close"))
        elif fn == "atr":
            computed[ind_id] = indicators.atr(int(resolved_args.get("period", 14)))
        elif fn == "macd":
            line, signal, hist = indicators.macd(
                int(resolved_args.get("fast", 12)),
                int(resolved_args.get("slow", 26)),
                int(resolved_args.get("signal", 9)),
                resolved_args.get("column", "close"),
            )
            computed[ind_id] = {"line": line, "signal": signal, "hist": hist}
        elif fn == "bollinger":
            lower, mid, upper = indicators.bollinger(
                int(resolved_args.get("period", 20)),
                float(resolved_args.get("std_dev", 2.0)),
                resolved_args.get("column", "close"),
            )
            computed[ind_id] = {"lower": lower, "mid": mid, "upper": upper}
    return computed


def eval_rule_group(
    group: dict | None,
    *,
    indicators: IndicatorRegistry,
    computed: dict[str, pd.Series | dict[str, pd.Series]],
    parameters: dict[str, Any],
) -> bool:
    if not group:
        return False
    rules = group.get("rules") or []
    if not rules:
        return False
    logic = (group.get("logic") or "and").lower()
    results: list[bool] = []
    for rule in rules:
        op = rule.get("op")
        if op not in COMPARE_OPS:
            raise ExprError(f"Unsupported rule op: {op}")
        left = resolve_expr(rule["left"], indicators=indicators, computed=computed, parameters=parameters)
        right = resolve_expr(rule["right"], indicators=indicators, computed=computed, parameters=parameters)
        results.append(eval_compare(op, left, right, indicators))
    if logic == "or":
        return any(results)
    return all(results)
