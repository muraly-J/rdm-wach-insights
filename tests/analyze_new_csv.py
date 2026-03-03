#!/usr/bin/env python3
"""Analyze regenerated CSV for edge cases."""
import pandas as pd

df = pd.read_csv('data/level1_hourly_health_24h.csv')

print("=" * 70)
print("EDGE CASE ANALYSIS - Level 1 AHUs (24h CSV)")
print("=" * 70)

# Check score ranges
print("\n--- Score Range Analysis ---")
metrics = ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload']

issues = []
for col in metrics:
    out_of_range = df[(df[col] < 0) | (df[col] > 1)]
    if len(out_of_range) > 0:
        issues.append(col)
        print(f"  {col}: FAIL - {len(out_of_range)} values outside [0,1]")
        print(f"    Min: {out_of_range[col].min():.4f}, Max: {out_of_range[col].max():.4f}")
    else:
        print(f"  {col}: PASS - All values in [0,1] (range: [{df[col].min():.4f}, {df[col].max():.4f}])")

# Check health index ranges
print("\n--- Health Index Analysis ---")
health_invalid_low = df[df['health_index'] < 0]
health_invalid_high = df[df['health_index'] > 100]
print(f"  Health < 0: {len(health_invalid_low)} records")
print(f"  Health > 100: {len(health_invalid_high)} records")

# Check for nonsensical health indices (outside [0,100])
print("\n--- Nonsensical Health Indices ---")
nonsensical = df[(df['health_index'] < 0) | (df['health_index'] > 100)]
if len(nonsensical) > 0:
    print(f"  Found {len(nonsensical)} records with health outside [0,100]")
    print("  Sample:")
    for _, row in nonsensical.head(5).iterrows():
        print(f"    {row['ahu_id']}: health={row['health_index']:.1f}")
else:
    print("  All health indices in valid range [0,100]")

# Check AHUs with highest/lowest health
print("\n--- AHU Rankings ---")
best_5 = df.nlargest(5, 'health_index')
worst_5 = df.nsmallest(5, 'health_index')

print("  Best 5:")
for _, row in best_5.iterrows():
    print(f"    {row['ahu_id']}: health={row['health_index']:.1f}")

print("  Worst 5:")
for _, row in worst_5.iterrows():
    print(f"    {row['ahu_id']}: health={row['health_index']:.1f}")
    
# Check for bimodal patterns in THD
print("\n--- Bimodal THD Detection ---")
for ahu in sorted(df['ahu_id'].unique())[:10]:  # Check first 10
    ahu_data = df[df['ahu_id'] == ahu]
    thd_range = ahu_data['thd_drift'].max() - ahu_data['thd_drift'].min()
    thd_mean = ahu_data['thd_drift'].mean()
    if thd_range > 0.5:
        print(f"  {ahu}: range={thd_range:.4f}, mean={thd_mean:.4f}")
        
print("\n" + "=" * 70)
