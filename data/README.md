# Health Scoring Data

This directory contains FAIR health scoring results for AHUs across all 11 building levels.

## Generated Files

### Health Score CSVs
| File | Size | Records | Description |
|------|------|---------|-------------|
| `all_levels_health_24h.csv` | ~1.6 MB | 9,537 | Last 24 hours of health data |
| `all_levels_health_7d.csv` | ~963 KB | 5,577 | Last 7 days of health data |
| `all_levels_health_30d.csv` | ~1.0 MB | 5,973 | Last 30 days of health data |

### Raw Metrics CSVs
| File | Size | Records | Description |
|------|------|---------|-------------|
| `all_levels_raw_24h.csv` | ~905 KB | 9,537 | Raw InfluxDB metrics (24h) |
| `all_levels_raw_7d.csv` | ~723 KB | 5,577 | Raw InfluxDB metrics (7d) |
| `all_levels_raw_30d.csv` | ~828 KB | 5,973 | Raw InfluxDB metrics (30d) |

### Anomaly Reports
| File | Size | Description |
|------|------|-------------|
| `anomaly_summary_*.json` | ~17 KB | Latest anomaly report (auto-generated) |
| `MULTI_LEVEL_HEALTH_ANALYSIS_SUMMARY.md` | ~6.5 KB | Comprehensive analysis summary |

---

## CSV Column Definitions

### Raw Metrics (all_levels_raw_*.csv)
| Column | Type | Description |
|--------|------|-------------|
| timestamp | string | ISO 8601 timestamp (e.g., "2026-03-01T06:45:00+00:00") |
| ahu_id | string | AHU identifier (e.g., "e0101") |
| level | string | Building level (e.g., "Level 1") |
| power_total | float | Total power consumption in kW |
| energy_import | float | Cumulative energy imported (kWh) |
| power_factor_avg | float | Average power factor (0-1) |
| current_unbalance | float | Current unbalance percentage |
| current_l1_thd | float | THD for Phase L1 (%) |
| current_l3_thd | float | THD for Phase L3 (%) |

### Health Scores (all_levels_health_*.csv)
| Column | Type | Description |
|--------|------|-------------|
| timestamp | string | ISO 8601 timestamp |
| ahu_id | string | AHU identifier |
| level | string | Building level |
| health_index | float | Overall health score (0-100) |
| tier | string | Health tier (Healthy/Monitor/Maintenance Soon/Critical) |
| energy_anomaly | float | Energy anomaly score (0-1) |
| pf_degradation | float | Power factor degradation score (0-1) |
| phase_imbalance | float | Phase imbalance score (0-1) |
| thd_drift | float | THD drift score (0-1) |
| overload | float | Overload risk score (0-1) |
| power_total | float | Current power in kW |
| power_factor | float | Current power factor |
| unbalance_pct | float | Current unbalance % |
| thd_24h | float | 24-hour THD average |
| delta_kwh | float | Energy difference from previous hour |
| data_quality_flag | int | 0=good, 1=missing THD |
| safety_flags | string | Comma-separated safety warnings |
| z_energy | float | Z-score for energy anomaly |
| z_pf | float | Z-score for PF degradation |
| z_imbalance | float | Z-score for phase imbalance |
| z_thd | float | Z-score for THD drift |
| z_overload | float | Z-score for overload risk |

---

## Tier Definitions

| Tier | Health Index Range | Color | Action |
|------|-------------------|-------|--------|
| Healthy | 80-100 | Green | Normal operation |
| Monitor | 60-79 | Yellow/Amber | Watch for degradation |
| Maintenance Soon | 40-59 | Orange | Schedule maintenance |
| Critical | 0-39 | Red | Immediate attention required |

---

## Safety Flags

| Flag | Condition | Action |
|------|-----------|--------|
| THD_CHRONIC_HIGH | Median THD > 15% | Investigate harmonics |
| IMBALANCE_SEVERE | Median unbalance > 30% | Check for load imbalance |
| PF_CHRONIC_LOW | Median power factor < 0.50 | Install power factor correction |
| OVERLOAD_CHRONIC | Median power > 90% of p95 | Redistribute load |

---

## How to Use

### View Health Data
```bash
# Show first 10 rows of health data
head -10 data/all_levels_health_24h.csv

# Count devices by tier (last 24h)
grep -v "timestamp" data/all_levels_health_24h.csv | cut -d',' -f5 | sort | uniq -c
```

### Find Anomalies
```bash
# Find devices with z-scores > 2.0 (high anomalies)
python3 -c "
import pandas as pd
df = pd.read_csv('data/all_levels_health_24h.csv')
high_z = df[df['z_energy'].abs() > 2.0]
print(high_z[['ahu_id', 'health_index', 'z_energy']].head(10))
"
```

### Generate New Health Scores
```bash
# Run for all ranges and levels
python3 scripts/generate_all_levels_health_scores.py --all-ranges

# Run for specific time range
python3 scripts/generate_all_levels_health_scores.py --range 7d

# Run for specific levels only
python3 scripts/generate_all_levels_health_scores.py --levels 1,2,3

# With longer delay between levels (to avoid timeouts)
python3 scripts/generate_all_levels_health_scores.py --all-ranges --delay 10
```

---

## FAIR Health Scoring Methodology

### Core Formula
```
health_index = 100 - penalty × 100

where penalty = 
    energy_anomaly × 0.15
  + pf_degradation × 0.25
  + phase_imbalance × 0.25
  + thd_drift × 0.15
  + overload × 0.20
```

### Scoring Components

Each component uses **70% level term + 30% trend term**:

1. **Energy Anomaly (weight: 15%)**
   - Compares current delta_kwh to historical baseline
   - Z-score based on robust statistics (median + MAD)

2. **PF Degradation (weight: 25%)**
   - Compares current power factor to baseline
   - Load discount applied if power < 60% of median

3. **Phase Imbalance (weight: 25%)**
   - Compares current unbalance to baseline
   - High values indicate load imbalance

4. **THD Drift (weight: 15%)**
   - Uses 24h rolling mean of THD
   - Identifies harmonic distortion trends

5. **Overload (weight: 20%)**
   - Compares current power to p95 ceiling
   - Includes trend analysis for overload risk

---

## Data Generation Parameters

| Parameter | Value |
|-----------|-------|
| Time Ranges | 24h, 7d, 30d |
| Sample per Level | 2-3 devices |
| Levels | 1-11 (all) |
| Total Devices | 33 |
| Delay Between Levels | 5 seconds |

---

## Notes

- Delta_kwh is computed as the difference between consecutive hourly energy readings
- Z-scores are normalized to range [-5, +5] for reasonable anomaly detection
- All baselines use robust statistics (median + 1.4826×MAD) instead of mean/std
- THD baseline uses 24h rolling mean to avoid permanent z-score inflation
