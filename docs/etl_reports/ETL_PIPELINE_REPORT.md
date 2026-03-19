# ETL Pipeline Architecture Report

## Executive Summary

The WACH Insight AHU health scoring system uses a **two-phase ETL pipeline** that fetches raw metrics from InfluxDB and computes health scores using the FAIR (Fast, Accurate, Intuitive, Robust) algorithm.

---

## One Pipeline Run - End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ETL PIPELINE RUN                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PHASE 1: FETCH_RAW_METRICS                                                 │
│  ───────────────────────────                                                │
│                                                                              │
│  Step 1: Get available devices for Level 1                                  │
│    → InfluxDB Query: DISTINCT measurements matching wach_e\\d{4}_power_total│
│    → Returns: List of device IDs (e0101, e0102, ..., e0121)                │
│                                                                              │
│  Step 2: Fetch 6 metrics for all devices                                    │
│    → power_total      (kW)                                                  │
│    → energy_import    (kWh)                                                 │
│    → power_factor_avg (unitless 0-1)                                        │
│    → current_unbalance (% phase imbalance)                                  │
│    → current_l1_thd   (THD Phase 1, %)                                      │
│    → current_l3_thd   (THD Phase 3, %)                                      │
│                                                                              │
│  Step 3: Resample and combine                                               │
│    → Resampling: last_24h=5min, last_7d=1h, last_30d=4h                    │
│    → Output: 5760 rows (20 AHUs × 288 hours)                                │
│    → Save to: data/level1_raw_metrics_24h.csv                              │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PHASE 2: COMPUTE_FAIR_SCORES                                               │
│  ───────────────────────────                                                │
│                                                                              │
│  Step 1: Build per-AHU baselines (median + MAD)                            │
│    → Robust parameters: median, 1.4826×MAD                                  │
│    → Each AHU has independent baseline                                      │
│                                                                              │
│  Step 2: Compute risk scores for each AHU, per hour                        │
│    → energy_anomaly     (weight: 0.15)                                      │
│    → pf_degradation     (weight: 0.25)                                      │
│    → phase_imbalance    (weight: 0.25)                                      │
│    → thd_drift         (weight: 0.15)                                      │
│    → overload          (weight: 0.20)                                      │
│                                                                              │
│  Step 3: Calculate health index                                            │
│    → health_index = 100 - (weighted_penalty × 100)                         │
│    → penalty = Σ(risk_score × weight)                                       │
│                                                                              │
│  Step 4: Assign tier and safety flags                                      │
│    → Tier: Healthy (≥80), Monitor (60-79), Maintenance Soon (40-59), Critical (<40)│
│    → Safety Flags: THD_CHRONIC_HIGH, IMBALANCE_SEVERE, PF_CHRONIC_LOW, OVERLOAD_CHRONIC│
│                                                                              │
│  Output: data/level1_hourly_health_24h.csv (5760 rows, 22 columns)         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## InfluxDB Queries Used

### Query 1: Get Available Devices
```flux
from(bucket: "wach_bucket_3")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement =~ /^wach_e\d{4}_power_total$/)
  |> distinct(column: "_measurement")
  |> keep(columns: ["_value"])
```

**Purpose:** Discover which AHU devices have data in the specified time range.

---

### Query 2: Fetch Time Series for Single Metric
```flux
from(bucket: "wach_bucket_3")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement =~ /^wach_(e0101|e0102|...)_power_total$/)
  |> pivot(rowKey:["_time"], columnKey: ["_measurement"], valueColumn: "_value")
  |> sort(columns: ["_time"])
```

**Purpose:** Pivot measurements so each device becomes a column, enabling time-series analysis across all devices.

---

### Query 3: Resample with Forward Fill
```python
df = df.resample("5min").mean().ffill().fillna(0)
```

**Purpose:** Convert high-frequency data to uniform intervals with gap-filling.

---

## Output CSV Schema

### Raw Metrics (data/level1_raw_metrics_24h.csv)
| Column | Type | Unit | Description |
|--------|------|------|-------------|
| timestamp | string (ISO8601) | - | UTC timestamp |
| ahu_id | string | - | Device ID (e0101-e0121) |
| power_total | float | kW | Active power |
| energy_import | float | kWh | Cumulative energy consumed |
| power_factor_avg | float | 0-1 | Power factor ratio |
| current_unbalance | float | % | Phase unpercentageage |
| current_l1_thd | float | % | THD Phase 1 |
| current_l3_thd | float | % | THD Phase 3 |

**Rows:** 5,760 (20 AHUs × 288 hours)  
**Columns:** 8 columns

---

### Health Scores (data/level1_hourly_health_24h.csv)
| Column | Type | Unit | Description |
|--------|------|------|-------------|
| timestamp | string (ISO8601) | - | UTC timestamp |
| ahu_id | string | - | Device ID |
| level | string | - | Level identifier (e.g., "Level 1") |
| health_index | float | 0-100 | Overall health score |
| tier | string | - | Health tier classification |
| energy_anomaly | float | 0-1 | Energy risk score |
| pf_degradation | float | 0-1 | Power factor degradation |
| phase_imbalance | float | 0-1 | Phase imbalance risk |
| thd_drift | float | 0-1 | THD drift risk |
| overload | float | 0-1 | Overload risk score |
| power_total | float | kW | Current power reading |
| power_factor | float | 0-1 | Current PF |
| unbalance_pct | float | % | Current unpercentageage |
| thd_24h | float | % | 24h rolling mean THD |
| delta_kwh | float | kWh | Hourly energy consumption |
| data_quality_flag | int | 0/1 | Data quality indicator |
| safety_flags | string | - | Comma-separated flags |
| z_energy | float | - | Z-score for energy |
| z_pf | float | - | Z-score for PF |
| z_imbalance | float | - | Z-score for imbalance |
| z_thd | float | - | Z-score for THD |
| z_overload | float | - | Z-score for overload |

**Rows:** 5,760 (20 AHUs × 288 hours)  
**Columns:** 22 columns total

---

## FAIR Algorithm Implementation

### Scoring Formula
```python
health_index = 100 - (weighted_penalty × 100)

where: weighted_penalty = 
    energy_anomaly     × 0.15
    + pf_degradation   × 0.25
    + phase_imbalance  × 0.25
    + thd_drift        × 0.15
    + overload         × 0.20
```

### Risk Score Components (per AHU)
Each risk score uses **70% level + 30% trend** blending:

```python
risk_score = LEVEL_WEIGHT × level_component + TREND_WEIGHT × trend_component

where:
  - LEVEL_WEIGHT = 0.70 ("is it bad right now?")
  - TREND_WEIGHT = 0.30 ("is it getting worse?")
```

### Baseline Calculation
```python
def robust_params(values):
    """Compute median and MAD (median absolute deviation)."""
    v = values[~np.isnan(values)]
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    rstd = max(1.4826 * mad, MIN_RSTD.get('default', 0.01))
    return med, rstd
```

**Key Points:**
- Uses **median** and **MAD** (Median Absolute Deviation) for robust statistics
- Each AHU has independent baseline - no fleet comparison needed
- Handles outliers gracefully with robust estimators

---

## Time Range Configuration

| UI Parameter | Influx Range | Resample Frequency | Readings/Hour |
|--------------|--------------|-------------------|---------------|
| last_24h | `-24h` | 5 minutes | 12 |
| last_7d | `-7d` | 1 hour | 1 |
| last_30d | `-30d` | 4 hours | 0.25 |

**Example Row Counts:**
- last_24h: 20 AHUs × 288 hours = 5,760 rows
- last_7d: 20 AHUs × 168 hours = 3,360 rows
- last_30d: 20 AHUs × 180 hours = 3,600 rows

---

## Tier Classification

| Tier | Health Index Range | Color |
|------|-------------------|-------|
| Healthy | 80-100 | Green (#00c9b1) |
| Monitor | 60-79 | Amber (#f5a623) |
| Maintenance Soon | 40-59 | Orange (#f5734e) |
| Critical | 0-39 | Red (#ff4d6d) |

---

## Safety Flags

| Flag | Threshold | Description |
|------|-----------|-------------|
| THD_CHRONIC_HIGH | median > 15% | THD levels consistently above threshold |
| IMBALANCE_SEVERE | median > 30% | Phase unbalance severity |
| PF_CHRONIC_LOW | median < 0.50 | Power factor consistently low |
| OVERLOAD_CHRONIC | median > 90% of p95 | Device operating near max capacity |

---

## Complete Script Usage

### Generate for All Time Ranges
```bash
python scripts/generate_level1_health_scores.py --all-ranges
```

**Output:**
- `data/level1_raw_metrics_24h.csv`
- `data/level1_hourly_health_24h.csv`
- `data/level1_raw_metrics_7d.csv`
- `data/level1_hourly_health_7d.csv`
- `data/level1_raw_metrics_30d.csv`
- `data/level1_hourly_health_30d.csv`

### Generate for Specific Time Range
```bash
python scripts/generate_level1_health_scores.py --range 24h
```

### Run Only Raw Data Fetch
```bash
python scripts/generate_level1_health_scores.py --fetch-only
```

### Compute Scores from Existing Raw Data
```bash
python scripts/generate_level1_health_scores.py --compute-only
```

---

## Verification Results

**All 14 tests passed:**

| Test | Result |
|------|--------|
| Raw Metrics Schema (8 columns) | ✓ PASS |
| Health Scores Schema (22 columns) | ✓ PASS |
| Health Index Range [43.0, 100.0] | ✓ PASS |
| Risk Score Bounds [0, 1] | ✓ PASS |
| Tier Classification | ✓ PASS |
| Tier Distribution | ✓ PASS (Healthy:45%, Monitor:47%, Maintenance Soon:8%) |
| Weighted Penalty Calculation | ✓ PASS |
| Weights Sum = 1.0 | ✓ PASS (1.00) |
| Z-Score Distribution | ✓ PASS |
| Safety Flags | ✓ PASS (THD_CHRONIC_HIGH, OVERLOAD_CHRONIC, etc.) |
| Raw/Health Row Count Match | ✓ PASS (5760 records) |
| AHU Coverage | ✓ PASS (20 devices, e0101-e0121) |
| Time Range | ✓ PASS (23.9 hours ~24h) |
| Data Quality | ✓ PASS (100% good) |

---

## Documentation Location

All documentation has been created in the `docs/` directory:

| File | Size | Purpose |
|------|------|---------|
| `docs/ETL_PIPELINE_ARCHITECTURE.md` | 14.5 KB | Complete ETL architecture documentation |
| `docs/ETL_VERIFICATION_SUITE.md` | 19.8 KB | Test suite with 14 verification checks |
| `docs/ETL_CONFIGURATION_REFERENCE.md` | 17.7 KB | Configuration reference guide |
| `docs/ETL_PIPELINE_REPORT.md` | This file | Comprehensive ETL pipeline report |

**Verification Script:** `scripts/verify_etl_pipeline.py`

---

## Running Verification

```bash
# Run all verification tests
cd /Users/rdmasia/wach-insight
python3 scripts/verify_etl_pipeline.py

# Expected output: 14 passed, 0 failed
```

---

## Data Quality Metrics

| Metric | Value |
|--------|-------|
| Total AHUs | 20 (e0101-e0121, excluding e0112) |
| Total Records | 5,760 (per time range) |
| Data Quality Flag = 0 (good) | 100% |
| Data Quality Flag = 1 (missing THD) | 0% |
| Health Index Range | [43.0, 100.0] |
| Missing Values | None |

---

## Summary

The ETL pipeline successfully:

1. **Fetches** raw metrics from InfluxDB using Flux queries
2. **Transforms** data through per-AHU baseline computation
3. **Computes** health scores using FAIR algorithm with 70/30 level/trend blending
4. **Outputs** structured CSV files for dashboard consumption

The pipeline is:
- **Robust**: Uses median + MAD for outlier-resistant baselines
- **Scalable**: Each AHU processed independently
- **Transparent**: 22-column output with full traceability
- **Verifiable**: 14 automated tests ensure correctness
