#!/usr/bin/env python3
"""
test_all_ahus_edge_cases.py
─────────────────────────────
Comprehensive edge case analysis for ALL 112+ AHUs.

Tests:
1. Bimodal distribution edge cases (all levels)
2. Missing metric handling (all levels)
3. AHUs scoring nonsensically (all levels)
"""

import pandas as pd
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def load_all_csvs():
    """Load all level CSV files."""
    csv_files = [
        ('data/all_levels_health_24h.csv', '24h'),
        ('data/all_levels_health_7d.csv', '7d'),
        ('data/all_levels_health_30d.csv', '30d')
    ]
    
    results = {}
    for csv_path, name in csv_files:
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            results[name] = df
            print(f"  Loaded {csv_path}: {len(df)} rows, {df['ahu_id'].nunique()} AHUs")
        else:
            print(f"  Skip {csv_path}: File not found")
    
    return results

def test_score_ranges_all_levels():
    """Check all scores are in [0,1] range across ALL levels."""
    print("\n" + "=" * 70)
    print("Test: Score Range Validation (ALL Levels)")
    print("=" * 70)
    
    results = load_all_csvs()
    
    all_passed = True
    metrics = ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload']
    
    for name, df in results.items():
        print(f"\n--- {name.upper()} CSV ---")
        
        for col in metrics:
            out_of_range = df[(df[col] < 0) | (df[col] > 1)]
            if len(out_of_range) > 0:
                all_passed = False
                print(f"  {col}: FAIL - {len(out_of_range)} values outside [0,1]")
                print(f"    Min: {out_of_range[col].min():.4f}, Max: {out_of_range[col].max():.4f}")
            else:
                print(f"  {col}: PASS - All values in [0,1]")

    return all_passed

def test_health_index_all_levels():
    """Check health indices are valid across ALL levels."""
    print("\n" + "=" * 70)
    print("Test: Health Index Validation (ALL Levels)")
    print("=" * 70)
    
    results = load_all_csvs()
    all_passed = True
    
    for name, df in results.items():
        print(f"\n--- {name.upper()} ---")
        
        health_invalid_low = df[df['health_index'] < 0]
        health_invalid_high = df[df['health_index'] > 100]
        
        if len(health_invalid_low) > 0 or len(health_invalid_high) > 0:
            all_passed = False
            print(f"  INVALID health indices: {len(health_invalid_low) + len(health_invalid_high)}")
        else:
            print(f"  Health indices: All valid [0,100]")

    return all_passed

def test_missing_metrics_all_levels():
    """Check for missing metrics across ALL levels."""
    print("\n" + "=" * 70)
    print("Test: Missing Metrics (ALL Levels)")
    print("=" * 70)
    
    results = load_all_csvs()
    all_passed = True
    
    metrics = ['health_index', 'energy_anomaly', 'pf_degradation', 
               'phase_imbalance', 'thd_drift', 'overload']
    
    for name, df in results.items():
        print(f"\n--- {name.upper()} ---")
        
        for col in metrics:
            nulls = df[col].isna().sum()
            if nulls > 0:
                all_passed = False
                print(f"  {col}: {nulls} nulls ({100*nulls/len(df):.2f}%)")
            else:
                print(f"  {col}: No nulls")

    return all_passed

def test_nonsensical_scores():
    """Find AHUs with nonsensical scores."""
    print("\n" + "=" * 70)
    print("Test: Nonsensical Scores Detection")
    print("=" * 70)
    
    results = load_all_csvs()
    nonsensical_findings = []
    
    for name, df in results.items():
        print(f"\n--- {name.upper()} ---")
        
        # Check for health < 0 or > 100
        invalid_health = df[(df['health_index'] < 0) | (df['health_index'] > 100)]
        if len(invalid_health) > 0:
            nonsensical_findings.append((name, "health", len(invalid_health)))
            print(f"  Health outside [0,100]: {len(invalid_health)} records")
        
        # Check for scores > 1
        metrics = ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload']
        for col in metrics:
            out_of_range = df[(df[col] < 0) | (df[col] > 1)]
            if len(out_of_range) > 0:
                nonsensical_findings.append((name, col, len(out_of_range)))
                print(f"  {col} outside [0,1]: {len(out_of_range)} records")
        
        # Check for scores < 0
        for col in metrics:
            negative = df[df[col] < 0]
            if len(negative) > 0:
                nonsensical_findings.append((name, f"{col}_negative", len(negative)))
                print(f"  {col} < 0: {len(negative)} records")
    
    if nonsensical_findings:
        print(f"\n  Nonsensical findings: {len(nonsensical_findings)}")
    else:
        print("\n  No nonsensical scores detected!")
    
    return len(nonsensical_findings) == 0

def test_bimodal_thd_all_levels():
    """Detect bimodal THD patterns across ALL levels."""
    print("\n" + "=" * 70)
    print("Test: Bimodal THD Detection (ALL Levels)")
    print("=" * 70)
    
    results = load_all_csvs()
    
    for name, df in results.items():
        print(f"\n--- {name.upper()} ---")
        
        bimodal_count = 0
        for ahu in sorted(df['ahu_id'].unique()):
            ahu_data = df[df['ahu_id'] == ahu]
            thd_range = ahu_data['thd_drift'].max() - ahu_data['thd_drift'].min()
            if thd_range > 0.5:
                bimodal_count += 1
        
        print(f"  AHUs with bimodal THD (range > 0.5): {bimodal_count} of {df['ahu_id'].nunique()}")
    
    return True

def main():
    """Run all edge case tests."""
    print("=" * 70)
    print("EDGE CASE ANALYSIS - ALL AHUs")
    print("=" * 70)

    results = {}
    results['score_ranges'] = test_score_ranges_all_levels()
    results['health_index'] = test_health_index_all_levels()
    results['missing_metrics'] = test_missing_metrics_all_levels()
    results['nonsensical_scores'] = test_nonsensical_scores()
    results['bimodal_thd'] = test_bimodal_thd_all_levels()

    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    all_passed = all(results.values())
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")

    print("\n" + "=" * 70)
    if all_passed:
        print("OVERALL: ALL EDGE CASES HANDLED CORRECTLY")
    else:
        print("OVERALL: SOME EDGE CASES NEED ATTENTION")
    print("=" * 70)

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
