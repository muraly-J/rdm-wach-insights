# Engineering Thresholds Documentation

**Date**: 2026-03-05  
**System**: WACH Insight - AHU Health Scoring Engine  
**Version**: Stage 2B (FAIR Method)

---

## Table of Contents

1. [Overview](#overview)
2. [Health Index Structure](#health-index-structure)
3. [Scoring Parameters](#scoring-parameters)
4. [Health Tier Thresholds](#health-tier-thresholds)
5. [Safety Flags](#safety-flags)
6. [IEEE/NEMA Engineering Standards](#ienmnema-engineering-standards)
7. [Component-Specific Thresholds](#component-specific-thresholds)
8. [Configuration Reference](#configuration-reference)

---

## Overview

The WACH Insight health scoring engine uses a **FAIR ( Fair Attribute Impact Rating)** methodology to evaluate AHU electrical performance. Each metric is scored relative to the AHU's own historical baseline rather than absolute fleet-wide thresholds.

### Core Philosophy

> **"Is this AHU behaving differently than it normally does?"**

Instead of comparing e0101 (0.67 kW, PF 0.35) to e0105 (35 kW, PF 0.74), each AHU is scored against its own historical distribution. This ensures fair evaluation across differently-sized AHUs.

---

## Health Index Structure

```
health_index = 100 - (penalty × 100)

where:
  penalty = Σ(weight_i × score_i)

  score_i ∈ [0, 1] for each metric i

Perfect baseline → penalty = 0 → index = 100
All metrics maxed → penalty = 1 → index = 0
```

### Component Weights

| Metric | Weight | Description |
|--------|--------|-------------|
| Energy Anomaly | 15% | Hourly energy consumption deviation |
| Power Factor Degradation | 25% | PF below own baseline |
| Phase Imbalance | 25% | Current unbalance deviation |
| THD Drift | 15% | Harmonic distortion trend |
| Overload | 20% | Power approaching ceiling |

**Total**: 100% (weights sum to 1.0)

---

## Scoring Parameters

### Level vs Trend Blend

Each metric score is a weighted blend:

```
score = LEVEL_WEIGHT × level_score + TREND_WEIGHT × trend_score

where:
  LEVEL_TERM (70%) = "Is it bad RIGHT NOW?"
  TREND_TERM (30%) = "Is it GETTING WORSE over the past 7 days?"
```

| Parameter | Value | Description |
|-----------|-------|-------------|
| LEVEL_WEIGHT | 0.70 | Current state weight |
| TREND_WEIGHT | 0.30 | Trend direction weight |

### Sensitivity Factors

Controls how sharply the sigmoid response transitions from "normal" to "concerning":

```python
SENSITIVITY = {
    "energy_anomaly":  2.0,   # Steep response to energy deviations
    "pf_degradation":  2.5,   # Slightly more sensitive to PF issues
    "phase_imbalance": 2.0,
    "thd_drift":       2.0,
    "overload":        2.0,
}
```

| Metric | Sensitivity | Effect |
|--------|-------------|--------|
| Energy Anomaly | 2.0 | Moderate sensitivity to energy spikes |
| PF Degradation | 2.5 | Higher sensitivity (PF critical for efficiency) |
| Phase Imbalance | 2.0 | Moderate sensitivity |
| THD Drift | 2.0 | Moderate sensitivity |
| Overload | 2.0 | Moderate sensitivity |

### Slope Sensitivity

```
SLOPE_SENS = 3.0
```

Normalizes slope values before sigmoid transformation:
- slope_normalized = ols_slope(hist_series) / rstd
- trend_score = sigmoid(score × SLOPE_SENS)

---

## Health Tier Thresholds

| Tier | Range | Color | Action Required |
|------|-------|-------|-----------------|
| Healthy | 80–100 | 🟢 Green | None - operating normally |
| Monitor | 60–79 | 🟡 Yellow/Amber | Watch for degradation |
| Maintenance Soon | 40–59 | 🟠 Orange | Schedule maintenance |
| Critical | 0–39 | 🔴 Red | Immediate intervention |

### Tier Distribution Example

```
Fleet: 120 AHUs

Healthy (80-100):     57 AHUs  (48%)
Monitor (60-79):      55 AHUs  (46%)
Maintenance Soon:      7 AHUs  (6%)
Critical (0-39):       0 AHUs  (0%)
```

---

## Safety Flags

Static flags indicating chronic structural issues. **They do NOT affect the health index** but trigger engineering review.

| Flag | Condition | Metric Threshold | Description |
|------|-----------|------------------|-------------|
| `THD_CHRONIC_HIGH` | median 24h-THD > 15% | THD > 15% | Chronic harmonic distortion |
| `IMBALANCE_SEVERE` | median unbalance > 30% | Unbalance > 30% | Severe phase imbalance |
| `PF_CHRONIC_LOW` | median PF < 0.50 | PF < 0.50 | Chronically poor power factor |
| `OVERLOAD_CHRONIC` | median/p95 > 0.90 | ratio > 0.90 | Operating near ceiling |

### Safety Flag Logic

```python
def compute_safety_flags(baselines: Dict) -> Dict[str, List[str]]:
    """Evaluate each AHU's baseline against structural thresholds."""
    flags = {}
    for ahu_id, b in baselines.items():
        f = []
        
        thd_med = b["composite_thd_24h"]["median"]
        imb_med = b["current_unbalance"]["median"]
        pf_med = b["power_factor_avg"]["median"]
        pwr_med = b["power_total"]["median"]
        pwr_p95 = b["power_total"]["p95"]
        
        if thd_med > 15.0:
            f.append("THD_CHRONIC_HIGH")
        if imb_med > 30.0:
            f.append("IMBALANCE_SEVERE")
        if pf_med < 0.50:
            f.append("PF_CHRONIC_LOW")
        if pwr_p95 > 0 and pwr_med / pwr_p95 > 0.90:
            f.append("OVERLOAD_CHRONIC")
        
        flags[ahu_id] = f
    return flags
```

---

## IEEE/NEMA Engineering Standards

### Phase Imbalance - NEMA MG1

| Threshold | Value | Description |
|-----------|-------|-------------|
| Warning | 2.0% | NEMA MG1 warning level |
| Critical | 5.0% | NEMA MG1 critical limit |

**Formula**: `unbalance_pct = max(I_max - I_avg, I_avg - I_min) / I_avg × 100`

### THD - IEEE 519

| Threshold | Value | Description |
|-----------|-------|-------------|
| Baseline | 3.5% | Typical baseline for commercial facilities |
| Critical Limit | 5.0% | IEEE 519 harmonic limit |

**Important**: THD uses **24-hour rolling mean** to filter transient spikes from motor starts, elevators, etc.

### Power Factor

| Threshold | Value | Description |
|-----------|-------|-------------|
| Baseline | 0.87 | Typical good PF for industrial facilities |
| Minimum Acceptable | 0.80 | Often utility penalty threshold |

---

## Component-Specific Thresholds

### 1. Energy Anomaly (15% Weight)

**Question**: Is this AHU consuming an unusual amount of energy compared to its own baseline?

#### Formula

```
Level Term (70%):
  z = (delta_kwh − ahu_median_delta) / ahu_rstd_delta
  raw = 0.6 × |z| + 0.4 × max(0, z)

Trend Term (30%):
  slope_normalized = ols_slope(hist_delta_series) / rstd
  trend_score = sigmoid_score(max(0, slope_normalized) × SLOPE_SENS)

Final Score:
  score = clamp(LEVEL_WEIGHT × level_score + TREND_WEIGHT × trend_score, 0, 1)
```

#### Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| SENSITIVITY["energy_anomaly"] | 2.0 | Sigmoid steepness |
| MIN_RSTD["delta_kwh"] | 0.05 | Minimum robust std |
| TREND_WINDOW_H | 168 | Hours for trend (7 days) |

#### Edge Cases

| Condition | Action |
|-----------|--------|
| delta_kwh < 0 | Return 0.0 (meter reset) |
| Missing median or rstd | Return 0.5 (neutral) |

---

### 2. Power Factor Degradation (25% Weight)

**Question**: Is this AHU's PF lower than its own established normal, and trending downward?

#### Formula

```
Level Term (70%):
  z = (ahu_median_pf − current_pf) / ahu_rstd_pf
  Note: Positive z = PF below median = penalty

Trend Term (30%):
  slope_normalized = ols_slope(hist_pf_series) / rstd
  trend_score = sigmoid_score(max(0, -slope_normalized) × SLOPE_SENS)
  Note: Negative slope = PF falling = bad

Final Score:
  score = clamp(LEVEL_WEIGHT × level_score + TREND_WEIGHT × trend_score, 0, 1)

Load Discount:
  IF power < PF_DISCOUNT_THRESHOLD × own_median_power
    score = score × PF_DISCOUNT_FACTOR

  where: PF_DISCOUNT_THRESHOLD = 0.60
         PF_DISCOUNT_FACTOR = 0.35
```

#### Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| SENSITIVITY["pf_degradation"] | 2.5 | Higher sensitivity |
| MIN_RSTD["power_factor_avg"] | 0.008 | Minimum robust std |
| PF_DISCOUNT_THRESHOLD | 0.60 | Below 60% load threshold |
| PF_DISCOUNT_FACTOR | 0.35 | Score reduction factor |

#### Load Discount Logic

When an AHU operates below 60% of its own median power, the PF penalty is reduced:

```python
if current_power < PF_DISCOUNT_THRESHOLD * ahu_median_power:
    score = score × PF_DISCOUNT_FACTOR
```

**Rationale**: Low PF at low load is normal; penalties apply only when PF is bad at normal load.

#### Edge Cases

| Condition | Action |
|-----------|--------|
| pf is None or NaN | Return 0.0 (assume worst case) |
| Missing median/rstd | Return 0.0 |

---

### 3. Phase Imbalance (25% Weight)

**Question**: Is current unbalance higher than the AHU's established normal?

#### Formula

```
Level Term (70%):
  z = (current_unbalance − ahu_median_unbal) / ahu_rstd_unbal
  Higher unbalance = higher z = penalty

Trend Term (30%):
  slope_normalized = ols_slope(hist_unbal_series) / rstd
  trend_score = sigmoid_score(max(0, slope_normalized) × SLOPE_SENS)

Final Score:
  score = clamp(LEVEL_WEIGHT × level_score + TREND_WEIGHT × trend_score, 0, 1)
```

#### Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| SENSITIVITY["phase_imbalance"] | 2.0 | Sigmoid steepness |
| MIN_RSTD["current_unbalance"] | 0.15 | Minimum robust std |

#### Engineering Thresholds

| Condition | Value | NEMA MG1 Classification |
|-----------|-------|------------------------|
| Warning | > 2% | Engineering attention needed |
| Critical | > 5% | Immediate action required |

#### Edge Cases

| Condition | Action |
|-----------|--------|
| unbal is None or NaN | Return 0.0 (assume worst case) |
| Missing median/rstd | Return 0.0 |

---

### 4. THD Drift (15% Weight)

**Question**: Is harmonic distortion elevated above the AHU's normal trend?

#### CRITICAL REQUIREMENT

Both current value AND baseline MUST use **24-hour rolling mean**. This filters transient spikes from motor starts, elevators, etc.

#### Formula

```
Input: thd_24h = composite_thd_24h (max of L1 and L3, 24h rolling mean)

Level Term (70%):
  z = (thd_24h − ahu_median_thd) / ahu_rstd_thd

Trend Term (30%):
  slope_normalized = ols_slope(hist_thd_24h_series) / rstd
  trend_score = sigmoid_score(max(0, slope_normalized) × SLOPE_SENS)

Final Score:
  score = clamp(LEVEL_WEIGHT × level_score + TREND_DATE_WEIGHT × trend_score, 0, 1)
```

#### Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| SENSITIVITY["thd_drift"] | 2.0 | Sigmoid steepness |
| MIN_RSTD["composite_thd_24h"] | 0.15 | Minimum robust std |
| THD_ROLLING_H | 24 | Rolling mean window (hours) |
| TREND_WINDOW_H | 168 | Trend calculation window |

#### Baseline Building

```python
# MUST use rolling mean series, NOT instantaneous values
thd_24h_series = (
    grp["composite_thd"]
    .rolling(THD_ROLLING_H, min_periods=1)
    .mean()
    .dropna()
    .values
)

# Compute baseline ON the rolling mean series
med, rstd = robust_params(thd_24h_series, MIN_RSTD["composite_thd_24h"])
```

**Why 24h rolling mean?**
- Filters transient THD spikes from motor starts
- Compares apples-to-apples (current = rolling mean, baseline = rolling mean)
- Prevents permanently inflated z-scores

#### IEEE 519 Compliance

| Threshold | Value | Description |
|-----------|-------|-------------|
| Baseline | 3.5% | Typical commercial facility |
| Critical Limit | 5.0% | IEEE 519 maximum |

#### Edge Cases

| Condition | Action |
|-----------|--------|
| thd_24h is None or NaN | Return 0.0 |
| Baseline computed on rolling mean (not instantaneous) |

---

### 5. Overload (20% Weight)

**Question**: Is the AHU approaching or exceeding its own historical power ceiling?

#### Three-Component Formula

```
A. Ceiling Term (50%):
   power_ratio = current_power / own_p95_power
   demand = max(0, power_ratio − 0.85)
   score_A = sigmoid_score(demand × 8)

B. Z-Score Term (30%):
   z = (current_power − ahu_median_power) / ahu_rstd_power
   score_B = sigmoid_score(z × 1.5)

C. Trend Term (20%):
   slope_normalized = ols_slope(hist_power_series) / rstd
   score_C = sigmoid_score(max(0, slope_normalized) × SLOPE_SENS)

Final Score:
  score = 0.50 × score_A + 0.30 × score_B + 0.20 × score_C
```

#### Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| MIN_RSTD["power_total"] | 0.05 | Minimum robust std |
| SLOPE_SENS | 3.0 | Slope sensitivity |

#### Ceiling Detection Logic

| Condition | Score Component | Description |
|-----------|-----------------|-------------|
| power_ratio < 0.85 | score_A ≈ 0 | Operating well below ceiling |
| power_ratio = 0.95 | score_A ≈ 0.76 | Near ceiling - attention needed |
| power_ratio = 1.00 | score_A ≈ 1.0 | At p95 ceiling |
| power_ratio > 1.00 | score_A ≈ 1.0 | Exceeding ceiling - critical |

#### Sigmoid Details

```
score_A = sigmoid(demand × 8) × 2 - 1

where:
  demand = max(0, power_ratio - 0.85)

Behavior:
  power_ratio = 0.85 → demand = 0 → score_A ≈ 0
  power_ratio = 0.95 → demand = 0.10 → score_A ≈ 0.76
  power_ratio = 1.00 → demand = 0.15 → score_A ≈ 1.0
```

#### Edge Cases

| Condition | Action |
|-----------|--------|
| power is None or NaN | Return 0.5 (neutral) |
| p95 baseline unavailable | Return 0.5 (neutral) |

---

## Configuration Reference

### Main Configuration File

**Location**: `backend/core/risk_engine.py` and `backend/core/fair_health_scoring.py`

### Complete Parameter Table

| Category | Parameter | Value | Location |
|----------|-----------|-------|----------|
| **Health Index** | ENERGY_ANOMALY_WEIGHT | 0.15 | HEALTH_INDEX_WEIGHTS |
| | PF_DEGRADATION_WEIGHT | 0.25 | HEALTH_INDEX_WEIGHTS |
| | PHASE_IMBALANCE_WEIGHT | 0.25 | HEALTH_INDEX_WEIGHTES |
| | THD_DRIFT_WEIGHT | 0.15 | HEALTH_INDEX_WEIGHTS |
| | OVERLOAD_WEIGHT | 0.20 | HEALTH_INDEX_WEIGHTS |
| **Scoring Blend** | LEVEL_WEIGHT | 0.70 | Global constant |
| | TREND_WEIGHT | 0.30 | Global constant |
| **Sensitivity** | SENSITIVITY[energy] | 2.0 | SENSITIVITY dict |
| | SENSITIVITY[pf] | 2.5 | SENSITIVITY dict |
| | SENSITIVITY[unbalance] | 2.0 | SENSITIVITY dict |
| | SENSITIVITY[thd] | 2.0 | SENSITIVITY dict |
| | SLOPE_SENS | 3.0 | Global constant |
| **Minimum RSTD** | MIN_RSTD[delta_kwh] | 0.05 | MIN_RSTD dict |
| | MIN_RSTD[power_factor] | 0.008 | MIN_RSTD dict |
| | MIN_RSTD[unbalance] | 0.15 | MIN_RSTD dict |
| | MIN_RSTD[thd] | 0.15 | MIN_RSTD dict |
| | MIN_RSTD[power_total] | 0.05 | MIN_RSTD dict |
| **Load Discount** | PF_DISCOUNT_THRESHOLD | 0.60 | Global constant |
| | PF_DISCOUNT_FACTOR | 0.35 | Global constant |
| **THD Configuration** | THD_ROLLING_H | 24 | Global constant |
| **Safety Flags** | THD_CHRONIC_HIGH | > 15% | SAFETY_FLAGS_DEF |
| | IMBALANCE_SEVERE | > 30% | SAFETY_FLAGS_DEF |
| | PF_CHRONIC_LOW | < 0.50 | SAFETY_FLAGS_DEF |
| | OVERLOAD_CHRONIC | > 90% ratio | SAFETY_FLAGS_DEF |

### Threshold Comparison: Absolute vs FAIR

| Metric | Absolute Threshold | FAIR Method |
|--------|-------------------|-------------|
| Energy Anomaly | Not applicable | Uses per-AHU median + std |
| Power Factor | 0.87 (absolute) | Uses per-AHU baseline |
| Phase Imbalance | > 5% critical | Uses per-AHU baseline + NEMA thresholds |
| THD | 5% IEEE 519 limit | Uses per-AHU baseline + rolling mean |
| Overload | Not applicable | Uses per-AHU p95 ceiling |

---

## Formula Derivations

### Sigmoid Score Transformation

```
Standard sigmoid: σ(x) = 1 / (1 + e^(-x))

Our transformation:
  score = clip(σ(raw) × 2 - 1, 0, 1)

Where:
  raw = sensitivity × z_score (or slope_normalized)
  
Behavior:
  raw = 0   → σ(0) = 0.5 → score = 0.0 (baseline)
  raw = 1   → σ(1) ≈ 0.73 → score ≈ 0.46
  raw = 2   → σ(2) ≈ 0.88 → score ≈ 0.76
  raw = 3   → σ(3) ≈ 0.95 → score ≈ 0.91
```

### Robust Statistics (Median + MAD)

```
MAD = Median Absolute Deviation
rstd = 1.4826 × MAD

Why 1.4826?
- For normal distribution: E[MAD] ≈ 0.6745 × σ
- Therefore: σ ≈ MAD / 0.6745 ≈ 1.4826 × MAD

Advantages over std:
- Robust to outliers
- Works with bimodal distributions
- Stable for heavy-tailed data
```

### OLS Slope Calculation

```
OLS slope β = [n·Σ(i·y) - Σ(i)·Σ(y)] / [n·Σ(i²) - (Σ(i))²]

Where:
  i = {0, 1, 2, ..., n-1} (time indices)
  y = {y_0, y_1, ..., y_{n-1}} (values)

Normalized slope:
  slope_normalized = β / rstd
  
Where rstd is the robust std of the y values.
```

---

## Usage Examples

### Example 1: Energy Anomaly Calculation

```python
from core.fair_health_scoring import score_energy_anomaly
import numpy as np

# Current hourly energy consumption
current_delta_kwh = 2.5  # kWh

# AHU's historical baseline
ahu_median_delta = 2.0
ahu_rstd_delta = 0.5

# 7 days of hourly history
hist_delta_series = np.array([1.8, 2.1, 1.9, 2.3, 2.0] * 34)  # 170 points

score, z = score_energy_anomaly(
    delta_kwh=current_delta_kwh,
    ahu_median_delta=ahu_median_delta,
    ahu_rstd_delta=ahu_rstd_delta,
    hist_delta_series=hist_delta_series
)

print(f"Score: {score:.3f}")
print(f"Z-score: {z:.3f}")

# Interpretation:
# z = (2.5 - 2.0) / 0.5 = 1.0
# Current is 1 std above median → elevated but not critical
```

### Example 2: Power Factor with Load Discount

```python
from core.fair_health_scoring import score_power_factor
import numpy as np

# Current measurements
current_pf = 0.82
current_power = 50.0  # kW

# AHU's historical baseline
ahu_median_pf = 0.89
ahu_rstd_pf = 0.02
ahu_median_power = 100.0  # kW

# History
hist_pf_series = np.array([0.88, 0.89, 0.87] * 56)  # 168 points

# Check if load discount applies
if current_power < PF_DISCOUNT_THRESHOLD * ahu_median_power:
    print("Load discount applies!")
    # Score will be reduced to 35% of computed value

score, z = score_power_factor(
    pf=current_pf,
    power=current_power,
    ahu_median_pf=ahu_median_pf,
    ahu_rstd_pf=ahu_rstd_pf,
    hist_pf_series=hist_pf_series
)

print(f"Score: {score:.3f}")
```

### Example 3: THD with Rolling Mean

```python
from core.fair_health_scoring import score_thd_drift
import numpy as np

# Current 24h rolling mean THD (not instantaneous!)
composite_thd_24h = 4.5  # % THD (24h rolling mean)

# AHU's historical baseline on rolling mean
ahu_median_thd = 3.2
ahu_rstd_thd = 0.8

# History of 24h rolling means
hist_thd_24h_series = np.array([3.0, 3.1, 3.2, 3.3] * 42)  # 168 points

score, z = score_thd_drift(
    thd_24h=composite_thd_24h,
    ahu_median_thd=ahu_median_thd,
    ahu_rstd_thd=ahu_rstd_thd,
    hist_thd_24h_series=hist_thd_24h_series
)

print(f"Score: {score:.3f}")

# Compliance check (IEEE 519)
if composite_thd_24h > 5.0:
    print("WARNING: Exceeds IEEE 519 limit!")
```

---

## Troubleshooting

### Common Issues

| Symptom | Root Cause | Solution |
|---------|------------|----------|
| Score always 0.5 | Missing baseline data | Ensure ≥ 24h of history |
| Score always 0.0 | Missing/NaN values | Check for data gaps |
| Unstable scores | Insufficient history | Ensure ≥ 168h for trend |
| Division by zero | rstd near zero | MIN_RSTD should prevent this |

### Debugging Checklist

1. **Verify minimum history**: ≥ 24h for baseline, ≥ 168h for trend
2. **Check for NaN**: Ensure no missing values in current or baseline
3. **Verify units**: THD must use 24h rolling mean, not instantaneous
4. **Check MIN_RSTD**: Values should be > 0 for all metrics

---

## References

- **NEMA MG1**: Motors and Generators standard
- **IEEE 519**: Standard for Electric Power Systems in Industrial and Commercial Buildings
- **FAIR Scoring**: Fair Attribute Impact Rating methodology

---

*Document generated by WACH Insight Engineering Team*
