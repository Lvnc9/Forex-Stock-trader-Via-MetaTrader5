"""Load detector export CSV/JSON (Agent 3 contract)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


# Canonical fields — see HANDOFF-agent3.md
DETECTION_FIELDS = [
    "detection_id",
    "symbol",
    "timeframe",
    "direction",
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
    "entry_mode",
    "entry_bar_index",
    "entry_price",
    "H",
    "score",
    "scale",
]


ALIASES = {
    "id": "detection_id",
    "pattern_id": "detection_id",
    "left_shoulder_bar": "LS_bar_index",
    "left_shoulder_price": "LS_price",
    "right_shoulder_bar": "RS_bar_index",
    "right_shoulder_price": "RS_price",
    "left_armpit_bar_index": "trough1_bar_index",
    "left_armpit_price": "trough1_price",
    "right_armpit_bar_index": "trough2_bar_index",
    "right_armpit_price": "trough2_price",
    "confirm_bar_index": "confirmation_bar_index",
    "confirm_price": "confirmation_price",
    "confirm_bar": "confirmation_bar_index",
    "entry_bar": "entry_bar_index",
}


def _norm_key(k: str) -> str:
    k = (k or "").strip()
    return ALIASES.get(k, k)


def _coerce(det: dict[str, Any], source: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in det.items():
        out[_norm_key(str(k))] = v
    for req in ("symbol", "timeframe", "direction", "head_bar_index"):
        if req not in out or out[req] in (None, ""):
            raise ValueError(f"{source}: detection missing {req}")
    if "detection_id" not in out or out["detection_id"] in (None, ""):
        out["detection_id"] = (
            f"{out['symbol']}_{out['timeframe']}_{out['direction']}_h{out['head_bar_index']}"
        )
    # ints
    for ik in (
        "LS_bar_index",
        "trough1_bar_index",
        "head_bar_index",
        "trough2_bar_index",
        "RS_bar_index",
        "neckline_left_bar_index",
        "neckline_right_bar_index",
        "confirmation_bar_index",
        "entry_bar_index",
        "retest_bar_index",
    ):
        if ik in out and out[ik] not in (None, ""):
            out[ik] = int(out[ik])
    for fk in (
        "LS_price",
        "trough1_price",
        "head_price",
        "trough2_price",
        "RS_price",
        "neckline_left_price",
        "neckline_right_price",
        "confirmation_price",
        "entry_price",
        "H",
        "score",
    ):
        if fk in out and out[fk] not in (None, ""):
            out[fk] = float(out[fk])
    out["direction"] = str(out["direction"]).lower()
    if out["direction"] not in ("top", "inverse"):
        raise ValueError(f"{source}: bad direction {out['direction']}")
    return out


def load_detections(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [_coerce(row, f"{path}:{i+2}") for i, row in enumerate(reader)]
    text = path.read_text(encoding="utf-8").strip()
    if path.suffix.lower() == ".jsonl":
        out = []
        for i, line in enumerate(text.splitlines()):
            if not line.strip():
                continue
            out.append(_coerce(json.loads(line), f"{path}:{i+1}"))
        return out
    obj = json.loads(text)
    if isinstance(obj, dict) and "detections" in obj:
        obj = obj["detections"]
    if not isinstance(obj, list):
        raise ValueError(f"{path}: expected list or {{detections: [...]}}")
    return [_coerce(item, f"{path}[{i}]") for i, item in enumerate(obj)]
