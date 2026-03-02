# FAIR Health Scoring - Implementation Summary

## Date: 2026-02-27

## What Was Implemented

### 1. New FAIR Scoring Module
**File:** `backend/core/fair_health_scoring.py`

Complete standalone FAIR scoring engine with:
- **5 Scoring Functions:** energy_anomaly, power_factor, phase_imbalance, thd_drift, overload
- **Helper Functions:** robust_params (median + MAD), sigmoid_score, ols_slope
- **Baseline Builder:** build_baselines() for per-AHU baselines
- **Safety Flags:** compute_safety_flags() for chronic condition detection

### 2. Updated CSV Generation Script
**File:** `scripts/generate_level1_health_scores.py`

Changes:
- Added `power_p99` to baseline storage
- Added safety flag computation (4 flags: THD_CHRONIC_HIGH, IMBALANCE_SEVERE, PF_CHRONIC_LOW, OVERLOAD_CHRONIC)
- Updated output to include safety_flags column

### 3. Test Suite
**File:** `scripts/test_fair_scoring.py`

Comprehensive tests for:
- robust_params function
- sigmoid_score function  
- All 5 scoring functions
- Health index calculation
- Complete FAIR scoring scenario

### 4. Documentation
**Files:** 
- `docs/FAIR_HEALTH_SCORING_IMPLEMENTATION.md` - Full technical documentation
- `docs/IMPLEMENTATION_SUMMARY.md` - This file

## FAIR Algorithm Overview

### Core Principle
Each AHU is judged **entirely against its own historical baseline** - no fleet comparison.

### Scoring Formula
```
score = 0.70 × sigmoid_score(z × sensitivity) + 0.30 × sigmoid_score(max(0, ±slope_normalized) × 3.0)
```

Where:
- **Level Term (70%):** How far is current reading from THIS AHU's own median
- **Trend Term (30%):** Is this metric drifting in wrong direction over 7 days

### Health Index
```
health_index = 100 - penalty × 100
penalty = Σ(weight_i × score_i)

Weights:
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
| THD_CHRONIC_HIGH | median 24h-THD > 15% |
| IMBALANCE_SEVERE | median unbalance > 30% |
| PF_CHRONIC_LOW | median PF < 0.50 |
| OVERLOAD_CHRONIC | median power > 90% of own p95 |

## Output Schema

### CSV Columns
```
timestamp,ahu_id,level,health_index,tier,
energy_anomaly,pf_degradation,phase_imbalance,thd_drift,overload,
power_total,power_factor,unbalance_pct,thd_24h,delta_kwh,
data_quality_flag,safety_flags,
z_energy,z_pf,z_imbalance,z_thd,z_overload
```

### JSON Assessment Object
```json
{
  "timestamp": "2026-02-23T14:00:00+08:00",
  "ahu_id": "wach_e0101",
  "health_index": 84,
  "health_tier": "Healthy",
  "risk_scores": {
    "energy_anomaly": {"score": 0.15, ...},
    "power_factor": {"score": 0.25, ...},
    ...
  },
  // FAIR-specific fields
  "power_total": 7.5,
  "power_factor": 0.89,
  "unbalance_pct": 2.1,
  "thd_24h": 3.8,
  "delta_kwh": 15.2,
  "data_quality_flag": 0,
  "safety_flags": "",
  "z_energy": 0.5,
  "z_pf": -1.2,
  "z_imbalance": 0.8,
  "z_thd": -0.3,
  "z_overload": 1.5
}
```

## Test Results

All tests pass:
```
✓ robust_params([10, 12, 11]) → median=11.00, rstd=1.48
✓ sigmoid_score(0) = 0.0
✓ calculate_health_index(all zeros) = 100.0
✓ All scoring functions return (score, z) tuples
```

Test script output:
```
Testing complete FAIR scoring scenario...
  Energy anomaly:    score=0.691, z=2.50
  PF degradation:    score=0.700, z=3.50
  Phase imbalance:   score=0.675, z=2.00
  THD drift:         score=0.533, z=1.00
  Overload:          score=0.254, z=1.67

  Health Index: 42.2
  ✓ All z-scores verified
```

## Verification

```bash
# Syntax check
$ python3 -m py_compile backend/core/fair_health_scoring.py && echo "OK"

# Module import
$ python3 -c "from backend.core.fair_health_scoring import *" && echo "OK"

# Test suite
$ python3 scripts/test_fair_scoring.py

# Safety flag verification
$ grep -c "compute_safety_flags" scripts/generate_level1_health_scores.py
```

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `backend/core/fair_health_scoring.py` | ~700 | FAIR scoring engine |
| `scripts/test_fair_scoring.py` | ~150 | Test suite |
| `docs/FAIR_HEALTH_SCORING_IMPLEMENTATION.md` | ~300 | Technical docs |
| `docs/IMPLEMENTATION_SUMMARY.md` | ~150 | Summary doc |

## Files Modified

| File | Changes |
|------|---------|
| `scripts/generate_level1_health_scores.py` | Added safety flags, p99 column |
| `backend/core/risk_engine.py` | Added FAIR scoring functions (in parallel with old methods) |

## Usage

### Generate Health Scores
```bash
# All time ranges (24h, 7d, 30d)
python scripts/generate_level1_health_scores.py --all-ranges

# Specific range
python scripts/generate_level1_health_scores.py --range 24h
```

### Run Tests
```bash
python scripts/test_fair_scoring.py
```

### Import in Backend
```python
from backend.core.fair_health_scoring import (
    score_energy_anomaly,
    calculate_health_index,
)

# Score components
energy_score, z_energy = score_energy_anomaly(...)
health_index = calculate_health_index({...})
```

## Key Differences from Old Method

| Aspect | Old Method | New FAIR Method |
|--------|-----------|-----------------|
| Baseline | Fleet-wide median + percentile | Per-AHU median + MAD |
| Comparison | Absolute fleet position | Deviation from own baseline |
| Outlier Handling | Sensitive to outliers | Robust (MAD) |
| THD Baseline | Instantaneous values | 24h rolling mean |
| Load Discount | Applied (60% threshold) | Preserved |
| Z-scores | Not computed | Computed per metric |

## Benefits of FAIR Method

1. **Fairness:** Each AHU judged against its own history, not fleet
2. **Robustness:** MAD handles outliers better than std
3. **Interpretability:** Z-scores show how many SDs from baseline
4. **Thresholds:** No arbitrary fleet-wide thresholds needed
5. **Scalability:** Works equally well for 10 or 1000 AHUs

## Next Steps

1. Deploy to staging environment
2. Validate against known good scores
3. Compare old vs new scoring for discrepancies
4. Update frontend dashboard to display z-scores and safety flags
5. Add safety flag indicators in UI

## Validation Checklist

- [x] FAIR scoring module created (`fair_health_scoring.py`)
- [x] All 5 scoring functions implemented
- [x] Z-scores computed for all metrics
- [x] Safety flags added (4 flag types)
- [x] Health index calculation verified
- [x] Test suite passes
- [x] Syntax checks pass
- [x] Module imports successfully
- [x] CSV output includes safety_flags column
- [x] Documentation complete

## Status: ✅ COMPLETE

All implementation tasks completed successfully.
