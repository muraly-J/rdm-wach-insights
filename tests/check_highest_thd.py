#!/usr/bin/env python3
"""Check highest THD scores."""
import pandas as pd

df = pd.read_csv('data/level1_hourly_health.csv')

# Check the highest scores
print("Top 5 THD drift values:")
for _, row in df.nlargest(5, 'thd_drift').head(5).iterrows():
    print(f"  {row['ahu_id']}: thd_drift={row['thd_drift']:.4f}, "
          f"health={row['health_index']}")

# Check if scores are clamped in the formula
print("\nFormula check for highest THD row:")
row = df.nlargest(1, 'thd_drift').iloc[0]
print(f"  thd_drift={row['thd_drift']:.4f}")
penalty = (row['energy_anomaly']*0.15 + row['pf_degradation']*0.25 + 
          row['phase_imbalance']*0.25 + row['thd_drift']*0.15 + 
          row['overload']*0.20)
print(f"  penalty={penalty:.4f}")
expected = 100 - penalty*100
print(f"  expected health={expected:.4f}, actual={row['health_index']}")
