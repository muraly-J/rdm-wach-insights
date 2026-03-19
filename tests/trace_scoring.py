#!/usr/bin/env python3
"""Trace scoring path."""
import numpy as np

def sigmoid(x):
    import math
    return 1.0 / (1.0 + math.exp(-x))

def sigmoid_score(raw):
    return float(np.clip(sigmoid(raw) * 2.0 - 1.0, 0.0, 1.0))

def clamp01(x):
    return float(np.clip(x, 0.0, 1.0))

# Trace score_thd_drift from generate_level1_health_scores.py
SENSITIVITY = {"thd_drift": 2.0}
SLOPE_SENS = 3.0
LEVEL_WEIGHT = 0.70

# From CSV: e0111 has thd_drift=4.2995
thd_24h = 97.0  # High THD value
ahu_median_thd = 15.0
rstd = 3.0

# Level term: z-score
z = (thd_24h - ahu_median_thd) / rstd
print(f"z = ({thd_24h} - {ahu_median_thd}) / {rstd} = {z:.4f}")

# Apply sigmoid_score
lv = sigmoid_score(z * SENSITIVITY["thd_drift"])
print(f"lv = sigmoid_score({z} * {SENSITIVITY['thd_drift']}) = {lv:.10f}")

# Trend term
slope_n = 2.5  # arbitrary trend
tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
print(f"tr = sigmoid_score({slope_n} * {SLOPE_SENS}) = {tr:.10f}")

# Combine
score = clamp01(LEVEL_WEIGHT * lv + (1 - LEVEL_WEIGHT) * tr)
print(f"score = clamp01(0.7*{lv:.10f} + 0.3*{tr:.10f}) = {score:.10f}")

print("\n" + "="*60)
print("The score IS clamped correctly to [0,1]")
print("="*60)
