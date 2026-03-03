#!/usr/bin/env python3
"""Debug score calculation."""
import pandas as pd
import numpy as np
import math

def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-float(np.clip(x, -500, 500))))

def sigmoid_score(raw):
    """Map raw penalty to [0,1] where raw=0 -> score=0."""
    return float(np.clip(sigmoid(raw) * 2.0 - 1.0, 0.0, 1.0))

def clamp01(x):
    return float(np.clip(x, 0.0, 1.0))

# Test: What raw value would give thd_drift=4.2995?
# score = sigmoid_score(raw) * 0.7 + tr * 0.3
# If score = 4.2995, this is impossible because sigmoid_score and tr are both in [0,1]
# So the stored value must be未经clamped

print("Score calculation analysis:")
print("=" * 60)

# If thd_drift = 4.2995 in the CSV, this means:
# 1. Either the score was never clamped
# 2. Or the value stored is the z-score, not the final score

# Let's work backwards
thd_drift = 4.2995
print(f"\nStored thd_drift value: {thd_drift}")

# If this was supposed to be clamped but wasn't:
print(f"After clamp01: {clamp01(thd_drift)}")

# Check if it's a z-score
z = thd_drift
print(f"If this is a z-score, sigmoid_score(z) = {sigmoid_score(z)}")
print(f"  -> Final score after weights: clamp01(0.7*{sigmoid_score(z)} + 0.3*something)")

# Let's check what raw value would produce thd_drift=1.0 after weights
# score = 0.7 * sigmoid_score(level_raw) + 0.3 * sigmoid_score(trend_raw)
# If both are maxed at 1.0: score = 0.7*1 + 0.3*1 = 1.0
# So maximum possible score is 1.0

print("\nMaximum achievable score:")
level_score = sigmoid_score(20)  # Very high z-score
trend_score = sigmoid_score(20)
max_score = clamp01(0.7 * level_score + 0.3 * trend_score)
print(f"  max_score = 0.7*{level_score:.4f} + 0.3*{trend_score:.4f} = {max_score:.4f}")

# The issue: thd_drift > 1 means the score was not clamped after weights
print("\n" + "=" * 60)
print("ISSUE IDENTIFIED:")
print("The thd_drift values > 1 indicate scores are NOT clamped")
print("after applying LEVEL_WEIGHT + TREND_WEIGHT blend.")
print("=" * 60)
