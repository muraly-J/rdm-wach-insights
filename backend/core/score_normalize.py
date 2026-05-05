"""Canonical score representation: 0-100, high=good. Convert at API boundary only."""

from __future__ import annotations

import math
from typing import Literal, Optional

Scale = Literal["0-1", "0-100"]
Direction = Literal["high-good", "high-bad"]

_VALID_SCALES = ("0-1", "0-100")
_VALID_DIRECTIONS = ("high-good", "high-bad")


def _check(scale: str, direction: str) -> None:
    if scale not in _VALID_SCALES:
        raise ValueError(f"scale must be one of {_VALID_SCALES}, got {scale!r}")
    if direction not in _VALID_DIRECTIONS:
        raise ValueError(f"direction must be one of {_VALID_DIRECTIONS}, got {direction!r}")


def to_canonical(
    value: Optional[float], *, scale: Scale, direction: Direction
) -> Optional[float]:
    """Convert a raw score to canonical 0-100 high=good. None/NaN passthrough as None."""
    _check(scale, direction)
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if scale == "0-1":
        v = value * 100.0
    else:
        v = float(value)
    if direction == "high-bad":
        v = 100.0 - v
    return max(0.0, min(100.0, v))


def from_canonical(
    value: Optional[float], *, scale: Scale, direction: Direction
) -> Optional[float]:
    """Inverse of to_canonical. Used only for tests/round-trip validation."""
    _check(scale, direction)
    if value is None:
        return None
    v = float(value)
    if direction == "high-bad":
        v = 100.0 - v
    if scale == "0-1":
        v = v / 100.0
    return v