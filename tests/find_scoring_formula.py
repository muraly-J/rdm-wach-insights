#!/usr/bin/env python3
"""Find the exact scoring formula used."""
import numpy as np

# The CSV shows thd_drift=4.2995 which is way outside [0,1]
# This means either:
# 1. The score is NOT clamped
# 2. There's a different formula being used

# Let's work backwards from thd_drift=4.2995
thd_drift = 4.2995

# If score = z_score (no sigmoid transformation)
print("If score = raw z-score:")
z = thd_drift
print(f"  z = {z:.4f} (this would explain thd_drift > 1)")

# If score = z_score * sensitivity
print("\nIf score = z-score * SENSITIVITY:")
z = thd_drift / 2.0
print(f"  z = {z:.4f}, SENSITIVITY=2.0")

# If score = z_score * sensitivity + trend
print("\nIf score = (z * SENSITIVITY) + trend:")
# For thd_drift=4.2995, if z*2 = 3.5 and trend=0.8:
z_part = 3.5
trend_part = thd_drift - z_part
print(f"  z*SENSITIVITY = {z_part:.4f}")
print(f"  trend = {trend_part:.4f}")

# The simplest explanation: no sigmoid transformation at all!
print("\n" + "="*60)
print("SIMPLEST EXPLANATION:")
print("The score is stored as raw z-score without sigmoid transform!")
print("thd_drift=4.2995 means z = 4.2995 standard deviations")
print("="*60)

# Verify: if score = z (raw value), and z=4.2995
# Then health_index = 100 - (penalty * 100)
# But the penalty should be in [0,1], so this formula is wrong!
print("\n" + "="*60)
print("ALTERNATIVE: The penalty calculation uses raw scores")
print("Instead of clamped sigmoid scores!")
print("="*60)

# Check what happens if penalty uses unclamped z-scores
import pandas as pd
df = pd.read_csv('data/level1_hourly_health.csv')

row = df.nlargest(1, 'thd_drift').iloc[0]
print(f"\nFor row with thd_drift={row['thd_drift']:.4f}:")
print(f"  energy_anomaly = {row['energy_anomaly']}")
print(f"  pf_degradation = {row['pf_degradation']}")
print(f"  phase_imbalance = {row['phase_imbalance']}")

# If the penalty is calculated with raw scores (not clamped to [0,1]):
penalty = (row['energy_anomaly']*0.15 + row['pf_degradation']*0.25 + 
          row['phase_imbalance']*0.25 + row['thd_drift']*0.15 + 
          row['overload']*0.20)
print(f"  penalty = {penalty:.4f}")
health = 100 - penalty*100
print(f"  health = 100 - {penalty:.4f}*100 = {health:.1f}")
print(f"  actual health in CSV = {row['health_index']}")
