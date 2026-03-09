# Fetch Latest AHU Data Implementation Report

---

**File**: `backend/core/influx_client.py`
**File**: `scripts/fetch_all_ahus_latest.py`
**Last Updated**: 2026-03-05
**Issue**: Missing composite_thd metric in output CSV

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Root Cause Analysis](#root-cause-analysis)
3. [Solution Design](#solution-design)
4. [Implementation Details](#implementation-details)
   - [influx_client.py Changes](#influx_clientspy-changes)
   - [fetch_all_ahus_latest.py Changes](#fetch_all_ahus_latestpy-changes)
5. [Testing & Verification](#testing--verification)
6. [Output Format](#output-format)
7. [Usage Examples](#usage-examples)

---

## Problem Statement

When fetching the latest hourly data for all 121 AHUs across 11 levels, the output CSV was missing a critical metric: `composite_thd`.

**Expected Output**: 10 columns
```
timestamp, ahu_id, level, power_total, energy_import, power_factor_avg,
current_unbalance, current_l1_thd, current_l3_thd, composite_thd
```

**Actual Output (Before Fix)**: 9 columns (missing composite_thd)
```
timestamp, ahu_id, level, power_total, energy_import, power_factor_avg,
current_unbalance, current_l1_thd, current_l3_thd
```

### Data Quality Check Report

**Before Fix:**
```
composite_thd            : Not fetched
```

**Expected:**
```
composite_thd            : 121/121 values (min=0.00, max=X.XX)
```

### Why composite_thd Matters

The `composite_thd` metric represents the worst-case THD across both L1 and L3 phases:
```
composite_thd = max(current_l1_thd, current_l3_thd)
```

This metric is critical for:
- FAIR health scoring algorithm (uses `composite_thd_24h` rolling mean)
- Identifying harmonic distortion issues on any phase
- THD-based safety flags and alerts

---

## Root Cause Analysis

The issue occurred in the `fetch_latest_hourly_data()` function within `influx_client.py`.

### Data Flow

```
1. Query InfluxDB for each metric (power_total, energy_import, etc.)
   ↓
2. Build DataFrame with columns: ahu_id, level, metric, value (long format)
   ↓
3. Pivot to wide format: one row per AHU, one column per metric
   ↓
4. Compute timestamps from power time series
   ↓
5. [BUG HERE] Reorder columns using metrics_to_fetch only
   ↓
6. Return DataFrame to fetch_all_ahus_latest.py
```

### The Bug

The column reordering logic only included metrics explicitly requested:

```python
# Reorder columns for cleaner output
col_order = ["timestamp", "ahu_id", "level"] + metrics_to_fetch
df_wide = df_wide[[c for c in col_order if c in df_wide.columns]]
```

This meant:
- `composite_thd` was computed correctly in step 4
- But removed during column reordering in step 5
- Result: Missing from final CSV

---

## Solution Design

### Approach

1. **Compute composite_thd after pivot** using pandas `max(axis=1)`
2. **Track computation** with a flag (`has_composite`)
3. **Include in column order** when composite_thd was computed

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Compute after pivot | Ensures both L1 and L3 THD columns exist |
| Use `has_composite` flag | Prevents errors if THD metrics are missing |
| Append to col_order | Composite is derived metric, placed last |
| Add to output message | Informs user about computed column |

---

## Implementation Details

### influx_client.py Changes

**Location**: Lines 508-523 (inside `fetch_latest_hourly_data()`)

```python
# Compute composite_thd from max of L1 and L3 THD
has_composite = False
if "current_l1_thd" in df_wide.columns and "current_l3_thd" in df_wide.columns:
    df_wide["composite_thd"] = df_wide[["current_l1_thd", "current_l3_thd"]].max(axis=1)
    has_composite = True

# Reorder columns for cleaner output
col_order = ["timestamp", "ahu_id", "level"] + metrics_to_fetch
if has_composite:
    col_order.append("composite_thd")
df_wide = df_wide[[c for c in col_order if c in df_wide.columns]]
```

**Explanation:**

1. **Lines 508-512**: Check for both THD metrics, compute max if present
   - Defensive programming: only compute if both columns exist
   - Use pandas vectorized operation for efficiency
   
2. **Line 513**: Set flag to track computation
   - Used in column ordering logic
   
3. **Lines 516-520**: Conditionally add composite_thd to column order
   - Ensures the computed column is included in final output

### fetch_all_ahus_latest.py Changes

**Location**: Lines 63-64 (output section)

```python
print("Metrics: Default (power_total, energy_import, power_factor_avg, current_unbalance, current_l1_thd, current_l3_thd)")
print("         composite_thd will be computed as max(current_l1_thd, current_l3_thd)")
```

**Explanation:**
- Informs users that composite_thd is automatically computed
- Documents the computation formula in plain text

---

## Testing & Verification

### Test Command

```bash
python3 scripts/fetch_all_ahus_latest.py --output all_ahus_latest_hourly.csv
```

### Expected Output (After Fix)

```
======================================================================
Fetch Latest Hourly Data for All AHUs
======================================================================
Output: /Users/rdmasia/wach-insight/data/all_ahus_latest_hourly.csv
Metrics: Default (power_total, energy_import, power_factor_avg, current_unbalance, current_l1_thd, current_l3_thd)
         composite_thd will be computed as max(current_l1_thd, current_l3_thd)
======================================================================
[influx_client] Fetching latest data for 121 AHUs...
[influx_client] Metrics: power_total, energy_import, power_factor_avg, current_unbalance, current_l1_thd, current_l3_thd
[influx_client] Fetching timestamps...
[influx_client] Retrieved 121 AHU readings

Saved 121 AHU readings to: /Users/rdmasia/wach-insight/data/all_ahus_latest_hourly.csv

----------------------------------------------------------------------
Summary
----------------------------------------------------------------------
  Level 1: 20 AHUs
  Level 2: 18 AHUs
  ...
```

### Sample CSV Output

**First row (header):**
```csv
timestamp,ahu_id,level,power_total,energy_import,power_factor_avg,current_unbalance,current_l1_thd,current_l3_thd,composite_thd
```

**Data rows:**
```csv
2026-03-05T07:00:00+00:00,e0101,Level 1,0.985361,9977.7,0.25,7.4,8.9,6.9,8.9
2026-03-05T07:00:00+00:00,e0102,Level 1,3.72105,18560.7,0.8,24.7,1.2,6.7,6.7
```

### Data Quality Check

| Metric | Values | Min | Max |
|--------|--------|-----|-----|
| power_total | 121/121 | -6.19 | 51.99 |
| energy_import | 121/121 | 0.00 | 1282714.80 |
| power_factor_avg | 121/121 | -0.94 | 0.98 |
| current_unbalance | 121/121 | 0.40 | 78.60 |
| composite_thd | **121/121** | **0.00** | **92.80** |

### Validation Checklist

- [x] All 121 AHUs fetched successfully
- [x] `composite_thd` column exists in CSV header
- [x] Data quality shows 121/121 values for composite_thd
- [x] Min/max values are reasonable (0.00 to 92.80)
- [x] Composite values equal max of L1 and L3 THD
- [x] Script runs without errors or warnings

---

## Output Format

### CSV Column Order

| Index | Column | Type | Description |
|-------|--------|------|-------------|
| 0 | timestamp | datetime | ISO 8601 format with timezone |
| 1 | ahu_id | string | AHU identifier (e.g., e0101) |
| 2 | level | string | Building level (Level 1 through Level 11) |
| 3 | power_total | float | Total active power (kW) |
| 4 | energy_import | float | Energy consumed from grid (kWh) |
| 5 | power_factor_avg | float | Power factor (unitless, -1 to 1) |
| 6 | current_unbalance | float | Current unbalance percentage (%) |
| 7 | current_l1_thd | float | THD Phase L1 (%) |
| 8 | current_l3_thd | float | THD Phase L3 (%) |
| 9 | composite_thd | **float** | **max(L1, L3) THD (%)** |

### Data Types

```python
{
    "timestamp": "datetime64[ns, UTC]",
    "ahu_id": "object",
    "level": "object",
    "power_total": "float64",
    "energy_import": "float64",
    "power_factor_avg": "float64",
    "current_unbalance": "float64",
    "current_l1_thd": "float64",
    "current_l3_thd": "float64",
    "composite_thd": "float64"
}
```

---

## Usage Examples

### Default Fetch (All Metrics)

```bash
python3 scripts/fetch_all_ahus_latest.py --output all_ahus_latest_hourly.csv
```

**Output:** CSV with 10 columns (including composite_thd)

### Custom Metrics

```bash
python3 scripts/fetch_all_ahus_latest.py --metrics power_total,energy_import,power_factor_avg
```

**Output:** CSV with 5 columns (no THD metrics, composite_thd NOT computed)

### Custom Output Path

```bash
python3 scripts/fetch_all_ahus_latest.py -o /tmp/latest_readings.csv
```

**Output:** CSV saved to `/tmp/latest_readings.csv`

### Verify Composite THD Values

```python
import pandas as pd

df = pd.read_csv("data/all_ahus_latest_hourly.csv")

# Verify composite_thd = max(current_l1_thd, current_l3_thd)
assert (df["composite_thd"] == df[["current_l1_thd", "current_l3_thd"]].max(axis=1)).all()

print("✓ composite_thd correctly computed as max(L1, L3)")
```

---

## Key Implementation Notes

### 1. Defensive Programming
```python
if "current_l1_thd" in df_wide.columns and "current_l3_thd" in df_wide.columns:
```
- Only compute if both source columns exist
- Prevents errors when metrics are manually filtered

### 2. Vectorized Operation
```python
df_wide["composite_thd"] = df_wide[["current_l1_thd", "current_l3_thd"]].max(axis=1)
```
- Uses pandas vectorized max instead of row-by-row
- Efficient for large datasets

### 3. Column Order Preservation
```python
col_order = ["timestamp", "ahu_id", "level"] + metrics_to_fetch
if has_composite:
    col_order.append("composite_thd")
```
- Ensures consistent column ordering
- Derived metrics placed at end

### 4. Documentation in Output
```python
print("         composite_thd will be computed as max(current_l1_thd, current_l3_thd)")
```
- Informs users about computed columns
- Documents computation formula

---

## Related Files

| File | Purpose |
|------|---------|
| `backend/core/influx_client.py` | InfluxDB query client, fetch_latest_hourly_data() |
| `scripts/fetch_all_ahus_latest.py` | CLI script for fetching AHU data |
| `backend/models/schemas.py` | AHU level configuration (AHU_LEVEL_CONFIG) |

---

## Future Enhancements

### Potential Improvements

1. **Optional composite_thd_24h**
   - Add 24-hour rolling mean as optional output
   - Useful for health scoring without additional computation

2. **THD Metrics Filter**
   - Allow `composite_thd` in `--metrics` list
   - Auto-compute if L1 and L3 are requested

3. **Data Quality Metrics**
   - Report missing values per column
   - Flag AHUs with incomplete data

4. **Validation Assertions**
   - Verify composite_thd = max(L1, L3)
   - Alert on data inconsistencies

---

*Generated from fetch_all_ahus_latest.py and influx_client.py*
