"""Re-export shared pattern types for backward compatibility."""

import detector._bootstrap  # noqa: F401
from apps.strategies.patterns.head_shoulders.neckline import (  # noqa: F401
    neckline_kind,
    neckline_price_at,
    neckline_slope_norm,
)
