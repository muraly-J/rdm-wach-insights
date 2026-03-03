#!/usr/bin/env python3
"""Verify all CSVs have valid score ranges."""
import pandas as pd

csv_files = [
    ('data/level1_hourly_health_24h.csv', '24h'),
    ('data/level1_hourly_health_7d.csv', '7d'),
    ('data/level1_hourly_health_30d.csv', '30d')
]

all_passed = True

for csv_path, name in csv_files:
    print("=" * 70)
    print(f"Edge Case Analysis - {name} CSV")
    print("=" * 70)
    
    df = pd.read_csv(csv_path)
    
    # Check score ranges
    metrics = ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload']
    
    issues = []
    print("\n--- Score Range Analysis ---")
    for col in metrics:
        out_of_range = df[(df[col] < 0) | (df[col] > 1)]
        if len(out_of_range) > 0:
            issues.append(col)
            print(f"  {col}: FAIL - {len(out_of_range)} values outside [0,1]")
            print(f"    Min: {out_of_range[col].min():.4f}, Max: {out_of_range[col].max():.4f}")
        else:
            print(f"  {col}: PASS - All values in [0,1]")
    
    # Check health index ranges
    print("\n--- Health Index Analysis ---")
    health_invalid_low = df[df['health_index'] < 0]
    health_invalid_high = df[df['health_index'] > 100]
    
    print(f"  Health < 0: {len(health_invalid_low)} records")
    print(f"  Health > 100: {len(health_invalid_high)} records")
    
    nonsensical = df[(df['health_index'] < 0) | (df['health_index'] > 100)]
    if len(nonsensical) > 0:
        print(f"  NONSENSICAL: {len(nonsensical)} records with health outside [0,100]")
        all_passed = False
    else:
        print("  PASS: All health indices in valid range [0,100]")
    
    # AHU count
    print(f"\n--- Summary ---")
    print(f"  Total records: {len(df)}")
    print(f"  AHUs: {df['ahu_id'].nunique()}")
    
    # Bimodal detection
    print("\n--- Bimodal THD Candidates ---")
    bimodal_count = 0
    for ahu in sorted(df['ahu_id'].unique()):
        ahu_data = df[df['ahu_id'] == ahu]
        thd_range = ahu_data['thd_drift'].max() - ahu_data['thd_drift'].min()
        if thd_range > 0.5:
            bimodal_count += 1
    
    print(f"  Found {bimodal_count} AHUs with bimodal THD patterns (range > 0.5)")
    
    if issues:
        print(f"\n  FAIL: {len(issues)} metrics have out-of-range values")
        all_passed = False
    else:
        print(f"\n  PASS: All metrics in valid range [0,1]")

print("\n" + "=" * 70)
if all_passed:
    print("OVERALL: ALL CSVs PASSED VALIDATION")
else:
    print("OVERALL: SOME VALIDATIONS FAILED")
print("=" * 70)
