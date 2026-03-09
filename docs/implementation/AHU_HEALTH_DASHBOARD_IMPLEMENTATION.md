# AHU Health Dashboard Implementation Summary

## Overview
This document summarizes the implementation of the AHU Health Trend Dashboard feature.

## Components Created/Modified

### 1. Backend API Endpoints (`backend/routes/dashboard.py`)

#### `/api/dashboard/trend`
- Returns health index and component scores for all AHUs on a specific level
- Supports time ranges: 24h, 7d, 30d
- Returns latest snapshot or series data

#### `/api/dashboard/trend/csv` (NEW)
- Same as trend endpoint but returns CSV format
- Includes all component scores: health_index, energy_score, pf_score, imbalance_score, thd_score, overload_score
- Used for chart data generation

### 2. Risk Engine (`backend/core/risk_engine.py`)

#### Fix: Energy Anomaly in risk_scores
- Added `energy_anomaly` field to the nested risk_scores dictionary
- Structure is now:
  ```json
  {
    "energy_anomaly": 0.28,
    "power_factor": {"score": 0.584, ...},
    "phase_imbalance": {"score": 1.0, ...},
    "thd_drift": {"score": 1.0, ...},
    "overload": {"score": 0.982, ...}
  }
  ```

### 3. Frontend Component (`frontend/src/components/AhuHealthTrendDashboard.jsx`)

#### Key Features:
- **6 Chart Display**: 
  - 1 Health Index chart (0-100 scale)
  - 5 Component Score charts (0-1 scale shown as percentage)

#### Health Index Chart (Top):
- Y-axis: 0-100 scale
- Horizontal reference lines at:
  - 80 (Healthy boundary)
  - 60 (Monitor boundary)  
  - 40 (Maintenance Soon boundary)
- Tier labels on right side
- Chart title: "Health Index"
- Weight displayed as "(weight null)"

#### Component Score Charts (Below):
- Y-axis: 0-1 scale shown as percentages
- Horizontal reference lines at:
  - 60% (High threshold)
  - 30% (Elevated threshold)
- Component name and weight displayed
- Examples:
  - Energy Anomaly (weight 0.15)
  - PF Degradation (weight 0.25)
  - Phase Imbalance (weight 0.25)
  - THD Drift (weight 0.15)
  - Overload (weight 0.20)

#### Pill-Based Device Selection:
- Row of device pills at top
- Click to isolate a specific AHU
- All other lines dim to near-invisible (opacity 0.15)
- Click again to release and show all
- Pill colors match device tier:
  - Green (#00c9b1) for Healthy
  - Orange (#f5a623) for Monitor
  - Red-Orange (#f5734e) for Maintenance Soon
  - Red (#ff4d6d) for Critical

#### Time Range Toggle:
- Buttons: 24h, 7d, 30d
- Switches data window
- Updates all charts simultaneously

### 4. Data Structure

#### CSV Output Format:
```csv
timestamp,ahu_id,health_index,energy_score,pf_score,imbalance_score,thd_score,overload_score
2026-02-25T14:00:42.225678,e0101,15.2,0.291,0.963,0.996,1.0,0.825
```

#### API Response Format:
```json
{
  "level": "1",
  "range": "24h",
  "ahus": ["e0101", "e0102", ...],
  "series": [
    {
      "timestamp": "2026-02-25T14:00:42.225678",
      "ahu_id": "e0101",
      "health_index": 15.2,
      "energy_score": 0.291,
      "pf_score": 0.963,
      "imbalance_score": 0.996,
      "thd_score": 1.0,
      "overload_score": 0.825
    }
  ],
  "latest_snapshot": {
    "e0101": 15.2
  }
}
```

### 5. Tier Color Mapping

| Tier | Color | Y-Axis Range |
|------|-------|--------------|
| Healthy | #00c9b1 (green) | 80-100 |
| Monitor | #f5a623 (orange) | 60-79 |
| Maintenance Soon | #f5734e (red-orange) | 40-59 |
| Critical | #ff4d6d (red) | 0-39 |

### 6. Usage

#### Access the Dashboard:
Navigate to the dashboard route in your application. The component is accessible at:

```
/dashboard/ahu-health-trend
```

#### Time Range Selection:
- **24h**: Shows hourly data for the last 24 hours
- **7d**: Shows daily averages for the last 7 days
- **30d**: Shows daily averages for the last 30 days

#### Device Filtering:
Click any device pill to isolate that AHU across all 6 graphs.
Click again to restore all devices.

### 7. Files Modified

| File | Description |
|------|-------------|
| `backend/routes/dashboard.py` | Added `/trend/csv` endpoint, fixed risk_scores structure |
| `backend/core/risk_engine.py` | Added energy_anomaly to risk_scores dict |
| `frontend/src/components/AhuHealthTrendDashboard.jsx` | New component with all charting logic |
| `generate_daily_health_index.py` | Utility script for generating daily health data |

### 8. Known Limitations

- For 7d and 30d ranges, the risk engine returns only daily averages
- Chart data is sparse for longer time ranges (1 point per day)
- Consider adding hourly aggregation if more granular data is needed

### 9. Future Enhancements

- Add export to CSV button for chart data
- Add trend prediction lines
- Add threshold violation markers
- Add comparison mode (multiple devices side-by-side)
- Add filter by tier
