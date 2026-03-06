# Prediction ETL Implementation Report

**Date**: 2026-03-06  
**Status**: ✅ COMPLETE - All components implemented with level-by-level validation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Background](#background)
3. [Prediction Formula Overview](#prediction-formula-overview)
4. [Implementation Details](#implementation-details)
   - [Extract Phase](#extract-phase)
   - [Transform Phase](#transform-phase)
   - [Load Phase with Validation](#load-phase-with-validation)
5. [Level-by-Level Validation](#level-by-level-validation)
6. [Test Results](#test-results)
7. [CSV Output Schema](#csv-output-schema)
8. [Files Modified](#files-modified)
9. [Usage Guide](#usage-guide)

---

## Executive Summary

This report documents the implementation of a dedicated Prediction ETL pipeline that computes energy predictions for all AHUs using historical data comparison. The system:

1. **Fetches exact hourly values** at 4 time slots: `t`, `t-24h`, `t-168h`, `t-336h`
2. **Computes predicted energy** (`ŷ(t)`) as hourly average of historical values
3. **Calculates delta** (`ΔkWh`) = actual consumption − predicted consumption
4. **Validates device counts** per level against `AHU_LEVEL_CONFIG`

### Key Achievements

| Feature | Status | Notes |
|---------|--------|-------|
| Exact slot fetching (t-24h, t-168h, t-336h) | ✅ Implemented | Uses `fetch_prediction_data()` |
| Prediction formula (ŷ = avg of historical) | ✅ Implemented | 3-slot average |
| Delta calculation | ✅ Implemented | `ΔkWh = E(t) − ŷ(t)` |
| CSV output with all columns | ✅ Implemented | 9 columns, 121 rows |
| Level-by-level validation | ✅ Implemented | Validates against config |

### Output Verification

```
Level 1: 21/21 devices ✅
Level 2: 15/15 devices ✅
Level 3: 16/16 devices ✅
Level 4: 13/13 devices ✅
Level 5: 12/12 devices ✅
Level 6: 11/11 devices ✅
Level 7: 4/4 devices ✅
Level 8: 5/5 devices ✅
Level 9: 8/8 devices ✅
Level 10: 8/8 devices ✅
Level 11: 8/8 devices ✅

Total: 121 AHUs across all levels
```

---

## Background

### The Problem

The WACH Insight system needed a dedicated prediction ETL pipeline to:

| Requirement | Challenge |
|-------------|-----------|
| Energy forecasting | Need historical baseline for prediction |
| Anomaly detection | Compare actual vs predicted consumption |
| Multiple time slots | Fetch same hour from multiple days ago |

### Previous State

Before this implementation:
- ✅ Health scoring used historical data for scoring
- ❌ No dedicated prediction ETL pipeline
- ❌ Predictions not stored separately for analysis

### Requirements

1. **Fetch historical data**: `E(t)`, `E(t−24h)`, `E(t−168h)`, `E(t−336h)` from InfluxDB
2. **Compute prediction**: `ŷ(t) = avg(E(t−24h), E(t−168h), E(t−336h))`
3. **Calculate delta**: `ΔkWh = E(t) − ŷ(t)`
4. **Store predictions**: CSV with structured output
5. **Validate coverage**: Ensure all devices per level are present

---

## Prediction Formula Overview

### The 3-Step Process

```
┌────────────────────────────────────────────────────────────────────┐
│                    PREDICTION FORMULA                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Input: Energy readings at multiple historical points             │
│    • E(t)     = Current hour energy (kWh)                        │
│    • E(t−24h) = Same hour yesterday (kWh)                        │
│    • E(t−168h)= Same hour last week (kWh)                        │
│    • E(t−336h)= Same hour 2 weeks ago (kWh)                      │
│                                                                    │
│  Step 1: Fetch historical data from InfluxDB                      │
│    → Query each slot separately for all devices                   │
│    → Handle missing values gracefully                             │
│                                                                    │
│  Step 2: Compute prediction (ŷ)                                   │
│    → ŷ(t) = avg(E(t−24h), E(t−168h), E(t−336h))                 │
│    → Handle NaN by using available values                         │
│                                                                    │
│  Step 3: Compute delta (Δ)                                        │
│    → ΔkWh = E(t) − ŷ(t)                                           │
│    → Positive Δ = Higher than predicted (anomaly)                │
│    → Negative Δ = Lower than predicted                            │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Formula Components

| Component | Symbol | Definition |
|-----------|--------|------------|
| Current energy | `E(t)` | Energy consumed in current hour |
| Yesterday energy | `E(t−24h)` | Same hour, previous day |
| Last week energy | `E(t−168h)` | Same hour, 7 days ago |
| Two weeks ago | `E(t−336h)` | Same hour, 14 days ago |
| Predicted energy | `ŷ(t)` | Average of historical values |
| Energy delta | `ΔkWh` | Deviation from prediction |

---

## Implementation Details

### File: `scripts/run_prediction_etl.py`

**Line**: 0-532 (new file with validation)  
**Status**: ✅ Complete implementation

#### Step 1: EXTRACT - Fetch Prediction Data

```python
def extract_prediction_data(device_ids: list[str]) -> pd.DataFrame:
    """
    Fetch current and historical energy values from InfluxDB.
    
    Args:
        device_ids: List of AHU IDs to fetch
        
    Returns:
        DataFrame with columns:
          - ahu_id, level
          - energy_current: E(t) at current hour
          - yesterday_kwh: E(t-24h)
          - last_week_kwh: E(t-168h)
          - two_weeks_kwh: E(t-336h)
    """
```

**Key Implementation Details**:
- Calls `fetch_prediction_data()` from `influx_client.py`
- Queries 4 separate time slots for each device
- Returns wide-format DataFrame (one row per AHU)
- Handles missing values with `pd.Series().mean()` which ignores NaN

#### Step 2: TRANSFORM - Compute Predictions

```python
def transform_predictions(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Compute ŷ(t) and ΔkWh from historical values.
    
    Args:
        df_raw: DataFrame with E(t), E(t-24h), E(t-168h), E(t-336h)
        
    Returns:
        DataFrame with added columns:
          - predicted_kwh: ŷ(t) = avg(historical)
          - delta_kwh: ΔkWh = energy_current − predicted_kwh
    """
```

**Prediction Formula**:
```python
# Compute predicted energy as average of historical values
df['predicted_kwh'] = df[['yesterday_kwh', 'last_week_kwh', 'two_weeks_kwh']].mean(axis=1)

# Compute delta (deviation from prediction)
df['delta_kwh'] = df['energy_current'] - df['predicted_kwh']
```

**Output Statistics** (Level 1 test run):
- Energy Current: 86,219.82 kWh (σ=274,906)
- Predicted: 85,057.67 kWh (σ=273,759)
- Delta: 1,162.14 kWh (σ=1,294)
- All 21 devices: 100% above prediction

#### Step 3: LOAD - Write to CSV with Validation

```python
def load_to_csv(df_predictions: pd.DataFrame, output_path=None, dry_run=False):
    """
    Write predictions to CSV file.
    
    Args:
        df_predictions: DataFrame with all prediction columns
        output_path: Custom output path (default: data/predictions.csv)
        dry_run: If True, don't write file
        
    Returns:
        Number of rows written
    """
```

**Overwrite Behavior** (Fixed for this task):
```python
# ALWAYS overwrite existing file to prevent duplicates
mode = 'w'  # Was: mode = 'a' if file_exists else 'w'
header = True
```

### Level-by-Level Validation Function

```python
def validate_level_results(df_results: pd.DataFrame, level_num: int) -> bool:
    """
    Validate that all devices for a level are present in results.
    
    Args:
        df_results: DataFrame with prediction results
        level_num: Level number (1-11)
        
    Returns:
        True if all devices match, False otherwise
    """
```

**Validation Logic**:
```python
# Get expected devices from AHU_LEVEL_CONFIG
expected_device_ids = get_devices_by_level(level_num)
actual_device_ids = df_results['ahu_id'].unique().tolist()

# Compare sets
expected_set = set(expected_device_ids)
actual_set = set(actual_device_ids)

missing = sorted(list(expected_set - actual_set))
extra = sorted(list(actual_set - expected_set))

# Report and return pass/fail
print(f"Level {level_num}: {actual_count}/{expected_count} devices")
return actual_count == expected_count
```

---

## Level-by-Level Validation

### Validation Output (All Levels)

```
======================================================================
VALIDATION SUMMARY
======================================================================

  [PASS] Level 1: 21/21 devices

  [PASS] Level 2: 15/15 devices

  [PASS] Level 3: 16/16 devices

  [PASS] Level 4: 13/13 devices

  [PASS] Level 5: 12/12 devices

  [PASS] Level 6: 11/11 devices

  [PASS] Level 7: 4/4 devices

  [PASS] Level 8: 5/5 devices

  [PASS] Level 9: 8/8 devices

  [PASS] Level 10: 8/8 devices

  [PASS] Level 11: 8/8 devices

======================================================================
[OK] All levels passed validation
======================================================================
```

### Device Counts by Level (from `AHU_LEVEL_CONFIG`)

| Level | Expected | Actual | Status |
|-------|----------|--------|--------|
| 1 | e0101-e0121, e0212 | 21 | ✅ |
| 2 | e0201-e0218 (skip e0219) | 15 | ✅ |
| 3 | e0210, e0211, e03xx | 16 | ✅ |
| 4 | e04xx (skip some) | 13 | ✅ |
| 5 | e05xx, e0622 | 12 | ✅ |
| 6 | e06xx (skip some) | 11 | ✅ |
| 7 | e07xx | 4 | ✅ |
| 8 | e08xx | 5 | ✅ |
| 9 | e09xx | 8 | ✅ |
| 10 | e10xx | 8 | ✅ |
| 11 | e11xx | 8 | ✅ |

**Total**: 121 AHUs

---

## Test Results

### Test Run 1: Level 1 Only

```bash
$ python3 scripts/run_prediction_etl.py --level 1
```

**Output**:
```
======================================================================
PREDICTION ETL PIPELINE
======================================================================

[INFO] Processing Level 1 (21 AHUs)

======================================================================
STEP 1: EXTRACT - Fetching Prediction Data from InfluxDB
======================================================================
[OK] Retrieved prediction data for 21 AHUs

======================================================================
STEP 2: TRANSFORM - Computing Predictions
======================================================================

[OK] Computed predictions for 21 AHUs

    Summary Statistics:
      Energy Current: 86,219.82 kWh (σ=274,906)
      Predicted (ŷ): 85,057.67 kWh (σ=273,759)
      Delta (Δ): 1,162.14 kWh (σ=1,294)

      Devices with valid prediction: 21/21
      Devices above prediction: 21 (100.0%)

======================================================================
STEP 3: LOAD - Writing to predictions.csv
======================================================================
[OK] Overwritten CSV with 21 rows

======================================================================
VALIDATION SUMMARY
======================================================================

  [PASS] Level 1: 21/21 devices

======================================================================
[OK] ETL Complete: 21 rows written to data/predictions.csv
```

### Test Run 2: All Levels

```bash
$ python3 scripts/run_prediction_etl.py
```

**Output**:
```
======================================================================
PREDICTION ETL PIPELINE
======================================================================

[INFO] Processing all levels (121 AHUs)

======================================================================
STEP 1: EXTRACT - Fetching Prediction Data from InfluxDB
======================================================================
[OK] Retrieved prediction data for 121 AHUs

======================================================================
STEP 2: TRANSFORM - Computing Predictions
======================================================================

[OK] Computed predictions for 121 AHUs

    Summary Statistics:
      Energy Current: 39,423.56 kWh (σ=115,751)
      Predicted (ŷ): 38,427.38 kWh (σ=115,193)
      Delta (Δ): 996.18 kWh (σ=829)

======================================================================
VALIDATION SUMMARY
======================================================================

  [PASS] Level 1: 21/21 devices ✅
  [PASS] Level 2: 15/15 devices ✅
  ...
  [PASS] Level 11: 8/8 devices ✅

======================================================================
[OK] ETL Complete: 121 rows written to data/predictions.csv
```

### CSV Verification

```bash
$ head -5 data/predictions.csv
timestamp,ahu_id,level,energy_current,predicted_kwh,delta_kwh,yesterday_kwh,last_week_kwh,two_weeks_kwh
2026-03-06T02:15:18+00:00,e0101,Level 1,10000.98,9783.42,217.56,9966.85,9797.22,9586.19
...

$ wc -l data/predictions.csv
     122 data/predictions.csv

$ python3 -c "import pandas as pd; df = pd.read_csv('data/predictions.csv'); print(df['level'].value_counts())"
Level 1     21
Level 2     15
Level 3     16
Level 4     13
Level 5     12
Level 6     11
Level 7      4
Level 8      5
Level 9      8
Level 10     8
Level 11     8
Name: level, dtype: int64
```

---

## CSV Output Schema

### File Location
```
data/predictions.csv
```

### Column Definitions

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | ISO 8601 | Current hour timestamp (e.g., `2026-03-06T02:15:18+00:00`) |
| `ahu_id` | string | AHU identifier (e.g., `e0101`) |
| `level` | string | Building level (e.g., `Level 1`) |
| `energy_current` | float | Current hour energy consumption (kWh) |
| `predicted_kwh` | float | Predicted energy: ŷ(t) = avg(historical) |
| `delta_kwh` | float | Deviation: ΔkWh = energy_current − predicted_kwh |
| `yesterday_kwh` | float | Same hour yesterday (E(t−24h)) |
| `last_week_kwh` | float | Same hour last week (E(t−168h)) |
| `two_weeks_kwh` | float | Same hour 2 weeks ago (E(t−336h)) |

### Example Row

```
timestamp,ahu_id,level,energy_current,predicted_kwh,delta_kwh,yesterday_kwh,last_week_kwh,two_weeks_kwh
2026-03-06T02:15:18+00:00,e0101,Level 1,10000.98,9783.42,217.56,9966.85,9797.22,9586.19
```

**Interpretation**:
- Current consumption: 10,000.98 kWh
- Predicted (average): 9,783.42 kWh
- Deviation: +217.56 kWh (2.2% higher than predicted)
- Historical data: All 3 slots available

---

## Files Modified

### New File Created
| File | Lines | Description |
|------|-------|-------------|
| `scripts/run_prediction_etl.py` | 532 | Dedicated prediction ETL pipeline with validation |

### Modified Files
| File | Change | Purpose |
|------|--------|---------|
| `backend/core/influx_client.py` | ~10 lines | Added `fetch_prediction_data()` function |

### Validation Function Addition
| Location | Lines | Function |
|----------|-------|----------|
| `scripts/run_prediction_etl.py` | 312-340 | `validate_level_results()` |
| `scripts/run_prediction_etl.py` | 382-410 | Integrated validation in ETL |

---

## Usage Guide

### Run Prediction ETL for Level 1 Only

```bash
cd /Users/rdmasia/wach-insight
python3 scripts/run_prediction_etl.py --level 1
```

**Output**:
- CSV file: `data/predictions.csv` (21 rows)
- Console: Validation summary for Level 1

### Run Prediction ETL for All Levels

```bash
cd /Users/rdmasia/wach-insight
python3 scripts/run_prediction_etl.py
```

**Output**:
- CSV file: `data/predictions.csv` (121 rows)
- Console: Validation summary for all 11 levels

### Dry Run (No File Writing)

```bash
cd /Users/rdmasia/wach-insight
python3 scripts/run_prediction_etl.py --dry-run
```

**Output**:
- No CSV written
- Console shows what would be processed

### Custom Output Path

```bash
cd /Users/rdmasia/wach-insight
python3 scripts/run_prediction_etl.py --output data/predictions_backup.csv
```

**Output**:
- CSV file at custom path

### Verify Results with Python

```python
import pandas as pd

df = pd.read_csv('data/predictions.csv')

# Check device counts per level
print(df['level'].value_counts().sort_index())

# Check Level 1 specifically
level1 = df[df['level'] == 'Level 1']
print(f"Level 1 devices: {len(level1)}")

# Check for missing predictions (delta should exist)
print(f"Missing delta: {df['delta_kwh'].isna().sum()}")

# Stats by level
print(df.groupby('level')['delta_kwh'].describe())
```

---

## Summary

### Final Checklist

| Task | Status |
|------|--------|
| Implement prediction formula: fetch E(t), E(t−24h), E(t−168h), E(t−336h) | ✅ |
| Compute ŷ(t) = avg(historical values) | ✅ |
| Calculate ΔkWh = energy_current − predicted_kwh | ✅ |
| Output CSV with all required columns | ✅ |
| Overwrite mode (no duplicates) | ✅ |
| Level-by-level validation against config | ✅ |
| All 121 AHUs across 11 levels validated | ✅ |

### Key Metrics

| Metric | Value |
|--------|-------|
| Total AHUs processed | 121 |
| Levels validated | 11/11 (100%) |
| Devices per level | Match AHU_LEVEL_CONFIG exactly |
| CSV columns | 9 (all required) |
| Validation pass rate | 100% |

### Future Enhancements

1. **Prediction confidence interval**: Add min/max historical range
2. **Anomaly flagging**: Mark large positive/negative deltas
3. **Historical archive**: Store predictions with timestamps for trend analysis
4. **Per-level summary**: Generate statistics per building level
