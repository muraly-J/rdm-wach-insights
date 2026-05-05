import math

import pytest

from backend.core.score_normalize import to_canonical, from_canonical


class TestToCanonical:
    def test_zero_to_one_scale_high_good_passthrough(self):
        assert to_canonical(0.0, scale="0-1", direction="high-good") == 0.0
        assert to_canonical(1.0, scale="0-1", direction="high-good") == 100.0
        assert to_canonical(0.5, scale="0-1", direction="high-good") == 50.0

    def test_zero_to_one_scale_high_bad_inverts(self):
        assert to_canonical(0.0, scale="0-1", direction="high-bad") == 100.0
        assert to_canonical(1.0, scale="0-1", direction="high-bad") == 0.0
        assert to_canonical(0.25, scale="0-1", direction="high-bad") == 75.0

    def test_zero_to_hundred_high_good_passthrough(self):
        assert to_canonical(73.0, scale="0-100", direction="high-good") == 73.0

    def test_zero_to_hundred_high_bad_inverts(self):
        assert to_canonical(73.0, scale="0-100", direction="high-bad") == 27.0

    def test_clamps_above_range(self):
        assert to_canonical(1.5, scale="0-1", direction="high-good") == 100.0
        assert to_canonical(150.0, scale="0-100", direction="high-good") == 100.0

    def test_clamps_below_range(self):
        assert to_canonical(-0.2, scale="0-1", direction="high-good") == 0.0
        assert to_canonical(-5.0, scale="0-100", direction="high-good") == 0.0

    def test_none_returns_none(self):
        assert to_canonical(None, scale="0-1", direction="high-good") is None

    def test_nan_returns_none(self):
        assert to_canonical(float("nan"), scale="0-1", direction="high-good") is None

    def test_invalid_scale_raises(self):
        with pytest.raises(ValueError):
            to_canonical(0.5, scale="0-10", direction="high-good")

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError):
            to_canonical(0.5, scale="0-1", direction="up")


class TestFromCanonical:
    def test_round_trip_zero_to_one_high_good(self):
        for v in [0.0, 0.25, 0.5, 0.75, 1.0]:
            canonical = to_canonical(v, scale="0-1", direction="high-good")
            assert math.isclose(
                from_canonical(canonical, scale="0-1", direction="high-good"), v, abs_tol=1e-9
            )