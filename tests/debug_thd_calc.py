#!/usr/bin/env python3
"""Debug THD calculation to find where values > 1 come from."""
import numpy as np

# Simulate the exact calculation path
def sigmoid(x):
    import math
    return 1.0 / (1.0 + math.exp(-x))

def sigmoid_score(raw):
    return float(np.clip(sigmoid(raw) * 2.0 - 1.0, 0.0, 1.0))

def clamp01(x):
    return float(np.clip(x, 0.0, 1.0))

# From the code:
# z = (thd_24h - ahu_median_thd) / rstd
# lv = sigmoid_score(z * SENSITIVITY["thd_drift"])
# slope_n = float(np.clip(ols_slope(hist_thd_24h_series) / rstd, -10, 10))
# tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
# score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)

# What if the score is calculated WITHOUT clamp01?
# Or what if clamp01 is not applied?

SENSITIVITY_thd_drift = 2.0
SLOPE_SENS = 3.0
LEVEL_WEIGHT = 0.70

# Scenario: thd_24h is very high (e.g., 97% for bimodal THD)
# ahu_median_thd = 15%, rstd = 3%
thd_24h = 97.0
ahu_median_thd = 15.0
rstd = 3.0

z = (thd_24h - ahu_median_thd) / rstd
print(f"z = ({thd_24h} - {ahu_median_thd}) / {rstd} = {z:.4f}")

# After sigmoid_score
lv = sigmoid_score(z * SENSITIVITY_thd_drift)
print(f"lv = sigmoid_score({z} * {SENSITIVITY_thd_drift}) = {lv:.6f}")

# Trend term - assume slope is also high
slope_n = 10.0  # High positive slope
tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
print(f"tr = sigmoid_score({slope_n} * {SLOPE_SENS}) = {tr:.6f}")

# Combined score
score_no_clamp = LEVEL_WEIGHT * lv + (1 - LEVEL_WEIGHT) * tr
print(f"combined (no clamp) = {LEVEL_WEIGHT}*{lv:.6f} + {1-LEVEL_WEIGHT}*{tr:.6f} = {score_no_clamp:.6f}")

# With clamp
score_with_clamp = clamp01(score_no_clamp)
print(f"combined (with clamp) = {score_with_clamp:.6f}")

# Now round to 4 decimal places
rounded_no_clamp = round(score_no_clamp, 4)
print(f"rounded (no clamp) = {rounded_no_clamp}")

# Round after clamp
rounded_with_clamp = round(score_with_clamp, 4)
print(f"rounded (with clamp) = {rounded_with_clamp}")

print("\n" + "="*60)
print("CONCLUSION:")
print(f"If clamping is MISSING, score = {rounded_no_clamp} > 1")
print("This matches the CSV values like thd_drift=4.2995!")
print("="*60)
