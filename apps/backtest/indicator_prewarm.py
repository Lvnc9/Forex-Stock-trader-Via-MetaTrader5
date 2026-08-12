"""Precompute indicator series for long backtests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pandas as pd

from apps.backtest.resources import resolve_worker_budget
from apps.strategies.indicators.registry import IndicatorRegistry


def infer_indicator_requests(strategy, parameters: dict[str, Any]) -> list[tuple]:
    requests: set[tuple] = set()
    for spec in getattr(strategy, "parameter_schema", []):
        if spec.get("type") != "int":
            continue
        name = spec.get("name")
        if not name:
            continue
        value = parameters.get(name, spec.get("default"))
        if value is None:
            continue
        period = int(value)
        if "fast" in name or "slow" in name:
            requests.add(("sma", period, "close"))
            requests.add(("ema", period, "close"))
        if "rsi" in name:
            requests.add(("rsi", period, "close"))
        if "atr" in name:
            requests.add(("atr", period))

    rule_spec = getattr(strategy, "rule_spec", None) or {}
    for spec in rule_spec.get("indicators", []):
        fn = spec.get("fn")
        if not fn:
            continue
        args = dict(spec.get("args") or {})
        resolved = {}
        for key, value in args.items():
            if isinstance(value, dict) and (value.get("ref") or value.get("type")) == "param":
                param_name = value.get("name")
                if param_name in parameters:
                    resolved[key] = parameters[param_name]
            else:
                resolved[key] = value
        column = resolved.get("column", "close")
        if fn in {"sma", "ema", "rsi"}:
            requests.add((fn, int(resolved.get("period", 14)), column))
        elif fn == "atr":
            requests.add(("atr", int(resolved.get("period", 14))))
        elif fn == "macd":
            requests.add(
                ("macd", int(resolved.get("fast", 12)), int(resolved.get("slow", 26)), int(resolved.get("signal", 9)), column)
            )
        elif fn == "bollinger":
            requests.add(
                ("bollinger", int(resolved.get("period", 20)), float(resolved.get("std_dev", 2.0)), column)
            )
    return sorted(requests)


def _compute_request(registry: IndicatorRegistry, request: tuple) -> tuple[tuple, Any]:
    kind = request[0]
    if kind == "sma":
        _, period, column = request
        return ("sma", period, column), registry.sma(period, column)
    if kind == "ema":
        _, period, column = request
        return ("ema", period, column), registry.ema(period, column)
    if kind == "rsi":
        _, period, column = request
        return ("rsi", period, column), registry.rsi(period, column)
    if kind == "atr":
        _, period = request
        return ("atr", period), registry.atr(period)
    if kind == "macd":
        _, fast, slow, signal, column = request
        line, macd_signal, hist = registry.macd(fast, slow, signal, column)
        return ("macd", fast, slow, signal, column), {
            "line": line,
            "signal": macd_signal,
            "hist": hist,
        }
    _, period, std_dev, column = request
    lower, mid, upper = registry.bollinger(period, std_dev, column)
    return ("bollinger", period, std_dev, column), {
        "lower": lower,
        "mid": mid,
        "upper": upper,
    }


def build_indicator_cache(
    bars: pd.DataFrame,
    strategy,
    *,
    parameters: dict[str, Any] | None = None,
) -> dict:
    if bars.empty:
        return {}
    params = dict(parameters or getattr(strategy, "parameters", {}) or {})
    requests = infer_indicator_requests(strategy, params)
    if not requests:
        return {}
    registry = IndicatorRegistry(bars)
    workers = min(resolve_worker_budget()["compute_workers"], len(requests))
    if workers <= 1:
        return dict(_compute_request(registry, req) for req in requests)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pairs = list(pool.map(lambda req: _compute_request(registry, req), requests))
    return dict(pairs)
