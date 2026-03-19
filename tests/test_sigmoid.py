#!/usr/bin/env python3
"""Test sigmoid score edge cases."""
import numpy as np
import math

def sigmoid(x):
    """Numerically stable logistic sigmoid."""
    return 1.0 / (1.0 + math.exp(-float(np.clip(x, -500, 500))))

def sigmoid_score(raw):
    """Map a raw penalty to [0, 1] where raw = 0 → score = 0."""
    return float(np.clip(sigmoid(raw) * 2.0 - 1.0, 0.0, 1.0))

# Test extreme values
print("Sigmoid score tests:")
for raw in [0, 1, 2, 3, 5, 10, 20, 50, 100]:
    score = sigmoid_score(raw)
    print(f"  raw={raw:6.1f} -> sigmoid_score={score:.6f}")

# Now test what happens with the actual formulas
print("\n--- THD Drift Calculation ---")
# If z = 10 (very high), SENSITIVITY = 2.0
z = 10
raw = z * 2.0  # = 20
score = sigmoid_score(raw)
print(f"z=10, raw=z*SENSITIVITY={raw}, score={score}")

# What about the trend term?
slope_n = 20  # Very high slope
tr = sigmoid_score(max(0.0, slope_n) * 3.0)
print(f"slope_n=20, tr={tr}")

# Combine with LEVEL_WEIGHT = 0.70
score_combined = 0.70 * score + 0.30 * tr
print(f"combined (0.70*score + 0.30*tr) = {score_combined}")
