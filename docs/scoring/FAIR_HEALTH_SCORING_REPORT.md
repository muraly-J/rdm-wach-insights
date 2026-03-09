# FAIR Health Scoring Engine - Technical Report

**File Analyzed:** `backend/core/fair_health_scoring.py`  
**Version:** Complete end-to-end analysis  
**Date:** 2026-03-03  

---

## Executive Summary

The FAIR (Fundamental AHU Integrity Ranking) Health Scoring Engine evaluates each Air Handling Unit (AHU) against its own historical baseline rather than fleet-wide thresholds. This per-AHU approach is necessary because AHUs in a hospital environment operate at vastly different scales:

- e0101 operates at 0.67 kW with PF 0.35
- e0105 operates at 35 kW with PF 0.74

Applying the same absolute thresholds to both would produce meaningless scores. Instead, FAIR uses z-scores relative to each AHU's own historical distribution.

---

## 1. Core Philosophy

### The FAIR Principle

> **"Every AHU is judged entirely against its own personal baseline. No AHU's score is influenced by any other AHU's operating level."**

The correct question is not *"Is this AHU good or bad in absolute terms?"*  
The correct question is *"Is this AHU behaving differently than it normally does?"*

### Why Robust Statistics?

The system uses **median + MAD (Median Absolute Deviation)** instead of mean ± std because:

1. AHUs can have bimodal operating patterns (e.g., THD alternating between ~9% and ~97%)
2. Mean = 52%, std = 40% is useless for such distributions
3. Median = 15.4%, MAD-std = 3.5% correctly identifies the lower mode as "normal"

For well-behaved distributions: median ≈ mean and MAD-std ≈ regular std  
Robust stats are strictly better with no downside.

---

## 2. Health Index Formula

### Overall Calculation

```
health_index = clip(100 − penalty × 100, 0, 100)

where: penalty = Σ(weight_i × score_i) for i ∈ {energy, pf, imbalance, thd, overload}
```

### Weight Distribution

| Component | Weight | Description |
|-----------|--------|-------------|
| energy_anomaly | 15% | Unusual energy consumption vs own baseline |
| power_factor | 25% | PF degradation from own normal |
| phase_imbalance | 25% | Current unbalance vs own baseline |
| thd_drift | 15% | Harmonic distortion drift vs own baseline |
| overload | 20% | Proximity to own power ceiling |

**Perfect baseline → penalty = 0 → index = 100**  
**All maxed → index = 0**

---

## 3. Health Tier Thresholds

| Tier | Range | Color |
|------|-------|-------|
| Healthy | 80–100 | Green |
| Monitor | 60–79 | Yellow/Amber |
| Maintenance Soon | 40–59 | Orange |
| Critical | 0–39 | Red |

---

## 4. Scoring Component Formulas

Each component score = `LEVEL_TERM × 0.70 + TREND_TERM × 0.30`

Where:
- **LEVEL TERM (70%)** answers: *"Is it bad RIGHT NOW?"*
- **TREND TERM (30%)** answers: *"Is it getting WORSE?"*

### 4.1 Energy Anomaly Score (15%)

**Purpose:** Detect unusual energy consumption compared to the AHU's own history.

```
Level Term:
  z = (delta_kwh − ahu_median_delta) / ahu_rstd_delta
  raw = 0.6 × |z| + 0.4 × max(0, z)
  lv = sigmoid_score(raw × SENSITIVITY[energy_anomaly])
  
Trend Term:
  slope_n = (7d_slope(delta_kwh_series) / ahu_rstd_delta)
  tr = sigmoid_score(max(0, slope_n) × SLOPE_SENS)

Final: score = 0.70 × lv + 0.30 × tr
```

**Parameters:**
- `SENSITIVITY["energy_anomaly"]` = 2.0

---

### 4.2 Power Factor Degradation Score (25%)

**Purpose:** Detect PF falling below the AHU's established normal.

```
Level Term:
  z = (ahu_median_PF − current_PF) / ahu_rstd_PF
  lv = sigmoid_score(z × SENSITIVITY[pf_degradation])
  
Trend Term:
  slope_n = (7d_slope(pf_series) / ahu_rstd_PF)
  tr = sigmoid_score(max(0, -slope_n) × SLOPE_SENS)

Final: score = 0.70 × lv + 0.30 × tr

Load Discount (NOT IMPLEMENTED in current code):
  If power < 60% of own median power:
    score = score × 0.35
```

**Parameters:**
- `SENSITIVITY["pf_degradation"]` = 2.5
- `PF_DISCOUNT_THRESHOLD` = 0.60 (60% of median power)
- `PF_DISCOUNT_FACTOR` = 0.35

**Note:** The load discount logic is commented out in `score_power_factor()`. To enable:
1. Pass `ahu_median_power` as additional parameter
2. Apply discount when current power < 60% of median

---

### 4.3 Phase Imbalance Score (25%)

**Purpose:** Detect current unbalance exceeding the AHU's own baseline.

```
Level Term:
  z = (current_unbalance − ahu_median_unbal) / ahu_rstd_unbal
  lv = sigmoid_score(z × SENSITIVITY[phase_imbalance])
  
Trend Term:
  slope_n = (7d_slope(unbal_series) / ahu_rstd_unbal)
  tr = sigmoid_score(max(0, slope_n) × SLOPE_SENS)

Final: score = 0.70 × lv + 0.30 × tr
```

**Parameters:**
- `SENSITIVITY["phase_imbalance"]` = 2.0
- `MIN_RSTD["current_unbalance"]` = 0.15

---

### 4.4 THD Drift Score (15%)

**Purpose:** Detect harmonic distortion elevation above the AHU's own baseline.

**CRITICAL DESIGN NOTE:** THD uses **24-hour rolling mean** (not instantaneous values) to filter transient spikes from motor starts, elevators, etc.

```
Level Term:
  z = (thd_24h − ahu_median_thd) / ahu_rstd_thd
  lv = sigmoid_score(z × SENSITIVITY[thd_drift])
  
Trend Term:
  slope_n = (7d_slope(thd_24h_series) / ahu_rstd_thd)
  tr = sigmoid_score(max(0, slope_n) × SLOPE_SENS)

Final: score = 0.70 × lv + 0.30 × tr
```

**Parameters:**
- `SENSITIVITY["thd_drift"]` = 2.0
- `THD_ROLLING_H` = 24 (hours for rolling mean)
- `MIN_RSTD["composite_thd_24h"]` = 0.15

**Why 24h Rolling Mean?**
- Instantaneous THD can spike to 97% during motor starts
- 24h mean filters these transients
- Baseline MUST be computed on the same 24h-mean series
- Using instantaneous baseline with 24h score caused z ≈ 10 for e0111

---

### 4.5 Overload Score (20%)

**Purpose:** Detect when the AHU approaches or exceeds its own historical power ceiling.

This score has **three sub-components**:

```
A. Ceiling Term (50%):
   power_ratio = current_power / own_p95_power
   demand = max(0, power_ratio − 0.85)
   score_A = sigmoid_score(demand × 8.0)

B. Z-Score Term (30%):
   z = (current − own_median) / own_rstd
   score_B = sigmoid_score(z × 1.5)

C. Trend Term (20%):
   slope_n = (7d_slope(power_series) / own_rstd)
   score_C = sigmoid_score(max(0, slope_n) × SLOPE_SENS)

Final: score = 0.50 × score_A + 0.30 × score_B + 0.20 × score_C
```

**Parameters:**
- `MIN_RSTD["power_total"]` = 0.05
- Ceiling threshold: 85% of p95 (p95 - 15%)

**Ceiling Proximity Interpretation:**
| Power Ratio | Status |
|-------------|--------|
| ≥ 0.95 | CRITICAL: near p95 ceiling |
| ≥ 0.90 | Elevated: approaching ceiling |
| ≥ 0.85 | Monitoring: above threshold |
| < 0.85 | Normal load level |

---

## 5. Mathematical Utilities

### 5.1 Sigmoid Functions

#### Standard Sigmoid
```python
sigmoid(x) = 1 / (1 + exp(-x))
```
Clamped to [-500, 500] for numerical stability.

#### Sigmoid Score
Maps raw penalty to [0, 1] where raw = 0 → score = 0:

```python
sigmoid_score(raw) = clip(sigmoid(raw) × 2 - 1, 0, 1)
```

**Behavior:**
| raw | score |
|-----|-------|
| 0.0 | 0.00 (exactly at baseline, no concern) |
| 1.0 | 0.46 (1 std above/below) |
| 2.0 | 0.76 (2 std) |
| 3.0 | 0.91 (3 std) |

### 5.2 Robust Statistics

```python
def robust_params(values):
    median = np.median(values)
    mad = np.median(abs(values - median))
    rstd = max(1.4826 × mad, min_rstd)
    return median, rstd
```

**1.4826 factor:** Makes MAD equal to std for normal distributions.

### 5.3 OLS Slope (7-Day Trend)

Closed-form linear regression for equally-spaced points:

```python
β = [n × Σ(i×y) − Σ(i) × Σ(y)] / [n × Σ(i²) − (Σ(i))²]
```

Slope is normalized by robust-std for comparison across metrics.

---

## 6. Thresholds & Configuration

### 6.1 Health Index Weights
```python
HEALTH_INDEX_WEIGHTS = {
    "energy_anomaly": 0.15,
    "power_factor":   0.25,
    "phase_imbalance": 0.25,
    "thd_drift":      0.15,
    "overload":       0.20,
}
```

### 6.2 Sensitivity Factors
Controls how quickly scores rise with deviation:

```python
SENSITIVITY = {
    "energy_anomaly":  2.0,
    "pf_degradation":  2.5,
    "phase_imbalance": 2.0,
    "thd_drift":       2.0,
    "overload":        2.0,
}
```

### 6.3 Level vs Trend Blend
```python
LEVEL_WEIGHT = 0.70   # "is it bad right now?"
TREND_WEIGHT = 0.30   # "is it getting worse?"
SLOPE_SENS = 3.0      # Slope sensitivity multiplier
```

### 6.4 Minimum Robust Std (prevent division by zero)
```python
MIN_RSTD = {
    "delta_kwh":          0.05,
    "power_factor_avg":   0.008,
    "current_unbalance":  0.15,
    "composite_thd_24h":  0.15,
    "power_total":        0.05,
}
```

### 6.5 Trend Window
```python
TREND_WINDOW_H = 168   # 7 days in hours
```

---

## 7. Safety Flags (Engineering Audit Layer)

**Purpose:** Identify chronic structural issues that warrant engineering review, regardless of daily health score.

Flags are metadata - they do NOT affect the health index calculation.

### 7.1 Safety Flag Thresholds

| Flag | Metric | Condition |
|------|--------|-----------|
| `THD_CHRONIC_HIGH` | median 24h-THD | > 15% |
| `IMBALANCE_SEVERE` | median unbalance | > 30% |
| `PF_CHRONIC_LOW` | median PF | < 0.50 |
| `OVERLOAD_CHRONIC` | median power / p95 | > 90% |

### 7.2 Flag Computation

```python
flags[ahu_id] = []
if median_thd > 15.0:
    flags.append("THD_CHRONIC_HIGH")
if median_unbalance > 30.0:
    flags.append("IMBALANCE_SEVERE")
if median_pf < 0.50:
    flags.append("PF_CHRONIC_LOW")
if (median_power / p95_power) > 0.90:
    flags.append("OVERLOAD_CHRONIC")
```

---

## 8. Edge Cases & Special Handling

### 8.1 Missing Data Handling

| Metric | Behavior |
|--------|----------|
| delta_kwh < 0 or NaN | Return (0.0, nan) |
| Missing median | Return (0.0, nan) |
| rstd ≤ 0 | Return (0.0, nan) |
| < 3 data points | Use min_rstd instead |

### 8.2 THD Special Case

The THD scoring has two critical requirements:

1. **Input must be 24h rolling mean** (not instantaneous)
2. **Baseline MUST be computed on the same 24h-mean series**

Violating this (e.g., using instantaneous baseline) causes:
- z-scores permanently inflated to ~10
- All units appear critically unhealthy

### 8.3 Floor Counting Edge Case

The documentation mentions:
> "For health index floor counting, use: 0–39 = Critical"

Current implementation uses `clip(100 − penalty × 100, 0, 100)` which ensures:
- Health index ∈ [0, 100]
- Floor counting: `int(health_index)` maps to tiers correctly

---

## 9. Output Schema

### 9.1 Assessment Structure

```python
{
    "ahu_id": str,
    "timestamp": ISO8601 string,
    "health_index": float (rounded to 1 decimal),
    "health_tier": str ("Healthy" | "Monitor" | "Maintenance Soon" | "Critical"),
    "level": str ("Level 1", etc.),
    
    "risk_scores": {
        "energy_anomaly": float,
        "power_factor": {
            "score": float,
            "severity": str ("Normal" | "Monitor" | "Attention Required" | "Critical"),
            "confidence": str,
            "signal": str (human-readable),
        },
        "phase_imbalance": {...},
        "thd_drift": {...},
        "overload": {...}
    },
    
    "data_quality": {
        "missing_data_pct": float,
        "days_since_last_valid_reading": int,
        "model_source": str,
        "model_confidence_flag": str
    },
    
    # Raw metrics for reference
    "power_total": float | None,
    "power_factor": float | None,
    "unbalance_pct": float | None,
    "thd_24h": float | None,
    "delta_kwh": float | None,
    
    # Diagnostics
    "data_quality_flag": 0 or 1,
    "safety_flags": str (comma-separated),
    
    # Z-scores per component
    "z_energy": float | None,
    "z_pf": float | None,
    "z_imbalance": float | None,
    "z_thd": float | None,
    "z_overload": float | None
}
```

### 9.2 Severity Mapping

| Score Range | Severity |
|-------------|----------|
| ≥ 0.8 | Critical |
| ≥ 0.6 | Attention Required |
| ≥ 0.4 | Monitor |
| < 0.4 | Normal |

---

## 10. Algorithm Flow Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                    FAIR HEALTH SCORING                         │
└───────────────────────────────────────────────────────────────┘

1. INPUT: Time series DataFrames
   ├─ df_power (power over time)
   ├─ df_energy (energy over time)
   ├─ df_pf (power factor over time)
   ├─ df_unbalance (unbalance over time)
   └─ df_thd_l1, df_thd_l3 (THD over time)

2. PREPROCESSING
   ├─ Build composite THD = max(L1, L3)
   ├─ Compute 24h rolling mean of THD
   └─ Calculate delta_kwh = energy.diff()

3. PER-AHU BASELINE CONSTRUCTION
   For each AHU:
   ├─ Compute robust stats for all metrics:
   │  ├─ delta_kwh: median, rstd, p5, p25, p75, p95
   │  ├─ power_factor: median, rstd, p5, etc.
   │  ├─ current_unbalance: median, rstd
   │  └─ composite_thd_24h: median, rstd (CRITICAL: use rolling mean!)
   └─ Compute safety flags based on baseline medians

4. SCORING (per AHU)
   For each of 5 metrics:
   ├─ Compute level term using current value vs baseline
   ├─ Compute trend term using 7-day slope
   └─ Blend: score = 0.70 × level + 0.30 × trend

5. HEALTH INDEX CALCULATION
   penalty = Σ(weight_i × score_i)
   health_index = clip(100 − penalty × 100, 0, 100)

6. TIER ASSIGNMENT
   if health_index ≥ 80: "Healthy"
   elif health_index ≥ 60: "Monitor"
   elif health_index ≥ 40: "Maintenance Soon"
   else: "Critical"

7. OUTPUT
   └─ Assessment object with all scores, tiers, and diagnostics
```

---

## 11. Critical Implementation Notes

### 11.1 THD Baseline is CRITICAL

The most common implementation error is using instantaneous THD values for the baseline while computing scores on 24h rolling means. This causes:

- **Symptom:** All units show z ≈ 10, health index ≈ 0
- **Root cause:** Baseline and score on different time scales
- **Fix:** Always compute baseline on the same aggregation level as scores

### 11.2 Load Discount Not Implemented

The `score_power_factor()` function has commented-out load discount logic:

```python
# Load discount: if power < 60% of own median power, scale score × 0.35
# Note: Need to pass ahu_median_power separately for this calculation
```

**Current behavior:** PF score is calculated regardless of load level.  
**Planned behavior (not implemented):**
- If current power < 60% of median: score = score × 0.35
- Rationale: PF degradation at very low loads is less concerning

### 11.3 Safety Flags Are Separate from Health Index

Safety flags are computed from **baseline medians** (long-term averages), not current values. They answer:
> "Does this AHU have chronic issues that warrant engineering review?"

They do NOT affect the health index calculation.

### 11.4 Data Quality Flag

The `data_quality_flag` field:
- `0`: All data present (THD 24h available)
- `1`: Missing data detected

This is a simple binary flag - future enhancements could track per-metric missing percentages.

---

## 12. Testing Recommendations

### 12.1 Unit Tests

1. **Sigmoid Score**
   - Input 0 → output 0
   - Input 1 → output ≈ 0.46
   - Input 3 → output ≈ 0.91

2. **Robust Stats**
   - Normal distribution: median ≈ mean, rstd ≈ std
   - Bimodal distribution: robust stats identify correct mode

3. **THD Baseline Consistency**
   - Input 24h rolling mean → baseline from 24h rolling mean
   - Input instantaneous → should fail gracefully

4. **Health Index Bounds**
   - All scores = 0 → index = 100
   - All scores = 1 → index = 0

### 12.2 Integration Tests

1. **Known AHU Behavior**
   - Load a known good AHU → health index ≥ 80
   - Load a known problematic AHU → health index < 60

2. **Tier Distribution**
   - Fleet of 100 identical AHUs → all in same tier
   - Mixed fleet → tiers reflect health distribution

---

## 13. Summary of Formulas

### All-in-One Health Index Formula

```
                    ┌─────────────────────────────────────────────┐
                    │         health_index = 100 − penalty × 100  │
                    └─────────────────────────────────────────────┘

where:

    penalty = w_e × score_e + w_pf × score_pf + w_i × score_i
            + w_t × score_t + w_o × score_o

    score_e = 0.70 × sigmoid_score( [0.6×|z_e|+0.4×max(0,z_e)] × 2.0 )
            + 0.30 × sigmoid_score( max(0, slope_e/rstd_e) × 3.0 )

    score_pf = 0.70 × sigmoid_score( [(med_pf−cur_pf)/rstd_pf] × 2.5 )
             + 0.30 × sigmoid_score( max(0, −slope_pf/rstd_pf) × 3.0 )
             [LOAD DISCOUNT NOT IMPLEMENTED]

    score_i = 0.70 × sigmoid_score( [(cur_unbal−med_unbal)/rstd_unbal] × 2.0 )
            + 0.30 × sigmoid_score( max(0, slope_unbal/rstd_unbal) × 3.0 )

    score_t = 0.70 × sigmoid_score( [(cur_thd−med_thd)/rstd_thd] × 2.0 )
            + 0.30 × sigmoid_score( max(0, slope_thd/rstd_thd) × 3.0 )
            [THD MUST use 24h rolling mean for both cur and baseline]

    score_o = 0.50 × sigmoid_score( [(cur/p95−0.85)] × 8.0 )
            + 0.30 × sigmoid_score( [(cur−med)/rstd] × 1.5 )
            + 0.20 × sigmoid_score( max(0, slope_power/rstd) × 3.0 )

    z_e = (delta_kwh − median_delta) / rstd_delta
    z_pf = (median_pf − cur_pf) / rstd_pf
    z_i = (cur_unbal − median_unbal) / rstd_unbal
    z_t = (cur_thd − med_thd_24h) / rstd_thd_24h
    z_o = (cur_power − median_power) / rstd_power

Weights: w_e=0.15, w_pf=0.25, w_i=0.25, w_t=0.15, w_o=0.20
```

---

## Appendix A: Reference Implementations

### Sigmoid Score (Core)
```python
def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-float(np.clip(x, -500, 500))))

def sigmoid_score(raw):
    return float(np.clip(sigmoid(raw) * 2.0 - 1.0, 0.0, 1.0))
```

### Robust Parameters
```python
def robust_params(values, min_rstd=0.01):
    v = values[~np.isnan(values)]
    if len(v) < 3:
        return np.nanmedian(values), min_rstd
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    rstd = max(1.4826 * mad, min_rstd)
    return med, rstd
```

### OLS Slope
```python
def ols_slope(values):
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    n = len(v)
    if n < 3:
        return 0.0
    i = np.arange(n, dtype=float)
    num = n * np.dot(i, v) - i.sum() * v.sum()
    denom = n * np.dot(i, i) - i.sum() ** 2
    return float(num / denom) if denom != 0 else 0.0
```

---

**Report Generated:** 2026-03-03  
**Document Owner:** WACH Insight Team  
**Next Review Date:** 2026-06-03
