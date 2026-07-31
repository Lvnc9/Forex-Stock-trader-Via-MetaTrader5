"""Validate and normalize rule strategy specs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from apps.strategies.rules.expr import COMPARE_OPS, INDICATOR_FNS, ExprError

SPEC_VERSION = 1


def empty_spec() -> dict[str, Any]:
    return {
        "version": SPEC_VERSION,
        "parameters": [],
        "indicators": [],
        "entry_long": {"logic": "and", "rules": []},
        "entry_short": {"logic": "and", "rules": []},
        "exit_long": {"logic": "and", "rules": []},
        "exit_short": {"logic": "and", "rules": []},
        "stop_loss": None,
        "take_profit": None,
    }


def validate_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ExprError("Rule spec must be an object")
    out = empty_spec()
    out["version"] = int(spec.get("version") or SPEC_VERSION)

    params = spec.get("parameters") or []
    if not isinstance(params, list):
        raise ExprError("parameters must be a list")
    seen_params: set[str] = set()
    for raw in params:
        if not isinstance(raw, dict) or not raw.get("name"):
            raise ExprError("Each parameter needs a name")
        name = str(raw["name"]).strip()
        if name in seen_params:
            raise ExprError(f"Duplicate parameter: {name}")
        seen_params.add(name)
        ptype = raw.get("type", "float")
        if ptype not in ("int", "float"):
            raise ExprError(f"Bad parameter type for {name}")
        entry = {
            "name": name,
            "type": ptype,
            "default": raw.get("default", 0),
            "label": raw.get("label") or name,
        }
        if "min" in raw:
            entry["min"] = raw["min"]
        if "max" in raw:
            entry["max"] = raw["max"]
        out["parameters"].append(entry)

    indicators = spec.get("indicators") or []
    if not isinstance(indicators, list):
        raise ExprError("indicators must be a list")
    seen_inds: set[str] = set()
    for raw in indicators:
        if not isinstance(raw, dict):
            raise ExprError("Indicator entries must be objects")
        ind_id = str(raw.get("id") or "").strip()
        fn = str(raw.get("fn") or "").strip()
        if not ind_id or not fn:
            raise ExprError("Each indicator needs id and fn")
        if fn not in INDICATOR_FNS:
            raise ExprError(f"Unknown indicator fn: {fn}")
        if ind_id in seen_inds:
            raise ExprError(f"Duplicate indicator id: {ind_id}")
        seen_inds.add(ind_id)
        out["indicators"].append(
            {
                "id": ind_id,
                "fn": fn,
                "args": deepcopy(raw.get("args") or {}),
            }
        )

    for key in ("entry_long", "entry_short", "exit_long", "exit_short"):
        group = spec.get(key) or {"logic": "and", "rules": []}
        if not isinstance(group, dict):
            raise ExprError(f"{key} must be an object")
        logic = (group.get("logic") or "and").lower()
        if logic not in ("and", "or"):
            raise ExprError(f"{key}.logic must be and/or")
        rules = group.get("rules") or []
        if not isinstance(rules, list):
            raise ExprError(f"{key}.rules must be a list")
        cleaned_rules = []
        for rule in rules:
            if not isinstance(rule, dict):
                raise ExprError("Rules must be objects")
            op = rule.get("op")
            if op not in COMPARE_OPS:
                raise ExprError(f"Unsupported rule op: {op}")
            if "left" not in rule or "right" not in rule:
                raise ExprError("Each rule needs left and right")
            cleaned_rules.append(
                {
                    "op": op,
                    "left": deepcopy(rule["left"]),
                    "right": deepcopy(rule["right"]),
                }
            )
        out[key] = {"logic": logic, "rules": cleaned_rules}

    out["stop_loss"] = _validate_stop(spec.get("stop_loss"))
    out["take_profit"] = _validate_tp(spec.get("take_profit"))
    _check_refs(out)
    return out


def _validate_stop(raw: Any) -> dict | None:
    if not raw:
        return None
    if not isinstance(raw, dict):
        raise ExprError("stop_loss must be an object")
    kind = raw.get("type")
    if kind == "pct":
        return {"type": "pct", "value": float(raw.get("value", 1.0))}
    if kind == "atr":
        return {
            "type": "atr",
            "mult": float(raw.get("mult", 1.5)),
            "period": int(raw.get("period", 14)),
        }
    raise ExprError("stop_loss.type must be pct or atr")


def _validate_tp(raw: Any) -> dict | None:
    if not raw:
        return None
    if not isinstance(raw, dict):
        raise ExprError("take_profit must be an object")
    kind = raw.get("type")
    if kind == "pct":
        return {"type": "pct", "value": float(raw.get("value", 2.0))}
    if kind == "rr":
        return {"type": "rr", "ratio": float(raw.get("ratio", 2.0))}
    raise ExprError("take_profit.type must be pct or rr")


def _walk_expr(node: Any, callback) -> None:
    if isinstance(node, dict):
        callback(node)
        for value in node.values():
            _walk_expr(value, callback)
    elif isinstance(node, list):
        for item in node:
            _walk_expr(item, callback)


def _check_refs(spec: dict[str, Any]) -> None:
    param_names = {p["name"] for p in spec["parameters"]}
    ind_ids = {i["id"] for i in spec["indicators"]}

    def check(node: dict) -> None:
        kind = node.get("ref") or node.get("type")
        if kind == "param" and node.get("name") not in param_names:
            raise ExprError(f"Unknown param ref: {node.get('name')}")
        if kind == "indicator" and node.get("id") not in ind_ids:
            raise ExprError(f"Unknown indicator ref: {node.get('id')}")

    for ind in spec["indicators"]:
        _walk_expr(ind.get("args"), check)
    for key in ("entry_long", "entry_short", "exit_long", "exit_short"):
        for rule in spec[key]["rules"]:
            _walk_expr(rule["left"], check)
            _walk_expr(rule["right"], check)
