"""H&S pattern detector — emits exports for hs-data harness."""

from detector.detect import detect_patterns
from detector.export import detections_to_json

__all__ = ["detect_patterns", "detections_to_json"]
