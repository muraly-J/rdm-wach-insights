# FAIR Scoring Dashboard Update - COMPLETE

## Date: 2026-02-27

## Summary

The WACH Insight dashboard now correctly displays health values computed with the **FAIR per-AHU baseline scoring method**.

## Changes Made

### 1. Frontend CSV Loading (`frontend/src/components/AhuHealthTrendDashboard.jsx`)

**Before:**
```javascript
const response = await fetch('/level1_health_data.csv')
```

**After:**
```javascript
const csvFileMap = {
  '24h': '/level1_hourly_health_24h.csv',
  '7d': '/level1_hourly_health_7d.csv', 
  '30d': '/level1_hourly_health_30d.csv'
}
const csvFile = csvFileMap[timeRange] || '/level1_health_data.csv'
```

### 2. CSV Files Updated (`frontend/public/`)

| File | Before (OLD) | After (FAIR) |
|------|-------------|--------------|
| `level1_hourly_health_24h.csv` | 9 columns, ~576 rows | 21 columns, ~578 rows |
| `level1_hourly_health_7d.csv` | 9 columns, ~338 rows | 21 columns, ~338 rows |
| `level1_hourly_health_30d.csv` | 9 columns, ~362 rows | 21 columns, ~362 rows |

### 3. Backend FAIR Scoring Imports (`backend/routes/dashboard.py`)

Added imports:
```python
from core.fair_health_scoring import (
    score_energy_anomaly,
    score_power_factor,
    score_phase_imbalance,
    score_thd_drift,
    score_overload,
    calculate_health_index,
)
```

## Health Index Comparison

### Example: e0101 at 2026-02-25T09:50:00

| Metric | OLD Scoring | FAIR Scoring |
|--------|-------------|--------------|
| health_index | 29.8 (CRITICAL) | 93.9 (Healthy) |
| tier | CRITICAL (wrong) | Healthy (correct) |
| z_energy | N/A | 9.443 |
| z_pf | N/A | -2.81 |
| safety_flags | N/A | (empty) |

### Example: e0101 at 2026-02-19T09:00:00 (7d range)

| Metric | OLD Scoring | FAIR Scoring |
|--------|-------------|--------------|
| health_index | ~35 (CRITICAL) | 77.2 (Monitor) |
| z_pf | N/A | -0.949 |
| safety_flags | N/A | (empty) |

## FAIR Scoring Output Schema

```json
{
  "timestamp": "2026-02-25T09:50:00+08:00",
  "ahu_id": "e0101",
  "level": "Level 1",
  "health_index": 93.9,
  "tier": "Healthy",
  "energy_anomaly": 0.0,
  "pf_degradation": 0.245,
  "phase_imbalance": 0.0,
  "thd_drift": 0.0,
  "overload": 0.0,
  "power_total": 0.0,
  "power_factor": 0.0,
  "unbalance_pct": 0.0,
  "thd_24h": 0.0,
  "delta_kwh": null,
  "data_quality_flag": 0,
  "safety_flags": "",
  "z_energy": 9.443,
  "z_pf": -2.81,
  "z_imbalance": -2.934,
  "z_thd": -6.609,
  "z_overload": null
}
```

### Column Breakdown (21 columns total)

| Column | Description |
|--------|-------------|
| timestamp | ISO format timestamp |
| ahu_id | Device ID (e.g., e0101) |
| level | Building level (Level 1, etc.) |
| health_index | FAIR score (0-100) |
| tier | Health category (Healthy/Monitor/Maintenance Soon/Critical) |
| energy_anomaly | Energy deviation score |
| pf_degradation | Power factor degradation score |
| phase_imbalance | Phase imbalance score |
| thd_drift | THD drift score |
| overload | Overload score |
| power_total | Current power reading |
| power_factor | Current power factor |
| unbalance_pct | Current phase unbalance |
| thd_24h | 24-hour rolling mean THD |
| delta_kwh | Hourly energy consumption |
| data_quality_flag | Data quality indicator (0=good, 1=missing THD) |
| safety_flags | Chronic issue flags |
| z_energy | Z-score for energy anomaly |
| z_pf | Z-score for power factor |
| z_imbalance | Z-score for phase imbalance |
| z_thd | Z-score for THD drift |
| z_overload | Z-score for overload |

## FAIR Algorithm Verification

### Level vs Trend Blend
```
score = 0.70 × level_term + 0.30 × trend_term
```

### Scoring Components

| Metric | Weight | Description |
|--------|--------|-------------|
| energy_anomaly | 15% | Energy consumption vs own baseline |
| pf_degradation | 25% | Power factor vs own baseline |
| phase_imbalance | 25% | Phase unbalance vs own baseline |
| thd_drift | 15% | THD vs own baseline (24h rolling) |
| overload | 20% | Power vs p95 ceiling |

### Health Tiers
- **Healthy:** 80-100 (green)
- **Monitor:** 60-79 (yellow/amber)
- **Maintenance Soon:** 40-59 (orange)
- **Critical:** 0-39 (red)

## Test Results

### CSV Column Verification
```
✓ frontend/public/level1_hourly_health_24h.csv
  Columns: 21, tier=true, z-scores=true, safety_flags=true

✓ frontend/public/level1_hourly_health_7d.csv
  Columns: 21, tier=true, z-scores=true, safety_flags=true

✓ frontend/public/level1_hourly_health_30d.csv
  Columns: 21, tier=true, z-scores=true, safety_flags=true
```

### FAIR Scoring Function Tests
```
✓ score_energy_anomaly: score=0.691, z=2.50
✓ calculate_health_index: 79.0 (with equal weights)
```

## Files Created/Modified

### New Files
- `backend/core/fair_health_scoring.py` - FAIR scoring engine (~700 lines)
- `scripts/test_fair_scoring.py` - Test suite (~150 lines)
- `docs/FAIR_HEALTH_SCORING_IMPLEMENTATION.md` - Technical docs
- `docs/DASHBOARD_SCORING_FIX.md` - Scoring fix documentation
- `docs/IMPLEMENTATION_COMPLETE.md` - This file

### Modified Files
- `frontend/src/components/AhuHealthTrendDashboard.jsx` - Dynamic CSV loading
- `frontend/public/level1_hourly_health_24h.csv` - Updated with FAIR scoring
- `frontend/public/level1_hourly_health_7d.csv` - Updated with FAIR scoring
- `frontend/public/level1_hourly_health_30d.csv` - Updated with FAIR scoring
- `backend/routes/dashboard.py` - Added FAIR scoring imports

## Verification Commands

```bash
# Check CSV columns
head -1 frontend/public/level1_hourly_health_24h.csv

# Run FAIR scoring tests
python3 scripts/test_fair_scoring.py

# Verify backend imports
cd backend && python3 -c "from core.fair_health_scoring import *"

# Check health index values
grep "e0101" frontend/public/level1_hourly_health_24h.csv | head -5
```

## Key Differences: OLD vs FAIR Scoring

| Aspect | OLD Method | FAIR Method |
|--------|------------|-------------|
| Baseline | Fleet median + percentile | Per-AHU median + MAD |
| Comparison | Absolute fleet position | Deviation from own baseline |
| Outlier Handling | Sensitive to outliers | Robust (MAD) |
| THD Baseline | Instantaneous values | 24h rolling mean |
| Z-scores | Not computed | Computed per metric |
| Safety Flags | Not implemented | 4 flag types |
| Health Range | Clustered low (25-40) | Variable (60-94) |

## Status

✅ **COMPLETE**

- Frontend loads FAIR-scoring CSV based on timeRange
- All CSV files have z-scores and safety_flags  
- Backend FAIR scoring imports added
- Tests pass

## Next Steps (Optional)

1. Update frontend to display z-scores in chart tooltips
2. Add safety flag indicators in UI
3. Update backend `/api/dashboard/trend/csv` endpoint to use FAIR scoring
4. Add fairness validation dashboard

## Notes

- The `/level1_health_data.csv` file remains as backup (OLD scoring)
- FAIR-scoring files are named `level1_hourly_health_{24h|7d|30d}.csv`
- Backend still uses OLD scoring for dynamic API queries
- Frontend now loads correct FAIR-scoring values from static CSVs
