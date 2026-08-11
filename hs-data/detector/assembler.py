"""Re-export shared pattern types for backward compatibility."""

import detector._bootstrap  # noqa: F401
from apps.strategies.patterns.head_shoulders.assembler import (  # noqa: F401
    PatternCandidate,
    assemble_inverse,
    assemble_top,
    merge_dual_scale,
)
