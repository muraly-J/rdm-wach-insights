#!/usr/bin/env python3
"""Test edge cases for clamping."""
import numpy as np
import math

def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))

def sigmoid_score(raw):
    return float(np.clip(sigmoid(raw) * 2.0 - 1.0, 0.0, 1.0))

def clamp01(x):
    return float(np.clip(x, 0.0, 1.0))

# Test edge case: what if score is exactly 1.0000000000001 due to floating point?
score = 1.0 + 1e-15
print(f"score = {score}")
print(f"clamp01(score) = {clamp01(score)}")
print(f"round(clamp01(score), 4) = {round(clamp01(score), 4)}")

# What if score is calculated WITHOUT clamping first?
level_score = 1.0
trend_score = 1.0
LEVEL_WEIGHT = 0.70

# Without clamping intermediate values
score_no_clamp = LEVEL_WEIGHT * level_score + (1 - LEVEL_WEIGHT) * trend_score
print(f"\nWithout clamping: {score_no_clamp} -> round = {round(score_no_clamp, 4)}")

# With clamping after combine
score_with_clamp = clamp01(LEVEL_WEIGHT * level_score + (1 - LEVEL_WEIGHT) * trend_score)
print(f"With clamping after combine: {score_with_clamp} -> round = {round(score_with_clamp, 4)}")

# What if sigmoid_score is broken?
print("\n--- Testing sigmoid_score edge cases ---")
for raw in [10, 20, 30, 50]:
    result = sigmoid_score(raw)
    print(f"sigmoid_score({raw}) = {result}")
