#!/usr/bin/env python3
"""Trace THD issue."""
import pandas as pd

df = pd.read_csv('data/level1_hourly_health.csv')

# Let's trace the exact calculation path for a high THD row
row = df.nlargest(1, 'thd_drift').iloc[0]

print("Analyzing row with thd_drift=4.2995:")
print(f"  ahu_id: {row['ahu_id']}")
print(f"  timestamp: {row['timestamp']}")

# Check the health index calculation
penalty_from_csv = (100 - row['health_index']) / 100
print(f"\nPenalty from health index (100-{row['health_index']})/100 = {penalty_from_csv:.4f}")

print("\n" + "="*60)
print("KEY QUESTION: What formula was used to compute health_index?")
print("="*60)

# The CSV shows health=32.7, so penalty = 0.673
# If all scores were in [0,1], this would be valid
# But if thd_drift=4.2995 is NOT clamped, penalty would be 0.673 + 4*0.15 = 1.27

# Let's check: if penalty = 0.673 and thd_drift was NOT clamped,
# then: energy*0.15 + pf*0.25 + unbal*0.25 + 4.2995*0.15 + overload*0.20 = 0.673
# => energy*0.15 + pf*0.25 + unbal*0.25 + overload*0.20 = 0.673 - 0.645 = 0.028
# This is suspiciously small!

print("\nIf thd_drift=4.2995 was NOT clamped:")
print(f"  contribution = {4.2995 * 0.15:.4f}")
print(f"  remaining for other metrics = {0.673 - 4.2995*0.15:.4f}")

# This means other metrics contribute almost nothing, which suggests:
# 1. Either the health formula is WRONG (doesn't clamp thd_drift)
# 2. Or thd_drift column contains something else

print("\nConclusion:")
print("The health_index=32.7 is calculated assuming thd_drift is clamped to [0,1]")
print("But the stored thd_drift value is 4.2995 (>1)")
print("This means the CSV contains UNCLAMPED scores!")
