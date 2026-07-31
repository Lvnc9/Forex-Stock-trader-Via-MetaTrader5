"""Library rule-spec templates (customize via builder ?from=slug)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from apps.strategies.rules.schema import validate_spec

RULE_TEMPLATES: dict[str, dict[str, Any]] = {
    "ma_cross_rules": {
        "name": "MA cross (rules)",
        "description": "Fast SMA crosses slow SMA — rule-spec template.",
        "spec": {
            "version": 1,
            "parameters": [
                {"name": "fast_period", "type": "int", "default": 10, "min": 2, "max": 200},
                {"name": "slow_period", "type": "int", "default": 30, "min": 3, "max": 400},
            ],
            "indicators": [
                {
                    "id": "fast",
                    "fn": "sma",
                    "args": {"period": {"ref": "param", "name": "fast_period"}},
                },
                {
                    "id": "slow",
                    "fn": "sma",
                    "args": {"period": {"ref": "param", "name": "slow_period"}},
                },
            ],
            "entry_long": {
                "logic": "and",
                "rules": [
                    {
                        "op": "cross_above",
                        "left": {"ref": "indicator", "id": "fast"},
                        "right": {"ref": "indicator", "id": "slow"},
                    }
                ],
            },
            "entry_short": {
                "logic": "and",
                "rules": [
                    {
                        "op": "cross_below",
                        "left": {"ref": "indicator", "id": "fast"},
                        "right": {"ref": "indicator", "id": "slow"},
                    }
                ],
            },
            "exit_long": {"logic": "and", "rules": []},
            "exit_short": {"logic": "and", "rules": []},
            "stop_loss": {"type": "pct", "value": 1.0},
            "take_profit": {"type": "rr", "ratio": 2.0},
        },
    },
    "rsi_rules": {
        "name": "RSI reversal (rules)",
        "description": "Enter long when RSI crosses up through oversold; short through overbought.",
        "spec": {
            "version": 1,
            "parameters": [
                {"name": "rsi_period", "type": "int", "default": 14, "min": 2, "max": 100},
                {"name": "oversold", "type": "float", "default": 30, "min": 1, "max": 50},
                {"name": "overbought", "type": "float", "default": 70, "min": 50, "max": 99},
            ],
            "indicators": [
                {
                    "id": "rsi",
                    "fn": "rsi",
                    "args": {"period": {"ref": "param", "name": "rsi_period"}},
                }
            ],
            "entry_long": {
                "logic": "and",
                "rules": [
                    {
                        "op": "cross_above",
                        "left": {"ref": "indicator", "id": "rsi"},
                        "right": {"ref": "param", "name": "oversold"},
                    }
                ],
            },
            "entry_short": {
                "logic": "and",
                "rules": [
                    {
                        "op": "cross_below",
                        "left": {"ref": "indicator", "id": "rsi"},
                        "right": {"ref": "param", "name": "overbought"},
                    }
                ],
            },
            "exit_long": {"logic": "and", "rules": []},
            "exit_short": {"logic": "and", "rules": []},
            "stop_loss": {"type": "atr", "mult": 1.5, "period": 14},
            "take_profit": {"type": "rr", "ratio": 2.0},
        },
    },
    "range_breakout_rules": {
        "name": "Range breakout (rules)",
        "description": "Close breaks prior range high/low with optional pct buffer (uses pct_offset).",
        "spec": {
            "version": 1,
            "parameters": [
                {"name": "lookback", "type": "int", "default": 20, "min": 5, "max": 200},
                {"name": "buffer_pct", "type": "float", "default": 0.0, "min": 0.0, "max": 5.0},
            ],
            "indicators": [
                {
                    "id": "range_high",
                    "fn": "sma",
                    "args": {"period": {"ref": "param", "name": "lookback"}, "column": "high"},
                },
                {
                    "id": "range_low",
                    "fn": "sma",
                    "args": {"period": {"ref": "param", "name": "lookback"}, "column": "low"},
                },
            ],
            "entry_long": {
                "logic": "and",
                "rules": [
                    {
                        "op": ">",
                        "left": {"ref": "price", "field": "close"},
                        "right": {
                            "ref": "pct_offset",
                            "base": {"ref": "indicator", "id": "range_high"},
                            "pct": {"ref": "param", "name": "buffer_pct"},
                        },
                    }
                ],
            },
            "entry_short": {
                "logic": "and",
                "rules": [
                    {
                        "op": "<",
                        "left": {"ref": "price", "field": "close"},
                        "right": {
                            "ref": "pct_offset",
                            "base": {"ref": "indicator", "id": "range_low"},
                            "pct": {
                                "ref": "arith",
                                "op": "*",
                                "left": {"ref": "param", "name": "buffer_pct"},
                                "right": {"ref": "value", "value": -1},
                            },
                        },
                    }
                ],
            },
            "exit_long": {"logic": "and", "rules": []},
            "exit_short": {"logic": "and", "rules": []},
            "stop_loss": {"type": "pct", "value": 1.5},
            "take_profit": {"type": "pct", "value": 3.0},
        },
    },
}


def get_template(slug: str) -> dict[str, Any] | None:
    item = RULE_TEMPLATES.get(slug)
    if not item:
        return None
    return {
        "slug": slug,
        "name": item["name"],
        "description": item["description"],
        "spec": validate_spec(deepcopy(item["spec"])),
    }


def list_templates() -> list[dict[str, Any]]:
    return [
        {
            "slug": slug,
            "name": meta["name"],
            "description": meta["description"],
        }
        for slug, meta in RULE_TEMPLATES.items()
    ]
