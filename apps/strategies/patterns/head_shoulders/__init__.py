"""Head & shoulders pattern detection (promoted from hs-data/detector)."""

from apps.strategies.patterns.head_shoulders.detect import detect_on_bars
from apps.strategies.patterns.head_shoulders.spec import HSSpec, get_spec, spec_from_parameters
from apps.strategies.patterns.head_shoulders.stops import compute_failure_stops, compute_stops

__all__ = [
    "detect_on_bars",
    "HSSpec",
    "get_spec",
    "spec_from_parameters",
    "compute_stops",
    "compute_failure_stops",
]
