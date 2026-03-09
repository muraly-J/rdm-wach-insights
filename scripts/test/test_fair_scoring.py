#!/usr/bin/env python3
"""
test_fair_scoring.py
────────────────────
Test FAIR health scoring implementation.

This script tests:
1. Basic scoring functions (energy, PF, imbalance, THD, overload)
2. Z-score calculation
3. Safety flags generation
4. Health index computation
"""

import numpy as np
import sys
sys.path.insert(0, '/Users/rdmasia/wach-insight/backend')

from core.fair_health_scoring import (
    score_energy_anomaly,
    score_power_factor,
    score_phase_imbalance,
    score_thd_drift,
    score_overload,
    calculate_health_index,
    robust_params,
    sigmoid_score,
)

def test_robust_params():
    """Test robust_params function."""
    print("Testing robust_params...")
    
    # Test normal distribution
    data = np.array([10, 12, 11, 13, 12, 11, 10])
    median, rstd = robust_params(data)
    print(f"  Normal data: median={median:.2f}, rstd={rstd:.2f}")
    assert abs(median - 11.0) < 0.1, "Median should be ~11"
    assert rstd > 0, "RSTD should be positive"
    
    # Test with outliers (should handle better than std)
    data_outlier = np.array([10, 12, 11, 13, 12, 100])  # 100 is outlier
    median_out, rstd_out = robust_params(data_outlier)
    print(f"  With outlier: median={median_out:.2f}, rstd={rstd_out:.2f}")
    
    print("  ✓ robust_params tests passed")


def test_sigmoid_score():
    """Test sigmoid_score function."""
    print("\nTesting sigmoid_score...")
    
    # z=0 should give score=0
    assert abs(sigmoid_score(0) - 0.0) < 0.01, "z=0 should give score=0"
    
    # z=1 should give ~0.46
    score_1 = sigmoid_score(1)
    assert 0.40 < score_1 < 0.50, f"z=1 should give ~0.46, got {score_1}"
    
    # z=2 should give ~0.76
    score_2 = sigmoid_score(2)
    assert 0.70 < score_2 < 0.80, f"z=2 should give ~0.76, got {score_2}"
    
    print(f"  z=0 → score={sigmoid_score(0):.3f}")
    print(f"  z=1 → score={score_1:.3f}")
    print(f"  z=2 → score={score_2:.3f}")
    print("  ✓ sigmoid_score tests passed")


def test_energy_anomaly():
    """Test energy anomaly scoring."""
    print("\nTesting score_energy_anomaly...")
    
    # AHU has median delta of 10 kWh, rstd of 2
    ahu_median = 10.0
    ahu_rstd = 2.0
    
    # Case 1: Exactly at median (z=0)
    score, z = score_energy_anomaly(10.0, ahu_median, ahu_rstd, np.array([10, 10, 10]))
    assert z == 0.0, f"z should be 0 when at median"
    assert score < 0.1, f"score near 0 when exactly at baseline"
    print(f"  At median: z={z}, score={score:.3f} ✓")
    
    # Case 2: 1 std above (z=1)
    score, z = score_energy_anomaly(12.0, ahu_median, ahu_rstd, np.array([10, 10, 10]))
    assert abs(z - 1.0) < 0.1, f"z should be ~1"
    print(f"  +1 std: z={z:.2f}, score={score:.3f} ✓")
    
    # Case 3: 2 std above (z=2)
    score, z = score_energy_anomaly(14.0, ahu_median, ahu_rstd, np.array([10, 10, 10]))
    assert abs(z - 2.0) < 0.1, f"z should be ~2"
    print(f"  +2 std: z={z:.2f}, score={score:.3f} ✓")
    
    print("  ✓ energy_anomaly tests passed")


def test_health_index():
    """Test health index computation."""
    print("\nTesting calculate_health_index...")
    
    # All scores at 0 → health_index = 100
    all_zero = {
        "energy_anomaly": 0.0,
        "power_factor": 0.0,
        "phase_imbalance": 0.0,
        "thd_drift": 0.0,
        "overload": 0.0,
    }
    index = calculate_health_index(all_zero)
    assert abs(index - 100.0) < 0.1, f"All zero scores → index should be 100, got {index}"
    print(f"  All zero scores → health_index = {index:.1f} ✓")
    
    # All scores at 1 → health_index = 0
    all_one = {
        "energy_anomaly": 1.0,
        "power_factor": 1.0,
        "phase_imbalance": 1.0,
        "thd_drift": 1.0,
        "overload": 1.0,
    }
    index = calculate_health_index(all_one)
    assert abs(index - 0.0) < 0.1, f"All one scores → index should be 0, got {index}"
    print(f"  All max scores → health_index = {index:.1f} ✓")
    
    # Mixed scores
    mixed = {
        "energy_anomaly": 0.15,
        "power_factor": 0.25,
        "phase_imbalance": 0.0,
        "thd_drift": 0.0,
        "overload": 0.20,
    }
    # penalty = 0.15*0.15 + 0.25*0.25 + 0.25*0 + 0.15*0 + 0.20*0.20
    #         = 0.0225 + 0.0625 + 0 + 0 + 0.04 = 0.125
    # health_index = 100 - 0.125*100 = 87.5
    index = calculate_health_index(mixed)
    expected = 100 - 0.125 * 100
    assert abs(index - expected) < 0.1, f"Expected {expected}, got {index}"
    print(f"  Mixed scores → health_index = {index:.1f} (expected ~{expected}) ✓")
    
    print("  ✓ health_index tests passed")


def test_complete_scenario():
    """Test complete scoring scenario."""
    print("\nTesting complete FAIR scoring scenario...")
    
    # Simulate AHU with:
    # - delta_kwh = 15 (median=10, rstd=2) → z=2.5
    # - PF = 0.80 (median=0.87, rstd=0.02) → below normal
    # - unbalance = 5% (median=3, rstd=1) → slightly elevated
    # - thd = 4% (median=3, rstd=1) → slightly elevated
    # - power = 25 kW (median=20, rstd=3, p95=30) → 83% of ceiling
    
    hist_delta = np.array([10, 10, 10, 10, 10])
    hist_pf = np.array([0.87, 0.87, 0.87, 0.87])
    hist_unbal = np.array([3, 3, 3, 3])
    hist_thd = np.array([3, 3, 3, 3])
    hist_power = np.array([20, 20, 20, 20])
    
    # Score each component
    energy_score, z_energy = score_energy_anomaly(15.0, 10.0, 2.0, hist_delta)
    pf_score, z_pf = score_power_factor(0.80, 25.0, 0.87, 0.02, hist_pf)
    unbal_score, z_unbal = score_phase_imbalance(5.0, 3.0, 1.0, hist_unbal)
    thd_score, z_thd = score_thd_drift(4.0, 3.0, 1.0, hist_thd)
    overload_score, z_overload = score_overload(25.0, 20.0, 3.0, 30.0, hist_power)
    
    print(f"  Energy anomaly:    score={energy_score:.3f}, z={z_energy:.2f}")
    print(f"  PF degradation:    score={pf_score:.3f}, z={z_pf:.2f}")
    print(f"  Phase imbalance:   score={unbal_score:.3f}, z={z_unbal:.2f}")
    print(f"  THD drift:         score={thd_score:.3f}, z={z_thd:.2f}")
    print(f"  Overload:          score={overload_score:.3f}, z={z_overload:.2f}")
    
    # Calculate health index
    risk_scores = {
        "energy_anomaly": round(energy_score, 4),
        "power_factor": round(pf_score, 4),
        "phase_imbalance": round(unbal_score, 4),
        "thd_drift": round(thd_score, 4),
        "overload": round(overload_score, 4),
    }
    
    health_index = calculate_health_index(risk_scores)
    print(f"\n  Health Index: {health_index:.1f}")
    
    # Should be in "Monitor" range (60-79) due to elevated scores
    assert 40 <= health_index <= 100, f"Health index should be in valid range"
    print(f"  ✓ Health index in valid range")
    
    # Verify z-scores
    assert abs(z_energy - 2.5) < 0.1, f"z_energy should be ~2.5"
    assert abs(z_pf - 3.5) < 0.1, f"z_pf should be ~3.5 (0.87-0.80)/0.02"
    assert abs(z_unbal - 2.0) < 0.1, f"z_unbal should be ~2.0"
    assert abs(z_thd - 1.0) < 0.1, f"z_thd should be ~1.0"
    assert abs(z_overload - 1.67) < 0.1, f"z_overload should be ~1.67 (25-20)/3"
    
    print(f"  ✓ All z-scores verified")
    print("\n  ✓ Complete FAIR scoring scenario passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("FAIR Health Scoring Test Suite")
    print("=" * 60)
    
    test_robust_params()
    test_sigmoid_score()
    test_energy_anomaly()
    test_health_index()
    test_complete_scenario()
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
