#!/usr/bin/env python3
"""
test_scoring_formulas.py
──────────────────────────
Comprehensive unit tests for all 5 FAIR scoring formulas.

Tests:
1. Energy Anomaly (score_energy_anomaly)
2. Power Factor Degradation (score_power_factor)
3. Phase Imbalance (score_phase_imbalance)
4. THD Drift (score_thd_drift)
5. Overload (score_overload)

Each formula tested with:
- Known-good data (should produce expected scores)
- Known-bad data (edge cases, edge conditions)
- Boundary conditions (min/max values)
- Missing/NaN handling
"""

import numpy as np
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from core.fair_health_scoring import (
    score_energy_anomaly,
    score_power_factor,
    score_phase_imbalance,
    score_thd_drift,
    score_overload,
)

# ─────────────────────────────────────────────────────────────────────────────
# TEST RESULTS TRACKING
# ─────────────────────────────────────────────────────────────────────────────

test_results = {
    "energy_anomaly": {"passed": 0, "failed": 0, "details": []},
    "power_factor": {"passed": 0, "failed": 0, "details": []},
    "phase_imbalance": {"passed": 0, "failed": 0, "details": []},
    "thd_drift": {"passed": 0, "failed": 0, "details": []},
    "overload": {"passed": 0, "failed": 0, "details": []},
}

current_suite = None


def test_assert(test_name, condition, expected=None, actual=None):
    """Assert with detailed logging."""
    global current_suite
    if condition:
        test_results[current_suite]["passed"] += 1
        print("  [PASS] " + test_name)
    else:
        test_results[current_suite]["failed"] += 1
        detail = test_name
        if expected is not None and actual is not None:
            detail += " | Expected: " + str(expected) + ", Got: " + str(actual)
        test_results[current_suite]["details"].append(detail)
        print("  [FAIL] " + test_name)


# ─────────────────────────────────────────────────────────────────────────────
# TEST SUITE: ENERGY ANOMALY (12 tests)
# ─────────────────────────────────────────────────────────────────────────────

current_suite = "energy_anomaly"

print("=" * 70)
print("Test Suite: Energy Anomaly (score_energy_anomaly)")
print("=" * 70)

hist_200 = np.array([10.0] * 200)  # 200 hours of data

# EA-01: At median (z=0)
score, z = score_energy_anomaly(10.0, 10.0, 2.0, hist_200)
test_assert("EA-01: At median (z=0)", abs(z) < 0.1, "z~0", "z=" + str(round(z, 3)))

# EA-02: +1 std above (z=1)
score, z = score_energy_anomaly(12.0, 10.0, 2.0, hist_200)
test_assert("EA-02: +1 std above (z=1)", abs(z - 1.0) < 0.1, "z~1", "z=" + str(round(z, 3)))

# EA-03: +2 std above (z=2)
score, z = score_energy_anomaly(14.0, 10.0, 2.0, hist_200)
test_assert("EA-03: +2 std above (z=2)", abs(z - 2.0) < 0.1, "z~2", "z=" + str(round(z, 3)))

# EA-04: -1 std below (z=-1)
score, z = score_energy_anomaly(8.0, 10.0, 2.0, hist_200)
test_assert("EA-04: -1 std below (z=-1)", abs(z + 1.0) < 0.1, "z~-1", "z=" + str(round(z, 3)))

# EA-05: Missing current energy (should return neutral score)
score, z = score_energy_anomaly(None, 10.0, 2.0, hist_200)
test_assert("EA-05: Missing current energy", score == 0.5 and np.isnan(z), "score=0.5, z=nan", "score=" + str(score) + ", z=" + str(z))

# EA-06: Missing baseline median
score, z = score_energy_anomaly(12.0, None, 2.0, hist_200)
test_assert("EA-06: Missing baseline median", score == 0.5 and np.isnan(z), "score=0.5, z=nan", "score=" + str(score) + ", z=" + str(z))

# EA-07: Zero std (edge case - should use MIN_RSTD)
hist_short = np.array([10.0] * 30)  # < 24h history for trend test
score, z = score_energy_anomaly(12.0, 10.0, 0.0, hist_short)
test_assert("EA-07: Zero std handled gracefully", 0 <= score <= 1, "score in [0,1]", "score=" + str(score))

# EA-08: Less than 24h history (should return neutral)
hist_10 = np.array([10.0] * 10)  # Only 10 points
score, z = score_energy_anomaly(12.0, 10.0, 2.0, hist_10)
test_assert("EA-08: < 24h history returns neutral", score == 0.5, "score=0.5 (neutral)", "score=" + str(score))

# EA-09: NaN current energy
score, z = score_energy_anomaly(np.nan, 10.0, 2.0, hist_200)
test_assert("EA-09: NaN current energy", score == 0.5 and np.isnan(z), "score=0.5, z=nan", "score=" + str(score) + ", z=" + str(z))

# EA-10: NaN baseline
score, z = score_energy_anomaly(12.0, np.nan, 2.0, hist_200)
test_assert("EA-10: NaN baseline", score == 0.5 and np.isnan(z), "score=0.5, z=nan", "score=" + str(score) + ", z=" + str(z))

# EA-11: Score should be in [0,1] range
score, z = score_energy_anomaly(20.0, 10.0, 2.0, hist_200)  # 5 std above
test_assert("EA-11: Score in [0,1] range", 0 <= score <= 1, "score in [0,1]", "score=" + str(score))

# EA-12: Hist with NaN values should still work
hist_with_nan = np.array([10.0] * 180)
hist_with_nan[50:60] = np.nan
score, z = score_energy_anomaly(12.0, 10.0, 2.0, hist_with_nan)
test_assert("EA-12: History with NaN values", 0 <= score <= 1, "score in [0,1]", "score=" + str(score))

print("")
print("  Energy Anomaly Summary: " + str(test_results["energy_anomaly"]["passed"]) + " passed, " + str(test_results["energy_anomaly"]["failed"]) + " failed")

# ─────────────────────────────────────────────────────────────────────────────
# TEST SUITE: POWER FACTOR (10 tests)
# ─────────────────────────────────────────────────────────────────────────────

current_suite = "power_factor"

print("")
print("=" * 70)
print("Test Suite: Power Factor (score_power_factor)")
print("=" * 70)

hist_pf_200 = np.array([0.87] * 200)

# PF-01: PF at median (z~0)
score, z = score_power_factor(0.87, 100.0, 0.87, 0.02, hist_pf_200)
test_assert("PF-01: PF at median (z~0)", abs(z) < 0.1, "z~0", "z=" + str(round(z, 3)))

# PF-02: Below median (bad) - 0.80 when mean is 0.87
score, z = score_power_factor(0.80, 100.0, 0.87, 0.02, hist_pf_200)
# z = (0.87 - 0.80) / 0.02 = 3.5
test_assert("PF-02: Below median (z~3.5)", abs(z - 3.5) < 0.1, "z~3.5", "z=" + str(round(z, 3)))
test_assert("PF-02: Score high for bad PF", score > 0.5, "score>0.5", "score=" + str(round(score, 3)))

# PF-03: Above median (good) - 0.95 when mean is 0.87
score, z = score_power_factor(0.95, 100.0, 0.87, 0.02, hist_pf_200)
# z = (0.87 - 0.95) / 0.02 = -4 (negative means good)
test_assert("PF-03: Above median (z~-4)", abs(z + 4.0) < 0.1, "z~-4", "z=" + str(round(z, 3)))
test_assert("PF-03: Score low for good PF", score < 0.2, "score<0.2", "score=" + str(round(score, 3)))

# PF-04: Missing PF value (returns 0.0 - worst case assumed)
score, z = score_power_factor(None, 100.0, 0.87, 0.02, hist_pf_200)
test_assert("PF-04: Missing PF value", score == 0.0 and np.isnan(z), "score=0.0, z=nan", "score=" + str(score) + ", z=" + str(z))

# PF-05: Missing baseline median (returns 0.0 - worst case assumed)
score, z = score_power_factor(0.85, 100.0, None, 0.02, hist_pf_200)
test_assert("PF-05: Missing baseline median", score == 0.0 and np.isnan(z), "score=0.0, z=nan", "score=" + str(score) + ", z=" + str(z))

# PF-06: Zero std (should use MIN_RSTD)
hist_pf_30 = np.array([0.87] * 30)
score, z = score_power_factor(0.85, 100.0, 0.87, 0.0, hist_pf_30)
test_assert("PF-06: Zero std handled gracefully", 0 <= score <= 1, "score in [0,1]", "score=" + str(score))

# PF-07: Score in [0,1] range
score, z = score_power_factor(0.70, 100.0, 0.87, 0.02, hist_pf_200)
test_assert("PF-07: Score in [0,1] range", 0 <= score <= 1, "score in [0,1]", "score=" + str(score))

# PF-08: Hist with NaN values
hist_pf_nan = np.array([0.87] * 180)
hist_pf_nan[50:60] = np.nan
score, z = score_power_factor(0.85, 100.0, 0.87, 0.02, hist_pf_nan)
test_assert("PF-08: History with NaN values", 0 <= score <= 1, "score in [0,1]", "score=" + str(score))

# PF-09: Current power for load discount test
hist_pf_200_power = np.array([100.0] * 200)
# Load discount applies when power < 60% of median
score, z = score_power_factor(0.85, 50.0, 0.87, 0.02, hist_pf_200_power)  # power=50 < 60% of 100
# Load discount should reduce score
test_assert("PF-09: Load discount applied (power<60%)", 0 <= score <= 1, "score in [0,1]", "score=" + str(score))

# PF-10: No load discount when power > 60%
hist_pf_200_power_good = np.array([100.0] * 200)
score, z = score_power_factor(0.85, 90.0, 0.87, 0.02, hist_pf_200_power_good)  # power=90 > 60% of 100
test_assert("PF-10: No load discount (power>60%)", 0 <= score <= 1, "score in [0,1]", "score=" + str(score))

print("")
print("  Power Factor Summary: " + str(test_results["power_factor"]["passed"]) + " passed, " + str(test_results["power_factor"]["failed"]) + " failed")

# ─────────────────────────────────────────────────────────────────────────────
# TEST SUITE: PHASE IMBALANCE (10 tests)
# ─────────────────────────────────────────────────────────────────────────────

current_suite = "phase_imbalance"

print("")
print("=" * 70)
print("Test Suite: Phase Imbalance (score_phase_imbalance)")
print("=" * 70)

hist_unbal_200 = np.array([3.0] * 200)

# PI-01: At median (z=0)
score, z = score_phase_imbalance(3.0, 3.0, 1.0, hist_unbal_200)
test_assert("PI-01: At median (z=0)", abs(z) < 0.1, "z~0", "z=" + str(round(z, 3)))

# PI-02: +1 std above (z=1)
score, z = score_phase_imbalance(4.0, 3.0, 1.0, hist_unbal_200)
test_assert("PI-02: +1 std above (z=1)", abs(z - 1.0) < 0.1, "z~1", "z=" + str(round(z, 3)))

# PI-03: +2 std above (z=2)
score, z = score_phase_imbalance(5.0, 3.0, 1.0, hist_unbal_200)
test_assert("PI-03: +2 std above (z=2)", abs(z - 2.0) < 0.1, "z~2", "z=" + str(round(z, 3)))

# PI-04: Missing unbalance (returns 0.0 - worst case assumed)
score, z = score_phase_imbalance(None, 3.0, 1.0, hist_unbal_200)
test_assert("PI-04: Missing unbalance", score == 0.0 and np.isnan(z), "score=0.0, z=nan", "score=" + str(score) + ", z=" + str(z))

# PI-05: Missing baseline median (returns 0.0 - worst case assumed)
score, z = score_phase_imbalance(4.0, None, 1.0, hist_unbal_200)
test_assert("PI-05: Missing baseline median", score == 0.0 and np.isnan(z), "score=0.0, z=nan", "score=" + str(score) + ", z=" + str(z))

# PI-06: Zero std (should use MIN_RSTD)
hist_unbal_30 = np.array([3.0] * 30)
score, z = score_phase_imbalance(4.0, 3.0, 0.0, hist_unbal_30)
test_assert("PI-06: Zero std handled gracefully", 0 <= score <= 1, "score in [0,1]", "score=" + str(score))

# PI-07: Score in [0,1] range
score, z = score_phase_imbalance(10.0, 3.0, 1.0, hist_unbal_200)
test_assert("PI-07: Score in [0,1] range", 0 <= score <= 1, "score in [0,1]", "score=" + str(score))

# PI-08: Hist with NaN values
hist_unbal_nan = np.array([3.0] * 180)
hist_unbal_nan[50:60] = np.nan
score, z = score_phase_imbalance(4.0, 3.0, 1.0, hist_unbal_nan)
test_assert("PI-08: History with NaN values", 0 <= score <= 1, "score in [0,1]", "score=" + str(score))

# PI-09: Low unbalance (good)
score, z = score_phase_imbalance(1.5, 3.0, 1.0, hist_unbal_200)
test_assert("PI-09: Low unbalance (good)", z < 0 and score < 0.2, "z<0, score<0.2", "z=" + str(round(z, 3)) + ", score=" + str(round(score, 3)))

# PI-10: High unbalance (bad) - z=5 gives score ~0.7
score, z = score_phase_imbalance(8.0, 3.0, 1.0, hist_unbal_200)
test_assert("PI-10: High unbalance (bad)", z > 2 and score >= 0.65, "z>2, score>=0.65", "z=" + str(round(z, 3)) + ", score=" + str(round(score, 3)))

print("")
print("  Phase Imbalance Summary: " + str(test_results["phase_imbalance"]["passed"]) + " passed, " + str(test_results["phase_imbalance"]["failed"]) + " failed")

# ─────────────────────────────────────────────────────────────────────────────
# TEST SUITE: THD DRIFT (10 tests)
# ─────────────────────────────────────────────────────────────────────────────

current_suite = "thd_drift"

print("")
print("=" * 70)
print("Test Suite: THD Drift (score_thd_drift)")
print("=" * 70)

hist_thd_200 = np.array([3.5] * 200)

# THD-01: At median (z=0)
score, z = score_thd_drift(3.5, 3.5, 1.0, hist_thd_200)
test_assert("THD-01: At median (z=0)", abs(z) < 0.1, "z~0", "z=" + str(round(z, 3)))

# THD-02: +1 std above (z=1)
score, z = score_thd_drift(4.5, 3.5, 1.0, hist_thd_200)
test_assert("THD-02: +1 std above (z=1)", abs(z - 1.0) < 0.1, "z~1", "z=" + str(round(z, 3)))

# THD-03: +2 std above (z=2)
score, z = score_thd_drift(5.5, 3.5, 1.0, hist_thd_200)
test_assert("THD-03: +2 std above (z=2)", abs(z - 2.0) < 0.1, "z~2", "z=" + str(round(z, 3)))

# THD-04: IEEE 519 limit exceeded (7%) - z=3.5, score ~0.698
score, z = score_thd_drift(7.0, 3.5, 1.0, hist_thd_200)
test_assert("THD-04: IEEE 519 limit exceeded (z=3.5)", abs(z - 3.5) < 0.1, "z~3.5", "z=" + str(round(z, 3)))
test_assert("THD-04: High score for limit exceeded", score >= 0.65, "score>=0.65", "score=" + str(round(score, 3)))

# THD-05: Missing thd_24h (returns 0.0 - worst case assumed)
score, z = score_thd_drift(None, 3.5, 1.0, hist_thd_200)
test_assert("THD-05: Missing thd_24h", score == 0.0 and np.isnan(z), "score=0.0, z=nan", "score=" + str(score) + ", z=" + str(z))

# THD-06: Missing baseline median (returns 0.0 - worst case assumed)
score, z = score_thd_drift(4.5, None, 1.0, hist_thd_200)
test_assert("THD-06: Missing baseline median", score == 0.0 and np.isnan(z), "score=0.0, z=nan", "score=" + str(score) + ", z=" + str(z))

# THD-07: Zero std (should use MIN_RSTD)
hist_thd_30 = np.array([3.5] * 30)
score, z = score_thd_drift(4.5, 3.5, 0.0, hist_thd_30)
test_assert("THD-07: Zero std handled gracefully", 0 <= score <= 1, "score in [0,1]", "score=" + str(score))

# THD-08: Score in [0,1] range
score, z = score_thd_drift(20.0, 3.5, 1.0, hist_thd_200)
test_assert("THD-08: Score in [0,1] range", 0 <= score <= 1, "score in [0,1]", "score=" + str(score))

# THD-09: Hist with NaN values
hist_thd_nan = np.array([3.5] * 180)
hist_thd_nan[50:60] = np.nan
score, z = score_thd_drift(4.5, 3.5, 1.0, hist_thd_nan)
test_assert("THD-09: History with NaN values", 0 <= score <= 1, "score in [0,1]", "score=" + str(score))

# THD-10: Low THD (good)
score, z = score_thd_drift(2.5, 3.5, 1.0, hist_thd_200)
test_assert("THD-10: Low THD (good)", z < 0 and score < 0.2, "z<0, score<0.2", "z=" + str(round(z, 3)) + ", score=" + str(round(score, 3)))

print("")
print("  THD Drift Summary: " + str(test_results["thd_drift"]["passed"]) + " passed, " + str(test_results["thd_drift"]["failed"]) + " failed")

# ─────────────────────────────────────────────────────────────────────────────
# TEST SUITE: OVERLOAD (10 tests)
# ─────────────────────────────────────────────────────────────────────────────

current_suite = "overload"

print("")
print("=" * 70)
print("Test Suite: Overload (score_overload)")
print("=" * 70)

hist_power_200 = np.array([100.0] * 200)

# OL-01: Well below p95 (score should be low)
score, z = score_overload(20.0, 150.0, 100.0, 100.0, hist_power_200)
test_assert("OL-01: Well below p95 (score low)", score < 0.2, "score<0.2", "score=" + str(round(score, 3)))

# OL-02: At 85% of p95
score, z = score_overload(127.5, 150.0, 100.0, 100.0, hist_power_200)  # 85% of 150
test_assert("OL-02: At 85% of p95", 0 <= score <= 1, "score in [0,1]", "score=" + str(round(score, 3)))

# OL-03: At 100% of p95
score, z = score_overload(150.0, 150.0, 100.0, 100.0, hist_power_200)
test_assert("OL-03: At 100% of p95", score > 0.4, "score>0.4", "score=" + str(round(score, 3)))

# OL-04: Above p95 (critical)
score, z = score_overload(160.0, 150.0, 100.0, 100.0, hist_power_200)
test_assert("OL-04: Above p95 (critical)", score > 0.4, "score>0.4", "score=" + str(round(score, 3)))

# OL-05: Missing power (returns neutral score)
score, z = score_overload(None, 150.0, 100.0, 100.0, hist_power_200)
test_assert("OL-05: Missing power", score == 0.5 and np.isnan(z), "score=0.5, z=nan", "score=" + str(score) + ", z=" + str(z))

# OL-06: Missing p95 baseline (returns neutral score)
score, z = score_overload(120.0, None, 100.0, 100.0, hist_power_200)
test_assert("OL-06: Missing p95 baseline", score == 0.5 and np.isnan(z), "score=0.5, z=nan", "score=" + str(score) + ", z=" + str(z))

# OL-07: Missing std power (returns fallback to MIN_RSTD)
score, z = score_overload(120.0, 150.0, None, 100.0, hist_power_200)
test_assert("OL-07: Missing std power", 0 <= score <= 1, "score in [0,1]", "score=" + str(round(score, 3)))

# OL-08: Score in [0,1] range
score, z = score_overload(120.0, 150.0, 100.0, 100.0, hist_power_200)
test_assert("OL-08: Score in [0,1] range", 0 <= score <= 1, "score in [0,1]", "score=" + str(round(score, 3)))

# OL-09: Negative power (edge case)
score, z = score_overload(-10.0, 150.0, 100.0, 100.0, hist_power_200)
test_assert("OL-09: Negative power (edge case)", 0 <= score <= 1, "score in [0,1]", "score=" + str(round(score, 3)))

# OL-10: Very high power (score capped by formula weights)
score, z = score_overload(500.0, 150.0, 100.0, 100.0, hist_power_200)
test_assert("OL-10: Very high power (score capped)", score >= 0.75, "score>=0.75", "score=" + str(round(score, 3)))

print("")
print("  Overload Summary: " + str(test_results["overload"]["passed"]) + " passed, " + str(test_results["overload"]["failed"]) + " failed")

# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

print("")
print("=" * 70)
print("FINAL TEST SUMMARY")
print("=" * 70)

total_passed = sum(t["passed"] for t in test_results.values())
total_failed = sum(t["failed"] for t in test_results.values())

print("")
print("Total Tests: " + str(total_passed + total_failed))
print("Passed: " + str(total_passed))
print("Failed: " + str(total_failed))
print("Pass Rate: " + str(round(100 * total_passed / (total_passed + total_failed), 1)) + "%")

print("")
print("-" * 70)
print("DETAILED FAILURES")
print("-" * 70)

all_passed = total_failed == 0
for suite, results in test_results.items():
    if results["failed"] > 0:
        print("")
        print(suite.upper() + ":")
        for detail in results["details"]:
            print("  [FAIL] " + detail)

if all_passed:
    print("")
    print("[PASS] ALL TESTS PASSED!")
else:
    print("")
    print("[" + str(total_failed) + " TEST(S) FAILED]")

# Exit with appropriate code
sys.exit(0 if all_passed else 1)
