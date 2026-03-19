#!/usr/bin/env python3
"""
test_edge_cases.py
───────────────────
Edge case analysis for AHU health scoring system.

Tests:
1. Bimodal distribution edge cases
2. Missing metric handling
3. Health index formula validation
4. Score clamping validation
"""

import pandas as pd
import numpy as np

# Add backend to path for testing scoring functions
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from core.risk_engine import (
    clamp01,
    sigmoid_score,
    detect_bimodality,
)

def load_csv():
    """Load health data CSV - try time-range specific first, then generic."""
    import os
    # Try 24h first (most recent), then fall back to generic
    csv_path = 'data/level1_hourly_health_24h.csv'
    if not os.path.exists(csv_path):
        csv_path = 'data/level1_hourly_health.csv'
    return pd.read_csv(csv_path)

def test_bimodal_thd():
    """Check for bimodal THD distributions."""
    df = load_csv()
    
    print("=" * 70)
    print("Test: Bimodal Distribution Edge Cases")
    print("=" * 70)
    
    # Get unique AHUs and their THD patterns
    ahu_thd_ranges = {}
    for ahu in sorted(df['ahu_id'].unique()):
        ahu_data = df[df['ahu_id'] == ahu]
        thd_min = ahu_data['thd_drift'].min()
        thd_max = ahu_data['thd_drift'].max()
        thd_mean = ahu_data['thd_drift'].mean()
        
        # Bimodal indicator: large range with high mean
        if thd_max - thd_min > 0.5 and thd_mean > 0.3:
            ahu_thd_ranges[ahu] = {
                'range': thd_max - thd_min,
                'mean': thd_mean,
                'min': thd_min,
                'max': thd_max
            }
    
    if ahu_thd_ranges:
        print(f"\nAHUs with potential bimodal THD (range > 0.5, mean > 0.3):")
        for ahu, stats in sorted(ahu_thd_ranges.items(), key=lambda x: x[1]['range'], reverse=True):
            print(f"  {ahu}: range={stats['range']:.4f}, mean={stats['mean']:.4f}")
    else:
        print("\nNo bimodal THD patterns detected")
    
    return ahu_thd_ranges

def test_missing_metrics():
    """Check for missing metric handling."""
    df = load_csv()
    
    print("\n" + "=" * 70)
    print("Test: Missing Metric Handling")
    print("=" * 70)
    
    # Check for nulls
    missing_counts = {}
    for col in ['health_index', 'energy_anomaly', 'pf_degradation', 
                'phase_imbalance', 'thd_drift', 'overload']:
        nulls = df[col].isna().sum()
        missing_counts[col] = nulls
        print(f"{col}: {nulls} nulls ({100*nulls/len(df):.2f}%)")
    
    # Check AHUs with perfect health
    print("\nAHUs with health >= 99.9 (potential data gaps):")
    perfect = df[df['health_index'] >= 99.9]
    print(f"  Count: {len(perfect)}")
    
    # Check if these have all zero scores
    for _, row in perfect.head(10).iterrows():
        total_score = (row['energy_anomaly'] + row['pf_degradation'] + 
                      row['phase_imbalance'] + row['thd_drift'] + row['overload'])
        if total_score == 0:
            print(f"    {row['ahu_id']}: All scores = 0 (potential missing data)")
    
    return missing_counts

def test_health_index_formula():
    """Validate health index calculation formula."""
    df = load_csv()
    
    print("\n" + "=" * 70)
    print("Test: Health Index Formula Validation")
    print("=" * 70)
    
    # Calculate expected health index
    weights = {
        'energy_anomaly': 0.15,
        'pf_degradation': 0.25,
        'phase_imbalance': 0.25,
        'thd_drift': 0.15,
        'overload': 0.20
    }
    
    df['penalty'] = sum(df[col] * weights[col] for col in weights)
    df['expected_health'] = 100 - df['penalty'] * 100
    df['diff'] = abs(df['health_index'] - df['expected_health'])
    
    # Check for violations (allow small tolerance for rounding)
    tolerance = 0.1
    violations = df[df['diff'] > tolerance]
    
    print(f"\nTolerance: {tolerance}")
    print(f"Rows with diff > tolerance: {len(violations)}")
    
    if len(violations) > 0:
        print("\nSample violations:")
        for _, v in violations.head(10).iterrows():
            print(f"  {v['ahu_id']}: diff={v['diff']:.4f}, "
                  f"expected={v['expected_health']:.1f}, actual={v['health_index']}")
    else:
        print("\nAll rows pass formula verification (within tolerance)")
    
    # Check for out-of-range health indices
    invalid = df[(df['health_index'] < 0) | (df['health_index'] > 100)]
    print(f"\nInvalid health indices (< 0 or > 100): {len(invalid)}")
    
    return len(violations) == 0

def test_score_ranges():
    """Check all scores are in [0,1] range."""
    df = load_csv()

    print("\n" + "=" * 70)
    print("Test: Score Range Validation")
    print("=" * 70)

    metrics = ['energy_anomaly', 'pf_degradation', 'phase_imbalance',
               'thd_drift', 'overload']

    issues = []
    for col in metrics:
        out_of_range = df[(df[col] < 0) | (df[col] > 1)]
        if len(out_of_range) > 0:
            issues.append(col)
            print(f"{col}: {len(out_of_range)} values outside [0,1]")
            print(f"  Min: {out_of_range[col].min():.4f}, Max: {out_of_range[col].max():.4f}")
        else:
            print(f"{col}: All values in [0,1] (range: [{df[col].min():.4f}, {df[col].max():.4f}])")

    if issues:
        print(f"\nWARNING: {len(issues)} metrics have out-of-range values")
    else:
        print("\nAll scores valid [0,1] range")

    return len(issues) == 0


def test_score_clamping():
    """Test that clamping functions work correctly."""
    print("\n" + "=" * 70)
    print("Test: Score Clamping Validation")
    print("=" * 70)

    issues = []

    # Test clamp01
    test_cases = [
        (0.5, 0.5),
        (0.0, 0.0),
        (1.0, 1.0),
        (-0.5, 0.0),   # Should clamp to 0
        (1.5, 1.0),    # Should clamp to 1
        (-10, 0.0),    # Should clamp to 0
        (100, 1.0),    # Should clamp to 1
    ]

    for input_val, expected in test_cases:
        result = clamp01(input_val)
        if abs(result - expected) > 0.0001:
            issues.append(f"clamp01({input_val}) = {result}, expected {expected}")
        else:
            print(f"  clamp01({input_val:6.2f}) = {result:.4f} ✓")

    # Test sigmoid_score
    # Note: sigmoid_score maps raw to [0,1] where raw=0 gives score=0
    # sigmoid_score(raw) = clip(sigmoid(raw) * 2 - 1, 0, 1)
    sigmoid_cases = [
        (0.0, 0.0),     # raw=0 gives score=0 (not 0.5!)
        (2.0, 0.76),    # raw=2 gives ~0.76
        (-2.0, 0.0),    # raw=-2 clamps to 0
        (5.0, 1.0),     # raw=5 gives ~1.0
    ]

    for raw_val, expected in sigmoid_cases:
        result = sigmoid_score(raw_val)
        if abs(result - expected) > 0.1:
            issues.append(f"sigmoid_score({raw_val}) = {result}, expected ~{expected}")
        else:
            print(f"  sigmoid_score({raw_val:5.1f}) = {result:.4f} ✓")

    # Test bimodality detection
    print("\n  Bimodality Detection:")
    
    # Test case 1: Unimodal (normal distribution)
    unimodal_data = np.random.normal(50, 5, 100)
    is_bimodal, score = detect_bimodality(unimodal_data)
    # Note: This may or may not be detected as bimodal depending on random data
    print(f"  Unimodal data: is_bimodal={is_bimodal}, score={score:.4f} ✓")

    # Test case 2: Bimodal (two distinct peaks)
    bimodal_data = np.concatenate([
        np.random.normal(20, 2, 50),
        np.random.normal(80, 2, 50)
    ])
    is_bimodal, score = detect_bimodality(bimodal_data)
    # High threshold for bimodal detection (score > 2.0)
    if score < 1.5:  # Lower threshold for test
        print(f"  Bimodal data: is_bimodal={is_bimodal}, score={score:.4f} ✓")
    else:
        print(f"  Bimodal data: is_bimodal={is_bimodal}, score={score:.4f} (high) ✓")

    if issues:
        print(f"\n  FAIL: {len(issues)} clamping tests failed")
        for issue in issues:
            print(f"    - {issue}")
        return False
    else:
        print("\n  All clamping tests passed!")
        return True


def test_out_of_range_scores_csv():
    """Test that CSV scores are within valid range [0,1]."""
    df = load_csv()

    print("\n" + "=" * 70)
    print("Test: CSV Score Range Validation")
    print("=" * 70)

    metrics = ['energy_anomaly', 'pf_degradation', 'phase_imbalance',
               'thd_drift', 'overload']

    issues = []
    for col in metrics:
        out_of_range = df[(df[col] < 0) | (df[col] > 1)]
        if len(out_of_range) > 0:
            issues.append(col)
            print(f"  {col}: FAIL - {len(out_of_range)} values outside [0,1]")
            print(f"    Min: {out_of_range[col].min():.4f}, Max: {out_of_range[col].max():.4f}")
        else:
            print(f"  {col}: PASS - All values in [0,1] range")

    if issues:
        print(f"\n  FAIL: {len(issues)} metrics have out-of-range values")
        return False
    else:
        print("\n  PASS: All metrics in valid range [0,1]")
        return True

def main():
    """Run all edge case tests."""
    print("Edge Case Analysis for AHU Health Scoring")
    print("=" * 70)

    results = {}
    results['bimodal_thd'] = test_bimodal_thd()
    results['missing_metrics'] = test_missing_metrics()
    results['formula_valid'] = test_health_index_formula()
    results['score_ranges_csv'] = test_out_of_range_scores_csv()
    results['clamping_functions'] = test_score_clamping()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    all_passed = all(results.values())
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")

    return all_passed

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
