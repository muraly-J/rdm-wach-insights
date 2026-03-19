# Safety Flags Implementation

## Overview

This document describes the **Safety Flags** feature added to the FAIR health scoring system.

## What Are Safety Flags?

Safety flags are **notification markers** that identify AHUs with chronically problematic electrical conditions. Unlike health index scores, safety flags are **not used in health calculation** - they are purely informational alerts.

## Flag Types

| Flag ID | Full Name | Condition | Severity |
|---------|-----------|-----------|----------|
| `THD_CHRONIC_HIGH` | THD Critical | median 24h-THD > 15% | High |
| `IMBALANCE_SEVERE` | Severe Imbalance | median unbalance > 30% | High |
| `PF_CHRONIC_LOW` | Low Power Factor | median PF < 0.50 | Moderate |
| `OVERLOAD_CHRONIC` | Overload Risk | median power > 90% of own p95 | High |

## FAIR Algorithm Integration

### Location: `backend/core/fair_health_scoring.py`

The safety flags are computed in the FAIR scoring module:

```python
# Flag definitions
SAFETY_FLAGS_DEF = {
    "THD_CHRONIC_HIGH":   ("composite_thd_24h", ">", 15.0),
    "IMBALANCE_SEVERE":   ("current_unbalance",  ">", 30.0),
    "PF_CHRONIC_LOW":     ("power_factor_avg",   "<",  0.50),
    "OVERLOAD_CHRONIC":   ("power_total",        ">",  None),  # computed separately
}
```

### Detection Logic

The `compute_safety_flags()` function evaluates metrics against thresholds:

```python
def compute_safety_flags(metrics: Dict) -> List[str]:
    """
    Evaluate AHU metrics against structural safety thresholds.
    
    Returns list of flag strings for this AHU.
    """
    flags = []

    # THD check
    thd_val = metrics.get("thd", {}).get("composite_24h_mean")
    if thd_val is not None and thd_val > 15.0:
        flags.append("THD_CHRONIC_HIGH")

    # Imbalance check
    unbal_val = metrics.get("phase_imbalance", {}).get("current")
    if unbal_val is not None and unbal_val > 30.0:
        flags.append("IMBALANCE_SEVERE")

    # PF check
    pf_val = metrics.get("power_factor", {}).get("current")
    if pf_val is not None and pf_val < 0.50:
        flags.append("PF_CHRONIC_LOW")

    # Overload check
    power_val = metrics.get("power", {}).get("current")
    historical_p95 = metrics.get("power", {}).get("historical_p95")
    if (power_val is not None and historical_p95 is not None
        and power_val / historical_p95 > 0.90):
        flags.append("OVERLOAD_CHRONIC")

    return flags
```

### Integration with Assessments

The safety_flags field is included in each assessment:

```json
{
  "ahu_id": "wach_e0101",
  "timestamp": "2026-03-10T14:00:00+08:00",
  "health_index": 72.5,
  "health_tier": "Monitor",
  "safety_flags": "THD_CHRONIC_HIGH,PF_CHRONIC_LOW",  // ← NEW FIELD
  ...
}
```

## CSV Output Format

The health scores CSV includes the `safety_flags` column:

```csv
timestamp,ahu_id,level,health_index,tier,
energy_anomaly,pf_degradation,phase_imbalance,thd_drift,overload,
power_total,power_factor,unbalance_pct,thd_24h,delta_kwh,
data_quality_flag,safety_flags
2026-03-10 14:00:00,e0101,Level 1,72.5,Monitor,
0.45,0.68,0.32,0.18,0.15,
7.5,0.89,2.1,3.8,15.2,
normal,THD_CHRONIC_HIGH
```

## Backend Dashboard Integration

The safety flags are exposed via the dashboard API:

### GET /api/dashboard/safety-flags (NEW)

**Endpoint**: `backend/routes/dashboard.py`

```python
@router.get("/safety-flags")
async def dashboard_safety_flags(
    level: str = Query(default="1", description="Building level (1-11)"),
    time_range: str = Query(default="last_30d", description="Time period to analyze")
):
```

**Response Format**:

```json
{
  "level": "1",
  "time_range": "last_30d",
  "generated_at": "2026-03-10T14:00:00+08:00",
  "safety_flags": [
    {
      "ahu_id": "e0101",
      "flags": [
        {"flag_id": "THD_CHRONIC_HIGH", "label": "THD Critical", "severity": "High", "threshold": ">15.0%"}
      ]
    },
    {
      "ahu_id": "e0102",
      "flags": []
    }
  ]
}
```

### Updated: GET /api/dashboard/trend

Added `safety_flags` field to response:

```json
{
  "level": "1",
  "range": "7d",
  "ahus": [...],
  "series": [...],
  "latest_snapshot": {...},
  "safety_flags": {
    "e0101": [
      {"flag_id": "THD_CHRONIC_HIGH", "label": "THD Critical", "severity": "High"}
    ],
    ...
  }
}
```

## Frontend Component Integration

### SafetyFlagsCombinedCard.tsx

**Location**: `frontend/src/components/dashboard/SafetyFlagsCombinedCard.tsx`

Renders safety flags for single device view with:

- Flag-specific icons (⚡, ⚖️, 📉, ⚠️)
- Severity color coding (High/Moderate/Low)
- Threshold display
- Severity badge (Critical/Warning/Info)

### HealthRankSection.tsx

**Location**: `frontend/src/components/dashboard/HealthRankSection.tsx`

Ranks devices by health index when "All AHUs" view is selected.

## Usage

### Generate Health Scores with Safety Flags

```bash
python scripts/generate_level1_health_scores.py --all-ranges
```

### Check Safety Flags in CSV

```bash
# List devices with safety flags
grep -v ',"",' data/level1_hourly_health_30d.csv | head

# Count flags per device
awk -F',' '{print $NF}' data/level1_hourly_health_30d.csv | sort | uniq -c
```

### Fetch Safety Flags via API

```bash
curl "http://localhost:8081/api/dashboard/safety-flags?level=1&time_range=last_30d"
```

## Severity Mapping

| Flag | Label | Badge | Color |
|------|-------|-------|-------|
| THD_CHRONIC_HIGH | THD Critical | Critical | Red |
| IMBALANCE_SEVERE | Severe Imbalance | Critical | Red |
| PF_CHRONIC_LOW | Low Power Factor | Warning | Amber |
| OVERLOAD_CHRONIC | Overload Risk | Critical | Red |

## Testing

### Unit Tests

```bash
python scripts/test_fair_scoring.py
```

Expected output:
```
Testing complete FAIR scoring scenario...
  Safety Flags: THD_CHRONIC_HIGH, PF_CHRONIC_LOW
  ✓ All safety flags computed correctly
```

### Integration Tests

1. Generate health scores CSV with safety_flags column
2. Verify CSV contains expected flags for known problematic devices
3. Check API endpoint returns correct flag format
4. Verify frontend renders flags with correct colors

## Known Limitations

1. **Threshold Values**: Flags use fixed thresholds - may need tuning per facility
2. **No History Tracking**: Flags don't track when they were introduced/resolved
3. **No Priority Ordering**: All flags displayed equally (may need severity sorting)

## Future Enhancements

1. **Configurable Thresholds**: Allow admin to adjust thresholds per facility
2. **Flag History**: Track emergence/dismissal dates
3. **Priority Sorting**: Sort by severity/priority
4. **Actionable Recommendations**: Link each flag to recommended actions

## Related Documentation

- [Health Rankings & Safety Flags Implementation](../implementation/HEALTH_RANKINGS_SAFETY_FLAGS.md)
- [FAIR Health Scoring Documentation](../scoring/FAIR_HEALTH_SCORING_DOCUMENTATION.md)
- [Architecture Diagrams](../architecture/HEALTH_RANKINGS_ARCHITECTURE.md)

---

**Last Updated**: March 11, 2026  
**Status**: ✅ Complete
