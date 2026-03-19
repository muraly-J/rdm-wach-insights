# CSV File Formats: Health Index Data

## Overview

The WACH Insight system stores health index data in two CSV files with different granularities:

| File | Purpose | Granularity | Retention |
|------|---------|-------------|-----------|
| `data/health_hourly.csv` | 24h chart data | Hourly | 30 days |
| `data/health_all_levels.csv` | 7d/30d charts | Daily | Indefinite |

---

## File Schemas

### 1. health_hourly.csv (Hourly Granularity)

**Primary Key**: `(timestamp, ahu_id)`

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| `timestamp` | datetime | Hourly timestamp (ISO 8601) | UTC+8 timezone |
| `ahu_id` | string | Device identifier (e.g., e0101) | Pattern: `e<level><num>` |
| `level` | string | Level label (Level 1, Level 2, etc.) | Matches device prefix |
| `health_index` | float | Health score (0-100) | 1 decimal place |
| `tier` | string | Health tier category | Healthy/Monitor/Maintenance Soon/Critical |
| `energy_anomaly` | float | Energy anomaly score (0-1) | 4 decimal places |
| `pf_degradation` | float | Power factor degradation (0-1) | 4 decimal places |
| `phase_imbalance` | float | Phase imbalance score (0-1) | 4 decimal places |
| `thd_drift` | float | THD drift score (0-1) | 4 decimal places |
| `overload` | float | Overload risk score (0-1) | 4 decimal places |
| `raw_power_total` | float | Current power (kW) | 2 decimal places |
| `raw_energy_import` | float | Energy imported (kWh) | 2 decimal places |
| `raw_power_factor_avg` | float | Power factor (0-1) | 4 decimal places |
| `raw_current_unbalance` | float | Current unbalance (%) | 2 decimal places |
| `raw_composite_thd` | float | THD with 24h rolling mean (%) | 4 decimal places |
| `baseline_power_median` | float | Power baseline median | 2 decimal places |
| `baseline_power_rstd` | float | Power baseline MAD-std | 4 decimal places |
| `baseline_power_p5` | float | Power baseline 5th percentile | 2 decimal places |
| `baseline_power_p25` | float | Power baseline 25th percentile | 2 decimal places |
| `baseline_power_p75` | float | Power baseline 75th percentile | 2 decimal places |
| `baseline_power_p95` | float | Power baseline 95th percentile | 2 decimal places |
| `baseline_energy_median` | float | Energy delta baseline median | 4 decimal places |
| `baseline_energy_rstd` | float | Energy delta baseline MAD-std | 4 decimal places |
| `baseline_energy_p5` | float | Energy baseline 5th percentile | 4 decimal places |
| `baseline_energy_p25` | float | Energy baseline 25th percentile | 4 decimal places |
| `baseline_energy_p75` | float | Energy baseline 75th percentile | 4 decimal places |
| `baseline_energy_p95` | float | Energy baseline 95th percentile | 4 decimal places |
| `baseline_pf_median` | float | PF baseline median | 4 decimal places |
| `baseline_pf_rstd` | float | PF baseline MAD-std | 4 decimal places |
| `baseline_pf_p5` | float | PF baseline 5th percentile | 4 decimal places |
| `baseline_pf_p25` | float | PF baseline 25th percentile | 4 decimal places |
| `baseline_pf_p75` | float | PF baseline 75th percentile | 4 decimal places |
| `baseline_pf_p95` | float | PF baseline 95th percentile | 4 decimal places |
| `baseline_unbalance_median` | float | Unbalance baseline median | 4 decimal places |
| `baseline_unbalance_rstd` | float | Unbalance baseline MAD-std | 4 decimal places |
| `baseline_unbalance_p5` | float | Unbalance baseline 5th percentile | 4 decimal places |
| `baseline_unbalance_p25` | float | Unbalance baseline 25th percentile | 4 decimal places |
| `baseline_unbalance_p75` | float | Unbalance baseline 75th percentile | 4 decimal places |
| `baseline_unbalance_p95` | float | Unbalance baseline 95th percentile | 4 decimal places |
| `safety_flags` | string | Semicolon-separated flags | e.g., "THD_CHRONIC_HIGH;OVERLOAD_CHRONIC" |

**Total Columns**: 41

---

### 2. health_all_levels.csv (Daily Aggregation)

**Primary Key**: `(date, ahu_id)`

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| `timestamp` | datetime | Daily timestamp (ISO 8601) | UTC+8, typically end-of-day |
| `ahu_id` | string | Device identifier (e.g., e0101) | Pattern: `e<level><num>` |
| `level` | string | Level label (Level 1, Level 2, etc.) | Matches device prefix |
| `health_index` | float | Health score (0-100) | 1 decimal place |
| `tier` | string | Health tier category | Healthy/Monitor/Maintenance Soon/Critical |
| `energy_anomaly` | float | Energy anomaly score (0-1) | 4 decimal places |
| `pf_degradation` | float | Power factor degradation (0-1) | 4 decimal places |
| `phase_imbalance` | float | Phase imbalance score (0-1) | 4 decimal places |
| `thd_drift` | float | THD drift score (0-1) | 4 decimal places |
| `overload` | float | Overload risk score (0-1) | 4 decimal places |
| `raw_power_total` | float | Power at timestamp (kW) | 2 decimal places |
| `raw_energy_import` | float | Energy imported (kWh) | 2 decimal places |
| `raw_power_factor_avg` | float | Power factor (0-1) | 4 decimal places |
| `raw_current_unbalance` | float | Current unbalance (%) | 2 decimal places |
| `raw_composite_thd` | float | THD with 24h rolling mean (%) | 4 decimal places |
| `safety_flags` | string | Semicolon-separated flags | e.g., "THD_CHRONIC_HIGH" |

**Total Columns**: 23

**Key Difference from hourly**: Fewer baseline statistics columns since daily aggregation pre-computes these.

---

## Health Index Calculation

### Formula

```
Health Index = 100 - (weighted_penalty × 100)

where weighted_penalty =
    energy_anomaly     × 0.15
    + pf_degradation   × 0.25
    + phase_imbalance  × 0.25
    + thd_drift        × 0.15
    + overload         × 0.20
```

### Component Scores (Each: 0 to 1)

| Metric | Weight | Formula |
|--------|--------|---------|
| Energy Anomaly | 0.15 | `sigmoid_score(z × sensitivity)` |
| PF Degradation | 0.25 | `sigmoid_score((median - pf) / rstd × sensitivity)` |
| Phase Imbalance | 0.25 | `sigmoid_score((unbal - median) / rstd × sensitivity)` |
| THD Drift | 0.15 | `sigmoid_score((thd - median) / rstd × sensitivity)` |
| Overload | 0.20 | `sigmoid_score(power/p95 × 8 - 1) + ...` |

### Score → Health Index Mapping

| Weighted Penalty | Health Index | Tier |
|------------------|--------------|------|
| 0.0 - 0.2 | 100 - 80 | Healthy |
| 0.2 - 0.4 | 80 - 60 | Monitor |
| 0.4 - 0.6 | 60 - 40 | Maintenance Soon |
| > 0.6 | < 40 | Critical |

---

## Tier Definitions

| Tier | Range | Color | Action |
|------|-------|-------|--------|
| **Healthy** | 80 - 100 | Green (#00E5A0) | Normal operation |
| **Monitor** | 60 - 79 | Amber (#FFB020) | Observe for trends |
| **Maintenance Soon** | 40 - 59 | Orange (#FFA500) | Schedule maintenance |
| **Critical** | 0 - 39 | Red (#FF4D6A) | Immediate action required |

---

## Safety Flags

### Flag Definitions

| Flag ID | Metric | Threshold | Severity |
|---------|--------|-----------|----------|
| `THD_CHRONIC_HIGH` | composite_thd_24h > | 15.0% | High |
| `IMBALANCE_SEVERE` | current_unbalance > | 30.0% | High |
| `PF_CHRONIC_LOW` | power_factor_avg < | 0.50 | Moderate |
| `OVERLOAD_CHRONIC` | power_total / p95 > | 0.90 (90%) | High |

### Safety Flags Format

```csv
# Example: Multiple flags separated by semicolon
safety_flags
THD_CHRONIC_HIGH;OVERLOAD_CHRONIC
IMBALANCE_SEVERE
PF_CHRONIC_LOW
```

**Empty string** means no safety flags detected.

---

## File Format Examples

### Sample health_hourly.csv (First 5 rows)

```csv
timestamp,ahu_id,level,health_index,tier,energy_anomaly,pf_degradation,phase_imbalance,thd_drift,overload,raw_power_total,raw_energy_import,raw_power_factor_avg,raw_current_unbalance,raw_composite_thd,baseline_power_median,baseline_power_rstd,baseline_power_p5,baseline_power_p25,baseline_power_p75,baseline_power_p95,baseline_energy_median,baseline_energy_rstd,baseline_energy_p5,baseline_energy_p25,baseline_energy_p75,baseline_energy_p95,baseline_pf_median,baseline_pf_rstd,baseline_pf_p5,baseline_pf_p25,baseline_pf_p75,baseline_pf_p95,baseline_unbalance_median,baseline_unbalance_rstd,baseline_unbalance_p5,baseline_unbalance_p25,baseline_unbalance_p75,baseline_unbalance_p95,safety_flags
2026-03-10 14:00:00+08:00,e0101,Level 1,95.2,Healthy,0.12,0.08,0.15,0.20,0.30,45.23,12.45,0.92,2.34,8.56,42.15,5.23,35.02,38.92,46.15,51.72,0.85,0.12,0.62,0.72,0.98,1.05,0.91,0.03,0.86,0.89,0.94,0.97,2.15,0.34,1.67,1.89,2.45,2.89,
2026-03-10 13:00:00+08:00,e0101,Level 1,96.1,Healthy,0.08,0.10,0.12,0.18,0.25,43.12,12.30,0.93,2.18,8.23,42.15,5.23,35.02,38.92,46.15,51.72,0.83,0.11,0.60,0.70,0.95,1.02,0.92,0.03,0.87,0.90,0.95,0.98,2.12,0.32,1.65,1.87,2.42,2.85,
2026-03-10 12:00:00+08:00,e0101,Level 1,97.3,Healthy,0.05,0.06,0.10,0.12,0.20,41.05,12.15,0.94,2.05,7.89,42.15,5.23,35.02,38.92,46.15,51.72,0.81,0.10,0.58,0.68,0.92,0.98,0.93,0.02,0.88,0.91,0.96,0.99,2.08,0.30,1.62,1.84,2.38,2.82,
2026-03-10 14:00:00+08:00,e0105,Level 1,82.5,Monitor,0.45,0.35,0.30,0.25,0.15,89.34,23.15,0.78,12.34,12.45,85.12,10.25,75.23,82.45,91.23,100.12,2.15,0.45,1.89,2.12,3.45,4.12,0.76,0.08,0.68,0.75,0.85,0.92,12.34,1.25,10.23,11.45,14.23,16.89,THD_CHRONIC_HIGH
2026-03-10 13:00:00+08:00,e0105,Level 1,78.2,Monitor,0.55,0.42,0.38,0.32,0.18,95.67,24.50,0.72,15.67,14.32,85.12,10.25,75.23,82.45,91.23,100.12,2.35,0.52,2.12,2.45,3.89,4.67,0.71,0.10,0.62,0.70,0.82,0.89,15.67,1.45,12.34,13.89,17.23,20.45,THD_CHRONIC_HIGH
```

### Sample health_all_levels.csv (First 3 rows)

```csv
timestamp,ahu_id,level,health_index,tier,energy_anomaly,pf_degradation,phase_imbalance,thd_drift,overload,raw_power_total,raw_energy_import,raw_power_factor_avg,raw_current_unbalance,raw_composite_thd,safety_flags
2026-03-10 14:00:00+08:00,e0101,Level 1,95.2,Healthy,0.12,0.08,0.15,0.20,0.30,45.23,12.45,0.92,2.34,8.56,
2026-03-10 14:00:00+08:00,e0105,Level 1,82.5,Monitor,0.45,0.35,0.30,0.25,0.15,89.34,23.15,0.78,12.34,12.45,THD_CHRONIC_HIGH
2026-03-10 14:00:00+08:00,e0207,Level 2,67.8,Monitor,0.35,0.42,0.28,0.35,0.32,72.34,18.67,0.85,8.45,9.23,
```

---

## Data Type Definitions

### Numeric Types

| Type | Precision | Example |
|------|-----------|---------|
| integer | Whole number | `42`, `156` |
| float | 2-4 decimal places | `45.23`, `0.9178` |
| boolean | True/False | `true`, `false` |

### String Types

| Type | Format | Example |
|------|--------|---------|
| device_id | e<level><num> | `e0101`, `e1112` |
| level | Level N | `Level 1`, `Level 11` |
| tier | Enum | `Healthy`, `Monitor`, `Maintenance Soon`, `Critical` |

### Timestamp Format

```
ISO 8601 with UTC+8 timezone:
2026-03-10 14:00:00+08:00

# When parsed in Python:
pd.to_datetime(df['timestamp'], utc=True)

# Output to API (ISO 8601):
row['timestamp'].isoformat()
```

---

## Retention Policies

### health_hourly.csv

| Policy | Value |
|--------|-------|
| **Retention** | 30 days |
| **Update Frequency** | Every 30 minutes (ETL run) |
| **Data Points per Day** | 24 per AHU |
| **Max Size (50 AHUs)** | ~2.1 MB |

**Cleanup Script:**
```python
import pandas as pd
from datetime import datetime, timedelta

df = pd.read_csv('data/health_hourly.csv', parse_dates=['timestamp'])
cutoff = datetime.now() - timedelta(days=30)
df = df[df['timestamp'] >= cutoff]
df.to_csv('data/health_hourly.csv', index=False)
print(f"Cleaned data older than 30 days. Rows remaining: {len(df)}")
```

### health_all_levels.csv

| Policy | Value |
|--------|-------|
| **Retention** | Indefinite (archival) |
| **Update Frequency** | Every 30 minutes (ETL run) |
| **Data Points per Day** | 1 per AHU |
| **Current Size (365 days)** | ~7.8 MB |

**Archival Strategy:**
- Keep all data for trend analysis
- Consider partitioning by year after 2+ years
- Backup to S3/GCS for compliance

---

## Schema Evolution

### Version History

| Version | Changes | Date |
|---------|---------|------|
| v1.0 | Initial schema with 23 columns (daily) | March 5, 2026 |
| v2.0 | Added baseline statistics (18 columns) for hourly CSV | March 12, 2026 |

### Migration Path: v1 → v2

**If upgrading from v1 (health_all_levels.csv only):**

```bash
# 1. Run ETL with --output-hourly flag
python scripts/etl/run_health_etl.py --output-hourly

# This generates health_hourly.csv with baseline statistics
```

**New columns added in v2:**
- `baseline_power_median`, `_rstd`, `_p5`, `_p25`, `_p75`, `_p95`
- `baseline_energy_median`, `_rstd`, `_p5`, `_p25`, `_p75`, `_p95`
- `baseline_pf_median`, `_rstd`, `_p5`, `_p25`, `_p75`, `_p95`
- `baseline_unbalance_median`, `_rstd`, `_p5`, `_p25`, `_p75`, `_p95`

---

## Validation Rules

### Required Fields (Non-nullable)

| Column | Null Allowed |
|--------|--------------|
| `timestamp` | ❌ No |
| `ahu_id` | ❌ No |
| `level` | ❌ No |
| `health_index` | ❌ No |

### Optional Fields (Nullable)

| Column | Default |
|--------|---------|
| `safety_flags` | Empty string |
| All baseline_ columns | 0.0 or NaN |

---

## CSV File Generation

### ETL Output (run_health_etl.py)

```python
# Generate daily CSV
python scripts/etl/run_health_etl.py

# Generate hourly CSV (new in v2)
python scripts/etl/run_health_etl.py --output-hourly

# Generate both (default behavior)
python scripts/etl/run_health_etl.py --output-hourly
```

### Historical ETL Output (history_generator.py)

```bash
# One-shot historical generation
python scripts/etl/history_generator.py --level all

# Output files:
# - data/predictions.csv (intermediate)
# - data/health_all_levels.csv
# - data/health_hourly.csv
```

---

## Schema Verification Script

```python
#!/usr/bin/env python3
"""Verify CSV schema matches expected structure."""

import pandas as pd
import sys

HOURLY_COLUMNS = [
    'timestamp', 'ahu_id', 'level', 'health_index', 'tier',
    'energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload',
    'raw_power_total', 'raw_energy_import', 'raw_power_factor_avg',
    'raw_current_unbalance', 'raw_composite_thd',
    # Baseline statistics (hourly only)
    'baseline_power_median', 'baseline_power_rstd',
    'baseline_power_p5', 'baseline_power_p25', 'baseline_power_p75', 'baseline_power_p95',
    'baseline_energy_median', 'baseline_energy_rstd',
    'baseline_energy_p5', 'baseline_energy_p25', 'baseline_energy_p75', 'baseline_energy_p95',
    'baseline_pf_median', 'baseline_pf_rstd',
    'baseline_pf_p5', 'baseline_pf_p25', 'baseline_pf_p75', 'baseline_pf_p95',
    'baseline_unbalance_median', 'baseline_unbalance_rstd',
    'baseline_unbalance_p5', 'baseline_unbalance_p25', 'baseline_unbalance_p75', 'baseline_unbalance_p95',
    'safety_flags'
]

DAILY_COLUMNS = [
    'timestamp', 'ahu_id', 'level', 'health_index', 'tier',
    'energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload',
    'raw_power_total', 'raw_energy_import', 'raw_power_factor_avg',
    'raw_current_unbalance', 'raw_composite_thd',
    'safety_flags'
]

def verify_csv(filepath, expected_columns):
    """Verify CSV has all required columns."""
    try:
        df = pd.read_csv(filepath, nrows=1)
        missing = set(expected_columns) - set(df.columns)
        extra = set(df.columns) - set(expected_columns)
        
        if missing:
            print(f"❌ Missing columns in {filepath}:")
            for col in sorted(missing):
                print(f"   - {col}")
            return False
        
        if extra:
            print(f"⚠️  Extra columns in {filepath}:")
            for col in sorted(extra):
                print(f"   + {col}")
        
        print(f"✅ Schema valid: {filepath}")
        return True
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return False

if __name__ == "__main__":
    verify_csv('data/health_hourly.csv', HOURLY_COLUMNS)
    verify_csv('data/health_all_levels.csv', DAILY_COLUMNS)
```

---

## Common Operations

### Append Data to Existing CSV

```python
import pandas as pd

# Read existing
df_existing = pd.read_csv('data/health_hourly.csv', parse_dates=['timestamp'])

# Read new data
df_new = pd.read_csv('new_data.csv', parse_dates=['timestamp'])

# Combine and deduplicate
df_combined = pd.concat([df_existing, df_new], ignore_index=True)
df_combined = df_combined.drop_duplicates(subset=['timestamp', 'ahu_id'], keep='last')

# Save
df_combined.to_csv('data/health_hourly.csv', index=False)
```

### Query Last N Rows per AHU

```python
import pandas as pd

df = pd.read_csv('data/health_hourly.csv', parse_dates=['timestamp'])

# Get last 24 readings per AHU
latest_per_ahu = (
    df.sort_values('timestamp')
    .groupby('ahu_id')
    .tail(24)
)

print(f"Latest data for {latest_per_ahu['ahu_id'].nunique()} AHUs")
```

### Export Specific Time Range

```python
import pandas as pd
from datetime import datetime, timedelta

df = pd.read_csv('data/health_hourly.csv', parse_dates=['timestamp'])

# Filter to last 24 hours
cutoff = datetime.now() - timedelta(hours=24)
df_filtered = df[df['timestamp'] >= cutoff]

# Export
df_filtered.to_csv('export_24h.csv', index=False)
print(f"Exported {len(df_filtered)} rows")
```

---

**Last Updated**: March 12, 2026
**Author**: WACH Insight Team
**Version**: 2.0
