# Score Derivation Fix - Implementation Report

## Issue
The "Score Derivation" plots (showing raw data vs score relationships) were not visible in the frontend - only the header text appeared without any charts.

## Root Cause
The issue had two components:

### 1. Missing Raw Metric Columns in Daily CSV
The `health_daily.csv` file was generated without raw metric columns (`raw_power_total`, `raw_energy_import`, etc.), causing the score derivation endpoint to return empty data for 7d and 30d time ranges.

**Evidence:**
```bash
# Before fix:
$ head -1 data/health_daily.csv
timestamp,ahu_id,level,health_index,energy_anomaly,...  # Missing raw columns!
```

### 2. Time Range Filtering for 24h Used 3 Days Instead of 24 Hours
The `RANGE_DELTA['24h']` was set to `timedelta(days=3)` which is appropriate for daily data but incorrect for hourly data.

## Solution Implemented

### File: `backend/core/csv_reader.py`
1. **Fixed time range for 24h**: Changed from `timedelta(days=3)` to `timedelta(hours=24)`
2. **Added debug logging**: Added `DEBUG_MODE` flag and `_debug_csv_state()` function
3. **Improved validation**: Added column existence checks before processing
4. **Fixed dropna handling**: Added explicit copy() to avoid pandas warnings

### File: `scripts/etl/build_daily_csv.py`
1. **Added raw metric aggregation**: Added `RAW_METRIC_COLS` list with all raw column names
2. **Updated aggregation logic**: Now includes both score columns AND raw metric columns
3. **Updated rounding**: Includes raw metric columns in numeric column rounding
4. **Updated docstring**: Documents raw metric columns in output specification

## Data Files Status
- ✅ `health_all_levels.csv` - Already has all columns (source file)
- ✅ `health_hourly.csv` - Copies from health_all_levels, includes raw columns
- ✅ `health_daily.csv` - **Now includes raw metric columns** (fixed)

## Testing Results

### Backend API Test
```bash
$ CSV_DEBUG=true python3 -c "
from core.csv_reader import get_raw_score_relationship
print(get_raw_score_relationship('e0101', '7d'))
"
```
Output:
```
[DEBUG] After device filter: 31 rows
[DEBUG] After time filter: 6 rows
energy_anomaly: 6 data points
pf_degradation: 6 data points
phase_imbalance: 6 data points
thd_drift: 6 data points
overload: 6 data points
```

### API Endpoint Test
```bash
$ curl "http://localhost:8081/api/device/e0101/raw-score-relationship?range=7d&api_key=..."
Status: 200 OK
Scores returned: 5
```

### Unit Tests
```bash
$ pytest tests/test_csv_reader.py::test_raw_score_relationship_has_raw_and_score -v
PASSED
```

## Frontend Changes

### File: `frontend/src/components/dashboard/derivation/ScoreDerivationSection.tsx`
Added empty state handling:
- Shows warning card with yellow border when data is unavailable
- Displays which metric has no valid data points
- Prevents broken chart rendering

## Usage Instructions

### Regenerate Daily CSV (if needed)
```bash
cd /Users/rdmasia/wach-insight
python3 scripts/etl/build_daily_csv.py
```

### Enable Debug Logging
```bash
export CSV_DEBUG=true
# Or set in .env:
CSV_DEBUG=true
```

### Start Backend and Test
```bash
cd /Users/rdmasia/wach-insight
./start.sh

# Test endpoint directly:
curl "http://localhost:8081/api/device/e0101/raw-score-relationship?range=7d&api_key=dev-key-local-development"
```

## Files Modified
1. `backend/core/csv_reader.py` - Core fix + debug logging
2. `scripts/etl/build_daily_csv.py` - Raw metric column support
3. `frontend/src/components/dashboard/derivation/ScoreDerivationSection.tsx` - Empty state UI

## Verification Checklist
- [x] Daily CSV has raw metric columns
- [x] 24h time range uses correct window (24 hours)
- [x] Debug logging works when CSV_DEBUG=true
- [x] API endpoint returns 200 with data
- [x] All 5 scores have valid rawData and scoreData
- [x] Unit tests pass
- [x] Empty state UI implemented

## Notes
- The fix requires regenerating `health_daily.csv` using `build_daily_csv.py`
- Raw metrics are averaged when aggregating from hourly to daily data
- Debug mode logs each step of data filtering for troubleshooting
