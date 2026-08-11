"""Load and lightly validate H&S label JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED = [
    "label_id",
    "symbol",
    "timeframe",
    "direction",
    "hard_negative",
    "LS_bar_index",
    "LS_price",
    "trough1_bar_index",
    "trough1_price",
    "head_bar_index",
    "head_price",
    "trough2_bar_index",
    "trough2_price",
    "RS_bar_index",
    "RS_price",
    "neckline_left_bar_index",
    "neckline_left_price",
    "neckline_right_bar_index",
    "neckline_right_price",
    "confirmation_bar_index",
    "confirmation_price",
    "confirm_rule",
    "H",
    "label_quality",
]


def _validate(label: dict[str, Any], source: str) -> None:
    missing = [k for k in REQUIRED if k not in label]
    if missing:
        raise ValueError(f"{source}: missing fields {missing}")
    if label["direction"] not in ("top", "inverse"):
        raise ValueError(f"{source}: bad direction {label['direction']}")
    if label["confirm_rule"] not in ("close_beyond_neckline", "close_beyond_right_armpit"):
        raise ValueError(f"{source}: bad confirm_rule")
    if label["label_quality"] not in ("gold", "silver", "reject"):
        raise ValueError(f"{source}: bad label_quality")
    if label["hard_negative"] and not label.get("hard_negative_reason"):
        raise ValueError(f"{source}: hard_negative requires hard_negative_reason")


def _from_obj(obj: Any, source: str) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        out = []
        for i, item in enumerate(obj):
            if not isinstance(item, dict):
                raise ValueError(f"{source}[{i}]: expected object")
            _validate(item, f"{source}[{i}]")
            out.append(item)
        return out
    if isinstance(obj, dict):
        _validate(obj, source)
        return [obj]
    raise ValueError(f"{source}: expected object or array")


def load_labels(path: Path) -> list[dict[str, Any]]:
    """Load labels from a file or directory of JSON files."""
    if path.is_dir():
        labels: list[dict[str, Any]] = []
        for fp in sorted(path.glob("**/*")):
            if fp.suffix.lower() not in (".json", ".jsonl"):
                continue
            if fp.name == "schema.json":
                continue
            labels.extend(load_labels(fp))
        # de-dupe by label_id (last wins)
        by_id = {lb["label_id"]: lb for lb in labels}
        return list(by_id.values())

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix.lower() == ".jsonl":
        labels = []
        for i, line in enumerate(text.splitlines()):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            labels.extend(_from_obj(obj, f"{path}:{i+1}"))
        return labels
    obj = json.loads(text)
    return _from_obj(obj, str(path))


def expected_entry_bar(label: dict[str, Any], entry_mode: str) -> int | None:
    mode = label.get("entry_mode") or entry_mode
    if label.get("entry_bar_index") is not None:
        return int(label["entry_bar_index"])
    if mode == "B":
        if label.get("retest_bar_index") is not None:
            return int(label["retest_bar_index"])
        return None
    # Mode A default: confirmation
    return int(label["confirmation_bar_index"])
