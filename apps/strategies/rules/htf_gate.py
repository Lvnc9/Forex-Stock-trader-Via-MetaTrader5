"""Helpers for rule-spec / HTF requirements."""

from __future__ import annotations

from typing import Any


def rule_spec_requires_htf(rule_spec: dict[str, Any] | None) -> bool:
    """True when any indicator in the rule_spec uses source=htf."""
    if not rule_spec or not isinstance(rule_spec, dict):
        return False
    for ind in rule_spec.get("indicators") or []:
        if isinstance(ind, dict) and (ind.get("source") or "primary").lower() == "htf":
            return True
    return False


def strategy_requires_htf(strategy) -> bool:
    """True when a Strategy model instance needs HTF bars at runtime."""
    if strategy is None:
        return False
    if rule_spec_requires_htf(getattr(strategy, "rule_spec", None)):
        return True
    # Embedded in parameters (deployed copies / runtime_parameters)
    params = getattr(strategy, "parameters", None) or {}
    if isinstance(params, dict):
        embedded = params.get("_rule_spec")
        if rule_spec_requires_htf(embedded):
            return True
    return False
