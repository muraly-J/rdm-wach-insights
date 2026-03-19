#!/usr/bin/env python3
"""Debug rounding/clamping issue."""
import numpy as np

def sigmoid_score(raw):
    import math
    sigmoid = lambda x: 1.0 / (1.0 + math.exp(-x))
    return float(np.clip(sigmoid(raw) * 2.0 - 1.0, 0.0, 1.0))

def clamp01(x):
    return float(np.clip(x, 0.0, 1.0))

# Simulate a score that exceeds 1
raw = 35  # Very high z-score
SENSITIVITY_thd = 2.0
score = sigmoid_score(raw * SENSITIVITY_thd)
print(f"sigmoid_score(35*2) = {score}")

# With trend term
tr = sigmoid_score(10 * 3.0)
print(f"trend score (slope_n=10) = {tr}")

# Combine
LEVEL_WEIGHT = 0.70
score_combined = LEVEL_WEIGHT * score + (1 - LEVEL_WEIGHT) * tr
print(f"combined = 0.7*{score:.6f} + 0.3*{tr:.6f} = {score_combined:.6f}")

# After clamp
clamped = clamp01(score_combined)
print(f"after clamp01 = {clamped}")

# After round to 4 decimal places
rounded = round(clamped, 4)
print(f"after round(..., 4) = {rounded}")

# What if we round BEFORE clamping?
rounded_before = round(score_combined, 4)
print(f"round({score_combined:.6f}, 4) = {rounded_before}")
clamped_after_round = clamp01(rounded_before)
print(f"clamp01({rounded_before}) = {clamped_after_round}")

# The issue: round(score, 4) doesn't clamp!
print("\n--- THE BUG ---")
print(f"round(1.02345, 4) = {round(1.02345, 4)}")
print("Rounding does NOT clamp values!")
