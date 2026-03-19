#!/usr/bin/env python3
"""Check all score columns."""
import pandas as pd

df = pd.read_csv('data/level1_hourly_health.csv')

# Check ALL metrics for values > 1
print("Checking all score columns for values outside [0,1]:")
print("="*60)

for col in ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload']:
    out_of_range = df[(df[col] < 0) | (df[col] > 1)]
    if len(out_of_range) > 0:
        print(f"\n{col}: {len(out_of_range)} values outside [0,1]")
        print(f"  Min: {out_of_range[col].min():.4f}, Max: {out_of_range[col].max():.4f}")
        
        # Show a few samples
        for _, row in out_of_range.head(3).iterrows():
            print(f"    {row['ahu_id']}: {col}={row[col]:.4f}, health={row['health_index']}")
    else:
        print(f"\n{col}: OK (all in [0,1])")
