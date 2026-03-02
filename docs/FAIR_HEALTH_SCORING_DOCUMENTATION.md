# FAIR Health Scoring Engine Documentation

---

**File**: `backend/core/fair_health_scoring.py`  
**Last Updated**: 2026-03-02  
**Version**: Stage 2B (Per-AHU Baseline Method)

---

## Table of Contents

1. [Core Philosophy](#core-philosophy)
2. [Score Anatomy](#score-anatomy)
3. [Math Utilities](#math-utilities)
4. [Health Index Formula](#health-index-formula)
5. [Score Components](#score-components)
   - [Energy Anomaly (15%)](#energy-anomaly-15)
   - [Power Factor Degradation (25%)](#power-factor-degradation-25)
   - [Phase Imbalance (25%)](#phase-imbalance-25)
   - [THD Drift (15%)](#thd-drift-15)
   - [Overload (20%)](#overload-20)
6. [Baseline Building](#baseline-building)
7. [Safety Flags](#safety-flags)
8. [Edge Cases & Validation](#edge-cases--validation)
9. [Output Format](#output-format)

---

## Core Philosophy

### Per-AHU Baseline Methodology

Every AHU is judged **entirely against its own historical baseline**. No AHU's score is influenced by any other AHU's operating level.

> **Why?** A hospital fleet will never perform similarly.
> - `e0101` runs at 0.67 kW with PF 0.35
> - `e0105` runs at 35 kW with PF 0.74
>
> Applying the same absolute threshold to both produces meaningless scores.

### The Correct Question

**Wrong question**: "Is this AHU good or bad in absolute terms?"  
**Right question**: "Is this AHU behaving differently than it normally does?"

A z-score answers this for any AHU regardless of its size, load level, PF characteristic, or inherent imbalance.

### Why Robust Statistics (Median + MAD)?

e0111 has L1 THD alternating between ~14% and ~97% (bimodal):
- Mean = 52%, std = 40% → **useless** as baseline
- Median = 15.4%, MAD-std = 3.5% → **correctly** identifies the lower operating mode as "normal"

For well-behaved distributions: median ≈ mean and MAD-std ≈ regular std.  
**Robust stats are strictly better with no downside.**

### Critical THD Baseline Detail

The THD score uses the **24-hour rolling mean** of composite THD (max of L1, L3) to filter transient spikes from motor starts, elevators, etc.

**The baseline MUST also be computed on the 24h rolling mean series**, not instantaneous values. Otherwise the comparison is apples-to-oranges and z-scores will be permanently inflated.

> **Tested case**: e0111 had z ≈ 10 at all times when instantaneous baseline was used with 24h-mean score.

---

## Score Anatomy

Each component score is a weighted blend:

```
score = LEVEL_WEIGHT × level_term + TREND_WEIGHT × trend_term

where:
  LEVEL_TERM (70%)  = "Is it bad RIGHT NOW?"
  TREND_TERM (30%)  = "Is it GETTING WORSE over the past 7 days?"

score = 0.70 × sigmoid_score(z × sensitivity)
      + 0.30 × sigmoid_score(max(0, ±slope_normalized) × SLOPE_SENS)
```

### Sensitivity Configuration

```python
SENSITIVITY = {
    "energy_anomaly":  2.0,   # Steep response to energy deviations
    "pf_degradation":  2.5,   # Slightly more sensitive to PF issues
    "phase_imbalance": 2.0,
    "thd_drift":       2.0,
    "overload":        2.0,
}

SLOPE_SENS = 3.0  # Slope sensitivity after normalization
```

---

## Math Utilities

### Sigmoid Score Transformation

```python
def sigmoid_score(raw: float) -> float:
    """
    Map raw penalty to [0, 1] where raw = 0 → score = 0.

    Standard sigmoid gives 0.5 at raw=0. We shift and rescale:
        score = clip(sigmoid(raw) × 2 - 1, 0, 1)

    Behaviour:
        raw = 0  → 0.00   (exactly at baseline, no concern)
        raw = 1  → 0.46   (1 std above/below)
        raw = 2  → 0.76   (2 std)
        raw = 3  → 0.91   (3 std)
    """
    return float(np.clip(sigmoid(raw) * 2.0 - 1.0, 0.0, 1.0))
```

### Robust Parameters (Median + MAD)

```python
def robust_params(values, min_rstd=0.01) -> tuple:
    """
    Compute robust location (median) and scale (1.4826 × MAD).

    1.4826 × MAD equals std for a normal distribution.
    For heavy-tailed or bimodal distributions it is far more stable.

    Returns (median, rstd) where rstd >= min_rstd.
    """
    v = values[~np.isnan(values)]
    if len(v) < 3:
        median = float(np.nanmedian(values)) if len(values) > 0 else 0.0
        return median, min_rstd
    
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    rstd = max(1.4826 * mad, min_rstd)
    return med, rstd
```

### OLS Slope Calculation

```python
def ols_slope(values: np.ndarray) -> float:
    """
    OLS slope β through equally-spaced points (0, y₀), (1, y₁), …, (n-1, yₙ₋₁).
    Returns slope in metric-units per hour.

    Closed-form (O(n), no matrix ops):
        β = [n·Σ(i·y) − Σ(i)·Σ(y)] / [n·Σ(i²) − (Σ(i))²]
    """
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

## Health Index Formula

```
health_index = clamp(100 − penalty × 100, 0, 100)

where:
  penalty = Σ(weight_i × score_i) ∈ [0, 1]

Perfect baseline → penalty = 0 → index = 100  
All scores maxed → penalty = 1 → index = 0
```

### Health Tier Thresholds

| Tier | Range | Color |
|------|-------|-------|
| Healthy | 80–100 | Green |
| Monitor | 60–79 | Yellow/Amber |
| Maintenance Soon | 40–59 | Orange |
| Critical | 0–39 | Red |

---

## Score Components

### Energy Anomaly (15%)

**Question**: Is this AHU consuming an unusual amount of energy compared to its own baseline?

**Formula**:
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

**Key Parameters**:
```python
SENSITIVITY["energy_anomaly"] = 2.0
MIN_RSTD["delta_kwh"] = 0.05
```

**Edge Cases**:
- `delta_kwh < 0` → return 0.0
- Missing median or rstd → return 0.0

---

### Power Factor Degradation (25%)

**Question**: Is this AHU's PF lower than its own established normal, and trending downward?

**Formula**:
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

**Key Parameters**:
```python
SENSITIVITY["pf_degradation"] = 2.5
MIN_RSTD["power_factor_avg"] = 0.008
PF_DISCOUNT_THRESHOLD = 0.60   # below 60% of own median power
PF_DISCOUNT_FACTOR = 0.35      # reduce score to 35%
```

**Edge Cases**:
- `pf is None or isNaN` → return 0.0
- Missing median/rstd → return 0.0

---

### Phase Imbalance (25%)

**Question**: Is current unbalance higher than the AHU's established normal?

**Formula**:
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

**Key Parameters**:
```python
SENSITIVITY["phase_imbalance"] = 2.0
MIN_RSTD["current_unbalance"] = 0.15
```

**Edge Cases**:
- `unbal is None or isNaN` → return 0.0
- Missing median/rstd → return 0.0

---

### THD Drift (15%)

**Question**: Is harmonic distortion elevated above the AHU's normal trend?

**CRITICAL REQUIREMENT**: Both current value AND baseline must use 24h rolling mean.

**Formula**:
```
Input: thd_24h = composite_thd_24h (max of L1 and L3, 24h rolling mean)

Level Term (70%):
  z = (thd_24h − ahu_median_thd) / ahu_rstd_thd

Trend Term (30%):
  slope_normalized = ols_slope(hist_thd_24h_series) / rstd
  trend_score = sigmoid_score(max(0, slope_normalized) × SLOPE_SENS)

Final Score:
  score = clamp(LEVEL_WEIGHT × level_score + TREND_WEIGHT × trend_score, 0, 1)
```

**Key Parameters**:
```python
SENSITIVITY["thd_drift"] = 2.0
MIN_RSTD["composite_thd_24h"] = 0.15
THD_ROLLING_H = 24           # 24-hour rolling mean window
TREND_WINDOW_H = 168         # 7 days for slope calculation
```

**Baseline Building**:
```python
# MUST use rolling mean series, not instantaneous values
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

**Edge Cases**:
- `thd_24h is None or isNaN` → return 0.0
- Baseline computed on 24h rolling mean (not instantaneous)
- min_periods=1 ensures even short series work

---

### Overload (20%)

**Question**: Is the AHU approaching or exceeding its own historical power ceiling?

**Three-Component Score**:

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

**Key Parameters**:
```python
MIN_RSTD["power_total"] = 0.05
SLOPE_SENS = 3.0
```

**Ceiling Detection Logic**:
- `power_ratio >= 0.95` → "CRITICAL: near p95 ceiling"
- `power_ratio >= 0.90` → "elevated: approaching ceiling"
- `power_ratio >= 0.85` → "monitoring: above threshold"

**Edge Cases**:
- `power is None or isNaN` → return 0.0
- `p95 <= 0` → return 0.0

---

## Baseline Building

### Per-AHU Baseline Generation

```python
def build_baselines(df: pd.DataFrame) -> Dict:
    """
    Compute per-AHU robust baseline statistics from full history.
    
    Returns: { ahu_id: {
        "delta_kwh": {"median", "rstd", "p5", "p25", "p75", "p95", "n"},
        "power_factor_avg": {...},
        "current_unbalance": {...},
        "composite_thd_24h": {...},  # MUST use 24h rolling mean
        "power_total": {...}
    } }
    """
```

### THD Baseline Special Case

```python
# Calculate 24h rolling mean FIRST
thd_24h_series = (
    grp["composite_thd"]
    .rolling(THD_ROLLING_H, min_periods=1)
    .mean()
    .dropna()
    .values
)

# Then compute baseline ON the rolling mean series
med, rstd = robust_params(thd_24h_series, MIN_RSTD["composite_thd_24h"])
```

**Why this matters**: If you compute baseline on instantaneous values but score on 24h mean, z-scores will be permanently inflated.

---

## Safety Flags

Static flags indicating chronic structural issues. **They do NOT affect the health index** but trigger engineering review.

### Safety Flag Thresholds

| Flag | Condition | Description |
|------|-----------|-------------|
| `THD_CHRONIC_HIGH` | median 24h-THD > 15% | Chronic harmonic distortion |
| `IMBALANCE_SEVERE` | median unbalance > 30% | Severe phase imbalance |
| `PF_CHRONIC_LOW` | median PF < 0.50 | chronically poor power factor |
| `OVERLOAD_CHRONIC` | median / p95 > 0.90 | Operating near ceiling |

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

## Edge Cases & Validation

### Minimum Robust Std

Prevents division by near-zero:

```python
MIN_RSTD = {
    "delta_kwh":          0.05,
    "power_factor_avg":   0.008,
    "current_unbalance":  0.15,
    "composite_thd_24h":  0.15,
    "power_total":        0.05,
}

# Used in every scoring function:
rstd = max(ahu_rstd_value, MIN_RSTD["metric_name"])
if rstd <= 0:
    return 0.0, np.nan
```

### NaN Handling

Every scoring function validates inputs:

```python
def score_energy_anomaly(...):
    if delta_kwh is None or np.isnan(delta_kwh) or delta_kwh < 0:
        return 0.0, np.nan
    
    if ahu_median_delta is None or np.isnan(ahu_median_delta):
        return 0.0, np.nan
    
    # ... validation continues ...
```

### Historical Series Minimum Length

Slope calculation requires at least 3 points:

```python
hist_delta = df_energy[ahu_id].dropna().values[-TREND_WINDOW:]
hist_delta = hist_delta if len(hist_delta) >= 2 else np.array([])

# Later in scoring function:
if hist_delta is not None and len(hist_delta) >= 2
    # compute slope
else:
    score += 0.0  # No trend component
```

### Outlier Clipping

Slope values are clipped to prevent extreme values:

```python
slope_n = float(np.clip(ols_slope(hist_series) / rstd, -10, 10))
```

---

## Output Format

### Assessment JSON Structure

```json
{
  "ahu_id": "wach_e0101",
  "timestamp": "2026-03-02T14:30:00+08:00",
  "health_index": 84,
  "health_tier": "Healthy",
  "level": "Level 1",
  
  "risk_scores": {
    "energy_anomaly": 0.12,
    "power_factor": {
      "score": 0.15,
      "severity": "Normal",
      "confidence": "High"
    },
    "phase_imbalance": {
      "score": 0.25,
      "severity": "Elevated",
      "confidence": "Moderate"
    },
    "thd_drift": {
      "score": 0.12,
      "severity": "Normal",
      "confidence": "High"
    },
    "overload": {
      "score": 0.18,
      "severity": "Monitor",
      "confidence": "Moderate"
    }
  },
  
  "data_quality": {
    "missing_data_pct": 0.0,
    "days_since_last_valid_reading": 30,
    "model_source": "rule_based",
    "model_confidence_flag": "nominal"
  },
  
  // FAIR-specific output fields
  "power_total": 18.45,
  "power_factor": 0.72,
  "unbalance_pct": 4.5,
  "thd_24h": 2.8,
  "delta_kwh": 0.85,
  
  "data_quality_flag": 0,
  "safety_flags": "",
  
  // Z-score diagnostics
  "z_energy": 1.2,
  "z_pf": -0.8,
  "z_imbalance": 1.5,
  "z_thd": 0.9,
  "z_overload": 1.1
}
```

### Fleet Summary Output

```json
{
  "tier_distribution": {
    "Healthy": 45,
    "Monitor": 30,
    "MaintenanceSoon": 20,
    "Critical": 7
  },
  "top_5_lowest_health_index": [
    {"ahu_id": "e0111", "health_index": 28},
    ...
  ],
  "top_5_rising_risk": [
    {"ahu_id": "e0205", "overload_score": 0.78},
    ...
  ],
  "top_5_improved": [
    {"ahu_id": "e0103", "health_index": 92},
    ...
  ],
  "data_quality_issues_count": 3
}
```

---

## Severity Mapping

```python
def get_severity(score: float, risk_type: str) -> str:
    """Map risk score to severity level."""
    if score >= 0.8:
        return "Critical"
    elif score >= 0.6:
        return "Attention Required"
    elif score >= 0.4:
        return "Monitor"
    else:
        return "Normal"
```

| Score Range | Severity |
|-------------|----------|
| 0.8–1.0 | Critical |
| 0.6–0.79 | Attention Required |
| 0.4–0.59 | Monitor |
| 0.0–0.39 | Normal |

---

## Configuration Summary

### Health Index Weights (must sum to 1.0)

```python
HEALTH_INDEX_WEIGHTS = {
    "energy_anomaly":  0.15,
    "power_factor":    0.25,
    "phase_imbalance": 0.25,
    "thd_drift":       0.15,
    "overload":        0.20,
}
```

### Scoring Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `LEVEL_WEIGHT` | 0.70 | Current deviation weight |
| `TREND_WEIGHT` | 0.30 | Trend direction weight |
| `SLOPE_SENS` | 3.0 | Slope sensitivity multiplier |
| `THD_ROLLING_H` | 24 | THD rolling mean window |
| `TREND_WINDOW_H` | 168 | Slope calculation period (7 days) |
| `PF_DISCOUNT_THRESHOLD` | 0.60 | Power discount threshold |
| `PF_DISCOUNT_FACTOR` | 0.35 | Load discount multiplier |

---

## Key Implementation Notes

1. **Per-AHU Baseline**: Never compare AHUs to each other; always use historical own data
2. **Robust Stats**: Use median + MAD (1.4826 × MAD = robust std)
3. **THD Rolling Mean**: Both current value AND baseline must use 24h rolling mean
4. **Sigmoid Scoring**: Maps z-scores to [0,1] with anchor at 0 → score = 0
5. **Load Discount**: PF penalty reduced to 35% when operating <60% of own median power
6. **Overload Three-Part**: Ceiling proximity (50%) + z-score (30%) + trend (20%)
7. **Safety Flags**: Separate from health index; trigger engineering review
8. **Slope Clipping**: Clip slope/std to [-10, 10] to prevent extreme values
9. **Minimum Data**: Require ≥3 historical points for baseline; fallback to min_rstd

---

*Generated from `backend/core/fair_health_scoring.py`*
