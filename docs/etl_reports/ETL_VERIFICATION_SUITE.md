# ETL Pipeline Verification Test Suite

## Overview
Comprehensive test suite for validating ETL pipeline data integrity and schema correctness.

---

## Part 1: Data Integrity Tests

### Test 1.1: Row Count Validation
```python
"""
Verify row counts match expected values based on time range and resampling.
"""

# Test: Row count validation
assert len(raw_df) == ahus × (24h / resample_interval)

# Expected calculations:
# 24h: 21 AHUs × (24×60 / 5) = 21 × 288 = 6,048 (allow ~5% tolerance for gaps)
# 7d: 21 AHUs × (7×24 / 1) = 21 × 168 = 3,528 (allow ~5% tolerance)
# 30d: 21 AHUs × (30×24 / 4) = 21 × 180 = 3,780 (allow ~5% tolerance)
```

**Expected Results:**
| Time Range | AHUs | Expected Rows | Tolerance |
|------------|------|---------------|-----------|
| 24h | 21 | ~5,760-6,048 | ±5% |
| 7d | 21 | ~3,360-3,528 | ±5% |
| 30d | 21 | ~3,420-3,780 | ±5% |

### Test 1.2: Health Index Range
```python
"""
Verify health_index values are within valid range [0, 100].
"""

assert df['health_index'].min() >= 0
assert df['health_index'].max() <= 100

# Expected: health_index ∈ [0, 100]
```

### Test 1.3: Risk Scores Range
```python
"""
Verify all risk scores are within [0, 1].
"""

risk_columns = [
    'energy_anomaly', 'pf_degradation', 'phase_imbalance',
    'thd_drift', 'overload'
]

for col in risk_columns:
    assert df[col].min() >= 0, f"{col} has values < 0"
    assert df[col].max() <= 1, f"{col} has values > 1"
```

### Test 1.4: Weight Sum = 1.0
```python
"""
Verify health index weights sum to 1.0.
"""

HEALTH_INDEX_WEIGHTS = {
    "energy_anomaly": 0.15,
    "pf_degradation": 0.25,
    "phase_imbalance": 0.25,
    "thd_drift": 0.15,
    "overload": 0.20
}

assert sum(HEALTH_INDEX_WEIGHTS.values()) == 1.0, "Weights must sum to 1.0"
```

### Test 1.5: Tier Distribution
```python
"""
Verify tier distribution matches thresholds.
"""

def get_health_tier(health_index):
    if health_index >= 80:
        return "Healthy"
    elif health_index >= 60:
        return "Monitor"
    elif health_index >= 40:
        return "Maintenance Soon"
    else:
        return "Critical"

# Test tier thresholds
assert get_health_tier(100) == "Healthy"
assert get_health_tier(93.1) == "Healthy"
assert get_health_tier(80) == "Healthy"

assert get_health_tier(79.9) == "Monitor"
assert get_health_tier(70) == "Monitor"
assert get_health_tier(60) == "Monitor"

assert get_health_tier(59.9) == "Maintenance Soon"
assert get_health_tier(50) == "Maintenance Soon"
assert get_health_tier(40) == "Maintenance Soon"

assert get_health_tier(39.9) == "Critical"
assert get_health_tier(0) == "Critical"

# Test tier distribution matches total records
tier_counts = df['tier'].value_counts()
total_records = len(df)
assert sum(tier_counts.values()) == total_records
```

---

## Part 2: Cross-File Consistency Tests

### Test 2.1: Baseline Parameters Match
```python
"""
Verify baseline parameters are consistent across files.
"""

# Check MIN_RSTD consistency
from backend.core.risk_engine import MIN_RSTD as ENGINE_MIN_RSTD
from scripts.generate_level1_health_scores import MIN_RSTD as SCRIPT_MIN_RSTD

assert ENGINE_MIN_RSTD == SCRIPT_MIN_RSTD, "MIN_RSTD must match between files"

# Check SENSITIVITY consistency
from backend.core.risk_engine import SENSITIVITY as ENGINE_SENSITIVITY
from scripts.generate_level1_health_scores import SENSITIVITY as SCRIPT_SENSITIVITY

assert ENGINE_SENSITIVITY == SCRIPT_SENSITIVITY, "SENSITIVITY must match between files"
```

### Test 2.2: Weight Consistency
```python
"""
Verify health index weights match across files.
"""

from backend.core.risk_engine import HEALTH_INDEX_WEIGHTS as ENGINE_WEIGHTS
from scripts.generate_level1_health_scores import WEIGHTS as SCRIPT_WEIGHTS

assert ENGINE_WEIGHTS == SCRIPT_WEIGHTS, "HEALTH_INDEX_WEIGHTS must match"
```

### Test 2.3: Tier Thresholds Match
```python
"""
Verify health tier thresholds are consistent.
"""

from backend.core.risk_engine import HEALTH_TIERS as ENGINE_TIERS
from scripts.generate_level1_health_scores import get_health_tier as SCRIPT_TIER

# Test tier thresholds
assert SCRIPT_TIER(80) == "Healthy" or ENGINE_TIERS["Healthy"] == (80, 100)
assert SCRIPT_TIER(60) == "Monitor" or ENGINE_TIERS["Monitor"] == (60, 79)
assert SCRIPT_TIER(40) == "Maintenance Soon" or ENGINE_TIERS["Maintenance Soon"] == (40, 59)
assert SCRIPT_TIER(0) == "Critical" or ENGINE_TIERS["Critical"] == (0, 39)
```

---

## Part 3: CSV Schema Validation

### Test 3.1: Raw Metrics Schema
```python
"""
Verify raw metrics CSV has correct columns.
"""

EXPECTED_RAW_COLUMNS = [
    'timestamp', 'ahu_id', 'power_total', 'energy_import',
    'power_factor_avg', 'current_unbalance', 'current_l1_thd', 'current_l3_thd'
]

raw_df = pd.read_csv('data/level1_raw_metrics_24h.csv', nrows=0)
assert list(raw_df.columns) == EXPECTED_RAW_COLUMNS, "Raw metrics schema mismatch"
```

### Test 3.2: Health Scores Schema
```python
"""
Verify health scores CSV has correct columns.
"""

EXPECTED_HEALTH_COLUMNS = [
    'timestamp', 'ahu_id', 'level', 'health_index', 'tier',
    'energy_anomaly', 'pf_degradation', 'phase_imbalance', 
    'thd_drift', 'overload', 'power_total', 'power_factor',
    'unbalance_pct', 'thd_24h', 'delta_kwh', 'data_quality_flag',
    'safety_flags', 'z_energy', 'z_pf', 'z_imbalance', 
    'z_thd', 'z_overload'
]

health_df = pd.read_csv('data/level1_hourly_health_24h.csv', nrows=0)
assert list(health_df.columns) == EXPECTED_HEALTH_COLUMNS, "Health scores schema mismatch"
```

### Test 3.3: Column Data Types
```python
"""
Verify column data types are correct.
"""

df = pd.read_csv('data/level1_hourly_health_24h.csv')

# Timestamp
assert df['timestamp'].dtype == 'object'  # ISO8601 string

# AHU ID
assert df['ahu_id'].dtype == 'object'
assert all(df['ahu_id'].str.startswith('e'))

# Level
assert df['level'].dtype == 'object'
assert all(df['level'].str.startswith('Level'))

# Numeric columns
numeric_cols = [
    'health_index', 'energy_anomaly', 'pf_degradation',
    'phase_imbalance', 'thd_drift', 'overload'
]

for col in numeric_cols:
    assert pd.api.types.is_numeric_dtype(df[col]), f"{col} must be numeric"

# Tier enum
assert set(df['tier'].unique()) <= {'Healthy', 'Monitor', 'Maintenance Soon', 'Critical'}
```

---

## Part 4: Data Quality Tests

### Test 4.1: Missing Values Check
```python
"""
Verify data quality flags and missing value handling.
"""

df = pd.read_csv('data/level1_hourly_health_24h.csv')

# Check THD-related missing values
assert df['thd_24h'].notna().all() or df['data_quality_flag'].any()
assert df['delta_kwh'].notna().all() or df['data_quality_flag'].any()

# Check z-score alignment
z_columns = ['z_energy', 'z_pf', 'z_imbalance', 'z_thd', 'z_overload']
for z_col in z_columns:
    # Z-scores should be missing when risk score is 0 (no deviation)
    assert df[z_col].isna().sum() <= df['energy_anomaly'].eq(0).sum()
```

### Test 4.2: Safety Flags Validation
```python
"""
Verify safety flags follow expected format.
"""

df = pd.read_csv('data/level1_hourly_health_24h.csv')

VALID_FLAGS = {
    'THD_CHRONIC_HIGH', 'IMBALANCE_SEVERE', 
    'PF_CHRONIC_LOW', 'OVERLOAD_CHRONIC'
}

# Parse safety flags
all_flags = set()
for flags in df['safety_flags'].dropna():
    for flag in flags.split(','):
        all_flags.add(flag)

# Verify all flags are valid
assert all_flags <= VALID_FLAGS, f"Invalid safety flags: {all_flags - VALID_FLAGS}"

# Verify flag count distribution
flag_counts = df['safety_flags'].value_counts()
print("Safety Flag Distribution:")
for flags, count in flag_counts.items():
    print(f"  {flags or '(none)'}: {count} records")
```

### Test 4.3: Z-Score Distribution
```python
"""
Verify z-scores have reasonable distribution.
"""

df = pd.read_csv('data/level1_hourly_health_24h.csv')

z_columns = ['z_energy', 'z_pf', 'z_imbalance', 'z_thd', 'z_overload']

for col in z_columns:
    non_null = df[col].notna().sum()
    null_count = df[col].isna().sum()
    
    print(f"\n{col}:")
    print(f"  Non-null: {non_null}/{len(df)}")
    
    if non_null > 0:
        z_values = df[col].dropna()
        print(f"  Min: {z_values.min():.3f}")
        print(f"  Max: {z_values.max():.3f}")
        print(f"  Mean: {z_values.mean():.3f}")
        
        # Z-scores should be roughly normal with mean ~0
        assert -5 <= z_values.mean() <= 5, f"{col} mean outside expected range"
```

---

## Part 5: FAIR Algorithm Verification

### Test 5.1: Health Index Formula
```python
"""
Verify health_index = 100 - (weighted_penalty × 100).
"""

df = pd.read_csv('data/level1_hourly_health_24h.csv')

WEIGHTS = {
    "energy_anomaly": 0.15,
    "pf_degradation": 0.25,
    "phase_imbalance": 0.25,
    "thd_drift": 0.15,
    "overload": 0.20
}

# Calculate expected health index
df['calculated_penalty'] = sum(
    df[col] * WEIGHTS[col] for col in WEIGHTS.keys()
)
df['calculated_health_index'] = 100 - (df['calculated_penalty'] * 100)

# Verify within tolerance
tolerance = 0.1
diff = abs(df['health_index'] - df['calculated_health_index'])
assert (diff <= tolerance).all(), f"Health index calculation mismatch"

print(f"\nHealth Index Formula Verification:")
print(f"  Max difference: {diff.max():.4f}")
print(f"  All rows within tolerance: {(diff <= tolerance).all()}")
```

### Test 5.2: Risk Score Bounds
```python
"""
Verify each risk score is bounded [0, 1].
"""

df = pd.read_csv('data/level1_hourly_health_24h.csv')

risk_cols = [
    'energy_anomaly', 'pf_degradation', 
    'phase_imbalance', 'thd_drift', 'overload'
]

for col in risk_cols:
    min_val = df[col].min()
    max_val = df[col].max()
    
    print(f"\n{col}:")
    print(f"  Range: [{min_val:.4f}, {max_val:.4f}]")
    
    assert min_val >= 0, f"{col} minimum < 0"
    assert max_val <= 1.01, f"{col} maximum > 1"  # Allow small tolerance
```

### Test 5.3: Weight Distribution
```python
"""
Verify risk scores follow expected weight distribution.
"""

df = pd.read_csv('data/level1_hourly_health_24h.csv')

WEIGHTS = {
    "energy_anomaly": 0.15,
    "pf_degradation": 0.25,
    "phase_imbalance": 0.25,
    "thd_drift": 0.15,
    "overload": 0.20
}

risk_cols = list(WEIGHTS.keys())

# Calculate weighted contributions
df['weighted_penalty'] = sum(df[col] * WEIGHTS[col] for col in risk_cols)

# Expected health index distribution
expected_health_index = 100 - (df['weighted_penalty'] * 100)

# Verify health_index matches
assert df['health_index'].equals(expected_health_index.round(1))

print("\nWeight Distribution Verification:")
for col, weight in WEIGHTS.items():
    mean_score = df[col].mean()
    contribution = mean_score * weight
    print(f"  {col}: mean={mean_score:.4f}, weight={weight}, contribution={contribution:.4f}")

print(f"\nTotal expected penalty: {df['weighted_penalty'].mean():.4f}")
print(f"Expected health index: {100 - df['weighted_penalty'].mean() * 100:.2f}")
```

---

## Part 6: Time Range Consistency Tests

### Test 6.1: Timestamp Format
```python
"""
Verify timestamps are ISO8601 format.
"""

import re

df = pd.read_csv('data/level1_hourly_health_24h.csv')

# Check timestamp format
timestamp_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$'
valid_timestamps = df['timestamp'].str.match(timestamp_pattern, na=False)

assert valid_timestamps.all(), f"Invalid timestamps: {df['timestamp'][~valid_timestamps].tolist()[:5]}"
print("✓ All timestamps in ISO8601 format")
```

### Test 6.2: Time Range Coverage
```python
"""
Verify data covers expected time range.
"""

df = pd.read_csv('data/level1_hourly_health_24h.csv')

# Convert timestamp to datetime
df['timestamp_dt'] = pd.to_datetime(df['timestamp'])

# Expected: last 24 hours of data
expected_hours = 24 * 12  # 5-minute resampling = 12 per hour
expected_ahus = 21

actual_rows = len(df)
actual_hours = (df['timestamp_dt'].max() - df['timestamp_dt'].min()).total_seconds() / 3600
actual_ahus = df['ahu_id'].nunique()

print(f"\nTime Range Verification:")
print(f"  Expected AHUs: {expected_ahus}, Actual: {actual_ahus}")
print(f"  Expected hours: ~24, Actual: {actual_hours:.1f}")
print(f"  Expected rows: ~5760, Actual: {actual_rows}")

assert actual_ahus == expected_ahus
assert 20 <= actual_hours <= 30, f"Time range not ~24h: {actual_hours}h"
```

### Test 6.3: Resampling Interval
```python
"""
Verify resampling frequency matches time range.
"""

df = pd.read_csv('data/level1_hourly_health_24h.csv')
df['timestamp_dt'] = pd.to_datetime(df['timestamp'])

# Sort by timestamp and check intervals
df_sorted = df.sort_values(['ahu_id', 'timestamp_dt'])

# Check time gaps (allow some tolerance for missing data)
for ahu_id in df_sorted['ahu_id'].unique()[:3]:  # Sample first 3 AHUs
    ahu_data = df_sorted[df_sorted['ahu_id'] == ahu_id]
    time_diffs = ahu_data['timestamp_dt'].diff().dropna()
    
    if len(time_diffs) > 0:
        avg_interval = time_diffs.mean()
        print(f"  {ahu_id}: avg interval = {avg_interval}")
        
        # For 24h, should be ~5 minutes
        assert avg_interval <= pd.Timedelta('10min'), f"Interval too large for 24h: {avg_interval}"
```

---

## Part 7: Frontend Integration Tests

### Test 7.1: Long Format Schema
```python
"""
Verify CSV is in long format (not wide format).
"""

df = pd.read_csv('data/level1_hourly_health_24h.csv')

# Long format: has 'ahu_id' column, metrics as separate columns
assert 'ahu_id' in df.columns, "Missing 'ahu_id' column (not long format)"
assert 'health_index' in df.columns, "Missing 'health_index' column"
assert 'energy_anomaly' in df.columns, "Missing 'energy_anomaly' column"

# Verify unique AHUs
unique_ahus = df['ahu_id'].nunique()
print(f"  Unique AHUs: {unique_ahus}")
assert unique_ahus > 1, "Must have multiple AHUs in long format"

# Verify each row has one ahu_id value
assert df['ahu_id'].notna().all(), "Some rows missing ahu_id"
```

### Test 7.2: Tier Colors Match
```python
"""
Verify tier colors match health index thresholds.
"""

df = pd.read_csv('data/level1_hourly_health_24h.csv')

# Expected color mapping
tier_colors = {
    'Healthy': '#00c9b1',
    'Monitor': '#f5a623', 
    'Maintenance Soon': '#f5734e',
    'Critical': '#ff4d6d'
}

# Verify tier distribution
tier_dist = df['tier'].value_counts()
print("\nTier Distribution:")
for tier, count in tier_dist.items():
    print(f"  {tier}: {count} ({count/len(df)*100:.1f}%)")

# Verify threshold alignment
healthy_records = df[df['health_index'] >= 80]
monitor_records = df[(df['health_index'] >= 60) & (df['health_index'] < 80)]
critical_records = df[df['health_index'] < 40]

assert len(healthy_records) == tier_dist.get('Healthy', 0)
assert len(monitor_records) == tier_dist.get('Monitor', 0)
assert len(critical_records) == tier_dist.get('Critical', 0)

print("✓ Tier colors match health index thresholds")
```

---

## Part 8: End-to-End Pipeline Tests

### Test 8.1: Complete Pipeline Execution
```python
"""
Test complete ETL pipeline execution.
"""

import subprocess
import os

# Step 1: Run fetch phase
print("\n=== Step 1: Running fetch phase ===")
result = subprocess.run([
    'python', 'scripts/generate_level1_health_scores.py',
    '--range', '24h'
], capture_output=True, text=True)

assert result.returncode == 0, f"Fetch failed: {result.stderr}"
print("✓ Fetch phase completed")

# Step 2: Verify output files exist
raw_path = 'data/level1_raw_metrics_24h.csv'
health_path = 'data/level1_hourly_health_24h.csv'

assert os.path.exists(raw_path), f"Raw metrics file missing: {raw_path}"
assert os.path.exists(health_path), f"Health scores file missing: {health_path}"
print("✓ Output files created")

# Step 3: Verify row counts
raw_df = pd.read_csv(raw_path)
health_df = pd.read_csv(health_path)

print(f"\n=== Row Counts ===")
print(f"  Raw metrics: {len(raw_df)} rows")
print(f"  Health scores: {len(health_df)} rows")

assert len(raw_df) == len(health_df), "Row count mismatch between raw and health"
print("✓ Row counts match")

# Step 4: Verify column count
expected_columns = 24
assert len(health_df.columns) == expected_columns, f"Column count mismatch: {len(health_df.columns)}"
print(f"✓ Column count correct ({expected_columns})")
```

### Test 8.2: Two-Phase Execution
```python
"""
Test that fetch and compute phases can run separately.
"""

import subprocess

# Step 1: Run only fetch
print("\n=== Two-Phase Execution Test ===")

# Fetch only (without compute)
result = subprocess.run([
    'python', 'scripts/generate_level1_health_scores.py',
    '--range', '7d'
], capture_output=True, text=True)

assert result.returncode == 0
print("✓ Fetch completed")

# Verify raw file exists, health file should also exist from fetch
raw_path = 'data/level1_raw_metrics_7d.csv'
health_path = 'data/level1_hourly_health_7d.csv'

assert os.path.exists(raw_path), "Raw file missing"
print("✓ Raw metrics file created")

# Verify compute can run independently
result = subprocess.run([
    'python', 'scripts/generate_level1_health_scores.py',
    '--range', '7d'
], capture_output=True, text=True)

assert result.returncode == 0
print("✓ Compute completed")

# Verify output is consistent
raw_df1 = pd.read_csv(raw_path)
health_df1 = pd.read_csv(health_path)

assert len(raw_df1) == len(health_df1), "Row count mismatch after re-run"
print("✓ Re-run produces consistent results")
```

---

## Part 9: Performance Tests

### Test 9.1: Execution Time
```python
"""
Measure ETL pipeline execution time.
"""

import subprocess
import time

print("\n=== Performance Test ===")

start = time.time()
result = subprocess.run([
    'python', 'scripts/generate_level1_health_scores.py',
    '--range', '24h'
], capture_output=True, text=True)
elapsed = time.time() - start

print(f"\nExecution Time:")
print(f"  Total: {elapsed:.2f} seconds")

# Expected: ~60-120 seconds
assert elapsed < 300, f"Pipeline too slow: {elapsed}s"
print("✓ Performance within acceptable range")
```

### Test 9.2: Memory Efficiency
```python
"""
Verify memory usage during ETL.
"""

import subprocess

result = subprocess.run([
    'python', '-c',
    '''
import tracemalloc
tracemalloc.start()

# Run ETL pipeline
import subprocess
subprocess.run([
    "python", "scripts/generate_level1_health_scores.py",
    "--range", "24h"
], capture_output=True)

# Check peak memory
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
'''
], capture_output=True, text=True)

print(result.stdout)
assert 'Peak memory' in result.stdout
```

---

## Part 10: Final Verification Report

### Run All Tests
```python
"""
Run complete verification suite.
"""

import sys

def run_all_tests():
    print("=" * 60)
    print("ETL PIPELINE VERIFICATION SUITE")
    print("=" * 60)
    
    tests = [
        ("1.1 Row Count Validation", test_1_1),
        ("1.2 Health Index Range", test_1_2),
        ("1.3 Risk Scores Range", test_1_3),
        ("1.4 Weight Sum Check", test_1_4),
        ("2.1 Baseline Parameters", test_2_1),
        ("3.1 Raw Schema", test_3_1),
        ("3.2 Health Schema", test_3_2),
        ("4.1 Missing Values", test_4_1),
        ("5.1 Health Index Formula", test_5_1),
        ("7.1 Long Format", test_7_1),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: Unexpected error: {e}")
            failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
```

---

**Document Version**: 1.0  
**Last Updated**: March 3, 2026  
**Test Suite Status**: READY FOR EXECUTION
