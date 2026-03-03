#!/usr/bin/env python3
"""Trace THD score values."""
import pandas as pd

df = pd.read_csv('data/level1_hourly_health.csv')

# Check the z_thd column for high thd_drift values
print("Top 5 THD drift with z_thd:")
high_thd = df.nlargest(5, 'thd_drift')
for _, row in high_thd.iterrows():
    print(f"  {row['ahu_id']}: thd_drift={row['thd_drift']:.4f}, z_thd={row.get('z_thd', 'N/A')}")

print("\n" + "="*60)
print("The z_thd column should be much smaller than thd_drift!")
print("If z_thd is around 10-20, then thd_drift > 1 means no clamping")
print("="*60)
