"""
Unit tests for FAIR health scoring math utilities.

Tests sigmoid_score, get_health_tier, and calculate_health_index
against documented expected values in the module docstring.
No external I/O — pure math.
"""
import math

import pytest
from core.fair_health_scoring import (
    HEALTH_INDEX_WEIGHTS,
    calculate_health_index,
    get_health_tier,
    sigmoid_score,
)


class TestSigmoidScore:
    def test_zero_input_gives_zero_score(self):
        """A z-score of 0 means 'at own baseline' → no penalty."""
        assert sigmoid_score(0.0) == pytest.approx(0.0, abs=1e-9)

    def test_positive_input_gives_positive_score(self):
        """Above baseline → positive score in (0, 1)."""
        score = sigmoid_score(2.0)
        assert 0.0 < score < 1.0

    def test_documented_value_at_2(self):
        """sigmoid_score(2.0) ≈ 0.76 per module docstring."""
        assert sigmoid_score(2.0) == pytest.approx(0.762, abs=0.005)

    def test_documented_value_at_3(self):
        """sigmoid_score(3.0) ≈ 0.91 per module docstring."""
        assert sigmoid_score(3.0) == pytest.approx(0.905, abs=0.005)

    def test_negative_input_clamped_to_zero(self):
        """Below baseline scores are clamped to 0 (no negative penalties)."""
        assert sigmoid_score(-2.0) == pytest.approx(0.0, abs=1e-9)

    def test_large_positive_clamped_to_one(self):
        """Very large z-scores are clamped at 1.0."""
        assert sigmoid_score(100.0) == pytest.approx(1.0, abs=1e-9)


class TestGetHealthTier:
    @pytest.mark.parametrize("index,expected", [
        (100.0, "Healthy"),
        (80.0,  "Healthy"),
        (79.9,  "Monitor"),
        (60.0,  "Monitor"),
        (59.9,  "Maintenance Soon"),
        (40.0,  "Maintenance Soon"),
        (39.9,  "Critical"),
        (0.0,   "Critical"),
    ])
    def test_tier_boundaries(self, index, expected):
        assert get_health_tier(index) == expected


class TestCalculateHealthIndex:
    def test_all_zero_scores_give_100(self):
        """No penalty at all → perfect health."""
        scores = {k: 0.0 for k in HEALTH_INDEX_WEIGHTS}
        assert calculate_health_index(scores) == pytest.approx(100.0, abs=1e-6)

    def test_all_one_scores_give_zero(self):
        """Maximum penalty on every component → health index 0."""
        scores = {k: 1.0 for k in HEALTH_INDEX_WEIGHTS}
        assert calculate_health_index(scores) == pytest.approx(0.0, abs=1e-6)

    def test_single_component_penalty(self):
        """Only energy_anomaly maxed (weight=0.15) → index = 85."""
        scores = {k: 0.0 for k in HEALTH_INDEX_WEIGHTS}
        scores["energy_anomaly"] = 1.0
        assert calculate_health_index(scores) == pytest.approx(85.0, abs=1e-6)

    def test_weights_sum_to_one(self):
        """Sanity check: HEALTH_INDEX_WEIGHTS sum to exactly 1.0."""
        assert sum(HEALTH_INDEX_WEIGHTS.values()) == pytest.approx(1.0, abs=1e-9)
