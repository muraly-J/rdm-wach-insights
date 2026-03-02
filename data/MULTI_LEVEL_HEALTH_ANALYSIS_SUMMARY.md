# Multi-Level Health Analysis Summary

**Generated**: 2026-03-02  
**Time Range**: 24h, 7d, and 30d  
**Levels Analyzed**: 1-11 (All Levels)  

---

## Overview

This report summarizes the FAIR Health Scoring analysis for 33 sample AHUs across all 11 building levels at WACH Ward.

### Key Statistics

| Metric | Value |
|--------|-------|
| Total AHUs Analyzed | 33 |
| Levels Covered | 11 (all) |
| Sample per Level | 2-3 devices |

### Sampling Strategy

For each level, we selected 2-3 representative AHUs:

| Level | Devices Selected | Total Records |
|-------|------------------|---------------|
| 1 | e0101, e0105, e0111 | 867 |
| 2 | e0201, e0205, e0213 | 867 |
| 3 | e0301, e0307, e0401 | 867 |
| 4 | e0403, e0411, e0419 | 867 |
| 5 | e0501, e0506, e0622 | 867 |
| 6 | e0603, e0611, e0626 | 867 |
| 7 | e0701, e0703, e0704 | 864 |
| 8 | e0801, e0803, e0805 | 867 |
| 9 | e0901, e0904, e0908 | 867 |
| 10 | e1001, e1004, e1008 | 867 |
| 11 | e1101, e1105, e1108 | 867 |

**Total Records**: 9,534 (24h), 5,577 (7d), 5,973 (30d)

---

## Health Distribution by Time Range

### Last 24 Hours
- **Healthy (80-100)**: 4,782 (50.1%)
- **Monitor (60-79)**: 4,195 (44.0%)
- **Maintenance Soon (40-59)**: 559 (5.9%)
- **Critical (0-39)**: 1 (0.0%)

### Last 7 Days
- **Healthy**: 2,583 (46.3%)
- **Monitor**: 2,591 (46.5%)
- **Maintenance Soon**: 402 (7.2%)
- **Critical**: 1 (0.0%)

### Last 30 Days
- **Healthy**: 2,918 (48.9%)
- **Monitor**: 2,721 (45.6%)
- **Maintenance Soon**: 320 (5.4%)
- **Critical**: 14 (0.2%)

---

## Critical Findings

### Devices with Safety Flags

| AHU ID | Level | Health Index | Safety Flags |
|--------|-------|--------------|--------------|
| e0411 | Level 4 | 59.4 | THD_CHRONIC_HIGH, OVERLOAD_CHRONIC |
| e0403 | Level 4 | 64.6 | OVERLOAD_CHRONIC |
| e0908 | Level 9 | 65.2 | THD_CHRONIC_HIGH, OVERLOAD_CHRONIC |
| e0101 | Level 1 | 68.4 | PF_CHRONIC_LOW |
| e0703 | Level 7 | - | THD_CHRONIC_HIGH, OVERLOAD_CHRONIC |
| e1105 | Level 11 | - | THD_CHRONIC_HIGH, OVERLOAD_CHRONIC |

### Top 5 Issues by Prevalence

1. **THD_CHRONIC_HIGH** (>15% THD)
   - Multiple devices across levels 4, 7, 9, 11
   - Indicates potential harmonic distortion issues

2. **OVERLOAD_CHRONIC** (>90% p95 power)
   - Found in multiple levels
   - Devices running near max capacity

3. **PF_CHRONIC_LOW** (<0.50 power factor)
   - e0101 (Level 1): 0.25
   - Indicates need for power factor correction

4. **IMBALANCE_SEVERE** (>30% unbalance)
   - e0419 (Level 4): 56.4%
   - e0213 (Level 2): 73.9%

---

## FAIR Health Scoring Methodology

### Core Principles

1. **Per-AHU Baseline**: Each AHU is judged against its own historical baseline (median + MAD)
2. **No Fleet Comparison**: Inherently fair across differently-sized AHUs
3. **Robust Statistics**: Uses median and 1.4826×MAD for scale estimation
4. **70% Level + 30% Trend**: Health = 70% current state + 30% trend direction

### Scoring Components (5 Metrics)

| Metric | Weight | Formula | Notes |
|--------|--------|---------|-------|
| Energy Anomaly | 15% | Level + Trend on delta_kwh | Compares energy consumption to baseline |
| PF Degradation | 25% | Level + Trend on PF deviation | Load-dependent (discount <60% load) |
| Phase Imbalance | 25% | Level + Trend on unbalance | Current measurement vs baseline |
| THD Drift | 15% | Level + Trend on THD | Uses 24h rolling mean for baseline |
| Overload | 20% | Power ratio + z-score + trend | Based on p95 ceiling |

### Health Index Calculation

```
penalty = Σ(weight_i × score_i)
health_index = clamp(100 - penalty × 100, 0, 100)
```

### Tier Distribution

| Tier | Range | Color |
|------|-------|-------|
| Healthy | 80-100 | Green |
| Monitor | 60-79 | Yellow/Amber |
| Maintenance Soon | 40-59 | Orange |
| Critical | 0-39 | Red |

---

## Data Generation Process

### Step 1: Fetch Raw Metrics
- Processes one level at a time with 5-second delay between levels
- Prevents InfluxDB timeouts
- Collects power, energy, PF, unbalance, THD metrics

### Step 2: Compute FAIR Scores
- Per-AHU baseline computation (median + MAD)
- delta_kwh calculation from cumulative energy differences
- Trend analysis using 168-hour window

### Step 3: Generate Anomaly Summary
- Identifies devices with abnormal z-scores (|z| > 2.0)
- Flags chronic issues as safety_flags
- Ranks by health index (lowest first)

---

## Files Generated

### Raw Metrics (Intermediate)
- `data/all_levels_raw_24h.csv` - 9,537 rows
- `data/all_levels_raw_7d.csv` - 5,577 rows  
- `data/all_levels_raw_30d.csv` - 5,973 rows

### Health Scores (Final Output)
- `data/all_levels_health_24h.csv` - 9,537 rows
- `data/all_levels_health_7d.csv` - 5,577 rows
- `data/all_levels_health_30d.csv` - 5,973 rows

### Anomaly Reports
- `data/anomaly_summary_YYYY-MM-DD_HH-MM-SS.json`
- Contains tier distribution and anomaly details

---

## Anomaly Detection Results (30d Analysis)

| AHU ID | Health Index | Anomalies | Severity |
|--------|--------------|-----------|----------|
| e0101 | 68.4 | Energy (z=2.9), Overload (z=3.7) | Attention Required |
| e0411 | 59.4 | Energy (z=-3.7) | Maintenance Soon |
| e0403 | 64.6 | Energy (z=-4.3) | Monitor |
| e0908 | 65.2 | Energy (z=-5.6) | Monitor |
| e1101 | 37.1 | Multiple metrics | Critical |

---

## Recommendations

### Immediate Actions
1. **Power Factor Correction**: e0101 has PF of 0.25 - requires immediate attention
2. **THD Mitigation**: Multiple devices show THD > 15% - investigate harmonics
3. **Load Management**: Devices with OVERLOAD_CHRONIC flag need load redistribution

### Long-term Improvements
1. **Regular Maintenance**: Schedule maintenance for devices withMaintenance Soon tier
2. **Harmonic Studies**: Investigate THD issues on affected levels
3. **Load Balancing**: Redistribute loads to reduce overload risk

---

## Usage

### Regenerate Health Scores
```bash
# For all ranges and all levels
python scripts/generate_all_levels_health_scores.py --all-ranges

# For specific time range
python scripts/generate_all_levels_health_scores.py --range 7d

# For specific levels only
python scripts/generate_all_levels_health_scores.py --levels 1,3,5

# With custom delay between levels
python scripts/generate_all_levels_health_scores.py --all-ranges --delay 10
```

### View Anomaly Summary
```bash
# Latest anomaly report
cat data/anomaly_summary_*.json | jq '.anomalies[:5]'

# Tiers distribution
cat data/anomaly_summary_*.json | jq '.tier_distribution'
```

---

## Notes

- Delta_kwh calculation fixed: Now correctly computes difference from previous row
- Z-scores normalized: Range -5 to +5 (reasonable for anomaly detection)
- All scores use FAIR methodology (per-AHU baseline, robust statistics)
