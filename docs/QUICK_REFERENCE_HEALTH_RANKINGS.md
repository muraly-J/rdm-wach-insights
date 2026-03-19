# Health Rankings & Safety Flags - Quick Reference

## Overview

This feature adds **Health Rankings** (Top 5 best/worst devices) and **Safety Flags** (chronic condition detection) to the WACH Insight dashboard.

---

## Quick Links

| Component | Location |
|-----------|----------|
| Backend API | `backend/routes/dashboard.py` (lines 631-725) |
| Safety Flags Engine | `backend/core/risk_engine.py` (line ~1589) |
| Frontend Card | `frontend/src/components/dashboard/SafetyFlagsCombinedCard.tsx` |
| Health Rank Section | `frontend/src/components/dashboard/HealthRankSection.tsx` |

---

## API Endpoints

### GET /api/dashboard/ranking
```bash
curl "http://localhost:8081/api/dashboard/ranking?level=1&range=last_30d"
```
Returns Top 5 healthiest and Top 5 needs-attention devices.

### GET /api/dashboard/safety-flags (NEW)
```bash
curl "http://localhost:8081/api/dashboard/safety-flags?level=1&time_range=last_30d"
```
Returns safety flags per device.

### GET /api/dashboard/trend (MODIFIED)
```bash
curl "http://localhost:8081/api/dashboard/trend?level=1&range=7d"
```
Added `safety_flags` field to response.

---

## Safety Flags

| Flag ID | Metric | Threshold | Severity |
|---------|--------|-----------|----------|
| `THD_CHRONIC_HIGH` | composite_thd_24h | > 15.0% | High |
| `IMBALANCE_SEVERE` | current_unbalance | > 30.0% | High |
| `PF_CHRONIC_LOW` | power_factor_avg | < 0.50 | Moderate |
| `OVERLOAD_CHRONIC` | power_total/p95 | > 90% | High |

---

## Health Index Tiers

| Range | Tier | Color |
|-------|------|-------|
| 80-100 | Healthy | Green (#00E5A0) |
| 60-79 | Monitor | Amber (#FFB020) |
| 40-59 | Maintenance Soon | Orange (#FFA500) |
| 0-39 | Critical | Red (#FF4D6A) |

---

## File Checklist

### Backend
- [x] `backend/core/risk_engine.py` - SAFETY_FLAGS_DEF + compute_safety_flags()
- [x] `backend/routes/dashboard.py` - /api/dashboard/safety-flags endpoint
- [x] `backend/routes/dashboard.py` - Added safety_flags to trend response

### Frontend
- [x] `frontend/src/components/dashboard/SafetyFlagsCombinedCard.tsx` - NEW
- [x] `frontend/src/components/dashboard/HealthRankSection.tsx` - NEW
- [x] `frontend/src/App.tsx` - Added state and components
- [x] `frontend/src/api/client.ts` - Added fetch functions

### Documentation
- [x] `docs/implementation/HEALTH_RANKINGS_SAFETY_FLAGS.md` - COMPLETE
- [x] `docs/architecture/HEALTH_RANKINGS_ARCHITECTURE.md` - NEW
- [x] `docs/scoring/SAFETY_FLAGS_IMPLEMENTATION.md` - UPDATED

---

## Device Selection Logic

| View Type | Component Rendered |
|-----------|-------------------|
| "All AHUs" selected | HealthRankSection (Top 5 best/worst) |
| Single device selected | SafetyFlagsCombinedCard (flags for that device) |

---

## Testing Commands

```bash
# Verify backend syntax
python3 -m py_compile backend/routes/dashboard.py && echo "OK"

# Test safety flags function
python3 -c "
from backend.core.risk_engine import compute_safety_flags
metrics = {
  'thd': {'composite_24h_mean': 18.5},
  'phase_imbalance': {'current': 35.0},
  'power_factor': {'current': 0.45}
}
print(compute_safety_flags(metrics))
# Expected: ['THD_CHRONIC_HIGH', 'IMBALANCE_SEVERE', 'PF_CHRONIC_LOW']
"

# Test API endpoint
curl -s "http://localhost:8081/api/dashboard/safety-flags?level=1&time_range=last_30d" | jq

# Check CSV has safety_flags column
head -1 data/level1_hourly_health_30d.csv | tr ',' '\n' | grep safety_flags
```

---

## Common Tasks

### Add New Safety Flag

1. Update `SAFETY_FLAGS_DEF` in `risk_engine.py`
2. Add detection logic to `compute_safety_flags()`
3. Update frontend badge mapping in SafetyFlagsCombinedCard.tsx
4. Document threshold in this file

### Debug No Data

```bash
# Check backend is running
curl http://localhost:8081/api/levels

# Verify CSV exists
ls -la data/level1_hourly_health_30d.csv

# Check safety flags in CSV
grep "THD_CHRONIC_HIGH" data/level1_hourly_health_30d.csv
```

---

## API Response Examples

### Rankings Response
```json
{
  "level": "1",
  "time_range": "last_30d",
  "best": [
    {"ahu_id": "e0105", "index": 94.2, "tier": "Healthy"}
  ],
  "worst": [
    {"ahu_id": "e0112", "index": 38.5, "tier": "Critical"}
  ]
}
```

### Safety Flags Response
```json
{
  "level": "1",
  "time_range": "last_30d",
  "safety_flags": [
    {
      "ahu_id": "e0101",
      "flags": [
        {"flag_id": "THD_CHRONIC_HIGH", "label": "THD Critical", "severity": "High", "threshold": ">15.0%"}
      ]
    }
  ]
}
```

---

## Troubleshooting

### Issue: HealthRankSection shows "No health data available"

**Possible causes:**
1. CSV file missing for selected time range
2. Backend not running
3. Level has no devices

**Fix:**
```bash
# Verify CSV exists
ls -la data/level1_hourly_health_*.csv

# Restart backend
./start.sh
```

### Issue: SafetyFlagsCombinedCard shows wrong colors

**Check:** Severity mapping in component file
```typescript
// Should match:
'High' → Red (#FF4D6A)
'Moderate' → Amber (#FFB020)
```

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| `docs/implementation/HEALTH_RANKINGS_SAFETY_FLAGS.md` | Complete implementation guide |
| `docs/architecture/HEALTH_RANKINGS_ARCHITECTURE.md` | Architecture diagrams |
| `docs/scoring/SAFETY_FLAGS_IMPLEMENTATION.md` | Safety flags technical details |

---

**Last Updated**: March 11, 2026  
**Version**: 1.0
