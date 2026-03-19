#!/usr/bin/env python3
"""Find out-of-range scores in CSV."""
import pandas as pd

df = pd.read_csv('data/level1_hourly_health.csv')

# Find rows with THD > 1
thd_high = df[df['thd_drift'] > 1]
print(f"Rows with thd_drift > 1: {len(thd_high)}")
print("\nSample THD violations:")
for _, row in thd_high.head(10).iterrows():
    print(f"  {row['ahu_id']}: thd_drift={row['thd_drift']:.4f}, "
          f"health={row['health_index']}, energy_anomaly={row['energy_anomaly']}")

# Find rows with PF > 1
pf_high = df[df['pf_degradation'] > 1]
print(f"\nRows with pf_degradation > 1: {len(pf_high)}")
for _, row in pf_high.head(5).iterrows():
    print(f"  {row['ahu_id']}: pf_degradation={row['pf_degradation']:.4f}")

# Find rows with unbalance > 1
unbal_high = df[df['phase_imbalance'] > 1]
print(f"\nRows with phase_imbalance > 1: {len(unbal_high)}")
for _, row in unbal_high.head(5).iterrows():
    print(f"  {row['ahu_id']}: phase_imbalance={row['phase_imbalance']:.4f}")
