"""Write detector JSON export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def detections_to_json(detections: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(detections, indent=2) + "\n", encoding="utf-8")
