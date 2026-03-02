# FAIR Health Scoring Implementation

## Summary

The FAIR (Fairness through Individual Robustness) health scoring algorithm has been implemented to evaluate each AHU against its own historical baseline, rather than comparing across the fleet.

## Key Philosophy

> "Every AHU is judged entirely against its own personal baseline. No AHU's score is influenced by any other AHU's operating level."

A hospital AHU fleet will never perform similarly to one another:
- e0101 runs at 0.67 kW with PF 0.35
- e0105 runs at 35 kW with PF 0.74

Applying the same threshold to both produces meaningless scores for both.

**The correct question is not "is this AHU good or bad in absolute terms?" but "is this AHU behaving differently than it normally does?"**

## Implementation Details

### Files Created/Modified

| File | Purpose |
|------|---------|
| `backend/core/fair_health_scoring.py` | **NEW** - FAIR scoring engine module |
| `backend/core/risk_engine.py` | **MODIFIED** - Added FAIR scoring functions |
| `scripts/generate_level1_health_scores.py` | **MODIFIED** - Updated with safety flags |
| `scripts/test_fair_scoring.py` | **NEW** - Test suite for FAIR scoring |

### Files Added to Backend

#### 1. `backend/core/fair_health_scoring.py`

Complete FAIR scoring engine with:

**Math Utilities:**
- `sigmoid_score(raw)` - Maps raw penalty to [0,1] with anchor at 0
- `robust_params(values)` - Computes median + MAD (1.4826 × MAD)
- `ols_slope(values)` - OLS slope calculation for trend analysis
- `clamp01(x)` - Clamps value to [0,1]

**FAIR Scoring Functions (5 metrics):**
- `score_energy_anomaly()` - Energy anomaly score
- `score_power_factor()` - Power factor degradation score  
- `score_phase_imbalance()` - Phase imbalance score
- `score_thd_drift()` - THD drift score (uses 24h rolling mean)
- `score_overload()` - Overload score with p95 ceiling reference

**Configuration:**
- `HEALTH_INDEX_WEIGHTS` - Weighting for each metric
- `SENSITIVITY` - Sensitivity factors for sigmoid scoring
- `LEVEL_WEIGHT = 0.70` - Level term weight
- `TREND_WEIGHT = 0.30` - Trend term weight

**Output Schema:**
```json
{
  "timestamp": "2026-02-23T14:00:00+08:00",
  "ahu_id": "wach_e0101",
  "health_index": 84,
  "health_tier": "Healthy",
  "risk_scores": {
    "energy_anomaly": {...},
    "power_factor": {...},
    "phase_imbalance": {...},
    "thd_drift": {...},
    "overload": {...}
  },
  "data_quality": {...},
  // FAIR-specific output fields
  "power_total": 7.5,
  "power_factor": 0.89,
  "unbalance_pct": 2.1,
  "thd_24h": 3.8,
  "delta_kwh": 15.2,
  "data_quality_flag": 0,
  "safety_flags": "",  // or comma-separated list
  "z_energy": 0.5,
  "z_pf": -1.2,
  "z_imbalance": 0.8,
  "z_thd": -0.3,
  "z_overload": 1.5
}
```

### Key Scoring Formula

Each component score = **70% Level Term + 30% Trend Term**

```
score = 0.70 × sigmoid_score(z × sensitivity) 
      + 0.30 × sigmoid_score(max(0, ±slope_normalized) × 3.0)
```

**Health Index:**
```
health_index = 100 - penalty × 100
penalty = Σ(weight_i × score_i)

weights:
- energy_anomaly:   15%
- power_factor:     25%
- phase_imbalance:  25%
- thd_drift:        15%
- overload:         20%
```

### Health Tiers

| Range | Tier |
|-------|------|
| 80-100 | Healthy |
| 60-79 | Monitor |
| 40-59 | Maintenance Soon |
| 0-39 | Critical |

### Static Safety Flags

AHUs with chronically extreme baselines get safety flags (do NOT affect health index):

| Flag | Condition |
|------|-----------|
| `THD_CHRONIC_HIGH` | median 24h-THD > 15% |
| `IMBALANCE_SEVERE` | median unbalance > 30% |
| `PF_CHRONIC_LOW` | median PF < 0.50 |
| `OVERLOAD_CHRONIC` | median power > 90% of own p95 |

### Why Robust Statistics?

Using median + MAD (1.4826 × MAD) instead of mean/std:

**Example - e0111 with bimodal THD:**
- L1 THD alternates between ~14% and ~97%
- Mean = 52%, std = 40% → useless as baseline
- Median = 15.4%, MAD-std = 3.5% → correctly identifies lower mode as "normal"

### THD Baseline Critical Detail

The THD score uses the **24-hour rolling mean** (not instantaneous values) to filter transient spikes from motor starts, elevators, etc.

The baseline **MUST** also be computed on the 24h rolling mean series, not instantaneous values. Otherwise the comparison is apples-to-oranges and z-score will be permanently inflated.

## Test Results

```
============================================================
FAIR Health Scoring Test Suite
============================================================

Testing robust_params...
  Normal data: median=11.00, rstd=1.48
  With outlier: median=12.00, rstd=1.48
  ✓ robust_params tests passed

Testing sigmoid_score...
  z=0 → score=0.000
  z=1 → score=0.462
  z=2 → score=0.762
  ✓ sigmoid_score tests passed

Testing score_energy_anomaly...
  At median: z=0.0, score=0.000 ✓
  +1 std: z=1.00, score=0.533 ✓
  +2 std: z=2.00, score=0.675 ✓
  ✓ energy_anomaly tests passed

Testing calculate_health_index...
  All zero scores → health_index = 100.0 ✓
  All max scores → health_index = 0.0 ✓
  Mixed scores → health_index = 87.5 (expected ~87.5) ✓
  ✓ health_index tests passed

Testing complete FAIR scoring scenario...
  Energy anomaly:    score=0.691, z=2.50
  PF degradation:    score=0.700, z=3.50
  Phase imbalance:   score=0.675, z=2.00
  THD drift:         score=0.533, z=1.00
  Overload:          score=0.254, z=1.67

  Health Index: 42.2
  ✓ Health index in valid range
  ✓ All z-scores verified

  ✓ Complete FAIR scoring scenario passed!
============================================================
All tests passed! ✓
============================================================
```

## Usage

### Generate Health Scores for All Time Ranges

```bash
# Fetch raw data and compute scores (all time ranges)
python scripts/generate_level1_health_scores.py --all-ranges

# Or fetch only
python scripts/generate_level1_health_scores.py --fetch-only

# Or compute scores from existing raw data
python scripts/generate_level1_health_scores.py --compute-only

# For specific time range
python scripts/generate_level1_health_scores.py --range 24h
```

### Test FAIR Scoring

```bash
python scripts/test_fair_scoring.py
```

### Import FAIR Scoring Module

```python
from backend.core.fair_health_scoring import (
    score_energy_anomaly,
    score_power_factor,
    score_phase_imbalance,
    score_thd_drift,
    score_overload,
    calculate_health_index,
)

# Score each component
energy_score, z_energy = score_energy_anomaly(
    delta_kwh=15.0,
    ahu_median_delta=10.0,
    ahu_rstd_delta=2.0,
    hist_delta_series=np.array([...])
)

# Calculate health index
risk_scores = {
    "energy_anomaly": energy_score,
    "power_factor": pf_score,
    "phase_imbalance": unbal_score,
    "thd_drift": thd_score,
    "overload": overload_score,
}

health_index = calculate_health_index(risk_scores)
```

## Output Files

| File | Description |
|------|-------------|
| `data/level1_raw_metrics_24h.csv` | Raw InfluxDB measurements (last 24h) |
| `data/level1_raw_metrics_7d.csv` | Raw InfluxDB measurements (last 7d) |
| `data/level1_raw_metrics_30d.csv` | Raw InfluxDB measurements (last 30d) |
| `data/level1_hourly_health_24h.csv` | Health scores (last 24h) |
| `data/level1_hourly_health_7d.csv` | Health scores (last 7d) |
| `data/level1_hourly_health_30d.csv` | Health scores (last 30d) |

### Output CSV Columns

```
timestamp,ahu_id,level,health_index,tier
energy_anomaly,pf_degradation,phase_imbalance,thd_drift,overload
power_total,power_factor,unbalance_pct,thd_24h,delta_kwh
data_quality_flag,safety_flags
z_energy,z_pf,z_imbalance,z_thd,z_overload
```

## Backend Integration

The FAIR scoring module can be integrated into the backend by:

1. Importing from `backend.core.fair_health_scoring`
2. Using the scoring functions in place of old fleet-comparison methods
3. Updating output schema to include z-scores and safety flags

### Example Integration

```python
from backend.core.fair_health_scoring import (
    score_energy_anomaly,
    score_power_factor,
    calculate_health_index,
)

# In generate_fleet_risk_assessment():
risk_scores = {
    "energy_anomaly": score_energy_anomaly(...),
    "power_factor": score_power_factor(...),
    # ...
}

health_index = calculate_health_index(risk_scores)
```

## Validation

All syntax checks pass:
```bash
$ python3 -m py_compile backend/core/fair_health_scoring.py && echo "OK"
Syntax OK

$ python3 -m py_compile backend/core/risk_engine.py && echo "OK"
Syntax OK

$ python3 -m py_compile scripts/generate_level1_health_scores.py && echo "OK"
Syntax OK
```

## Next Steps

1. **Deploy** to staging environment
2. **Validate** against known good scores
3. **Compare** old vs new scoring for discrepancies
4. **Update** frontend dashboard to display z-scores and safety flags
5. **Add** safety flag indicators in UI
