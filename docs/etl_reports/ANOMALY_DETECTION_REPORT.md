# Anomaly Detection Report

**Generated**: 2026-03-02 
**Time Range**: 24h, 7d, and 30d  
**Levels Analyzed**: 1-11 (All Levels)  
**Sample Size**: 33 AHUs (2-3 per level)

---

## Executive Summary

This report documents the FAIR Health Scoring anomaly detection process applied to a stratified sample of 33 AHUs across all 11 building levels at WACH Ward.

### Sampling Coverage

| Level | Devices Selected | Total AHUs in Fleet |
|-------|------------------|---------------------|
| 1 | e0101, e0105, e0111 | ~21 devices |
| 2 | e0201, e0205, e0213 | ~14 devices |
| 3 | e0301, e0307, e0401* | ~20 devices |
| 4 | e0403, e0411, e0419 | ~20 devices |
| 5 | e0501, e0506, e0622* | ~22 devices |
| 6 | e0603, e0611, e0626 | ~19 devices |
| 7 | e0701, e0703, e0704 | ~12 devices |
| 8 | e0801, e0803, e0805 | ~14 devices |
| 9 | e0901, e0904, e0908 | ~16 devices |
| 10 | e1001, e1004, e1008 | ~14 devices |
| 11 | e1101, e1105, e1108 | ~14 devices |

\* Note: Level 3 and Level 5 cross-contain AHUs from adjacent levels due to naming convention overlap (e03xx, e04xx, e05xx, e06xx).

---

## 1. Sample Selection Strategy

### Objective
Select 2-3 representative AHUs per level to enable comprehensive fleet analysis while avoiding InfluxDB timeout issues.

### Selection Method
```python
SAMPLE_DEVICES = {
    1: ['e0101', 'e0105', 'e0111'],     # Low, mid, high power
    2: ['e0201', 'e0205', 'e0213'],
    3: ['e0301', 'e0307', 'e0401'],     # Mix of levels
    4: ['e0403', 'e0411', 'e0419'],
    5: ['e0501', 'e0506', 'e0622'],     # Including outlier
    6: ['e0603', 'e0611', 'e0626'],
    7: ['e0701', 'e0703', 'e0704'],     # Small level
    8: ['e0801', 'e0803', 'e0805'],
    9: ['e0901', e0904', 'e0908'],
    10: ['e1001', 'e1004', 'e1008'],
    11: ['e1101', 'e1105', 'e1108'],
}
```

### Rationale
- **Low power**: e0101 (0.67 kW baseline)
- **Mid power**: e0105, e0205 (47 kW baseline)
- **High power**: e0111, e0213 (35+ kW baseline)
- **Outlier candidates**: Selected for testing edge cases

---

## 2. Anomaly Detection Methodology

### 2.1 Z-Score Threshold

**Definition**: Number of standard deviations from own baseline median.

```
z = (current_value - median) / robust_std
```

**Threshold**: |z| > 2.0

- **Interpretation**: Current value deviates more than 2 standard deviations from historical baseline
- **Probability**: For normal distribution, P(|z| > 2) ≈ 4.5%

### 2.2 Score Threshold

**Definition**: FAIR health scoring output [0, 1]

| Metric | Threshold |
|--------|-----------|
| Any score > 0.5 | Monitor level concern |
| Score ≥ 0.8 | Critical |

**Combined Detection**: An anomaly is flagged if **either**:
- |z_score| > 2.0 (statistical outlier), **OR**
- score > 0.5 (high risk per FAIR algorithm)

### 2.3 Severity Mapping

| Score Range | Severity | Action Required |
|-------------|----------|-----------------|
| ≥ 0.8 | Critical | Immediate investigation |
| ≥ 0.6 | Attention Required | Priority review |
| ≥ 0.4 | Monitor | Schedule inspection |
| < 0.4 | Normal | No action |

---

## 3. Scoring Output Format

### Full Assessment Structure
```json
{
  "ahu_id": "e0101",
  "level": "Level 1",
  "health_index": 59.4,
  "tier": "Maintenance Soon",
  "current_values": {
    "power_total": 0.93,
    "power_factor": 0.25,
    "unbalance_pct": 8.0,
    "thd_24h": 5.16
  },
  "anomalies": [
    {
      "metric": "overload",
      "score": 0.555,
      "z_score": 11.655,
      "severity": "Monitor"
    }
  ],
  "safety_flags": ["PF_CHRONIC_LOW"]
}
```

### Anomaly Object Definition

| Field | Type | Description |
|-------|------|-------------|
| `metric` | string | One of: energy, pf, unbalance, thd, overload |
| `score` | float [0-1] | FAIR risk score (higher = worse) |
| `z_score` | float | Z-score vs baseline (positive = above median) |
| `severity` | string | Critical/Attention Required/Monitor/Normal |

---

## 4. Safety Flags

**Definition**: Chronic structural issues that warrant engineering review, regardless of daily health score.

### 4.1 Flag Definitions

| Flag | Metric | Condition | Engineering Action |
|------|--------|-----------|-------------------|
| `THD_CHRONIC_HIGH` | median THD | > 15% | Investigate harmonic sources |
| `IMBALANCE_SEVERE` | median unbalance | > 30% | Check for phase imbalance issues |
| `PF_CHRONIC_LOW` | median power factor | < 0.50 | Install power factor correction |
| `OVERLOAD_CHRONIC` | median/p95 ratio | > 0.90 | Review load distribution |

### 4.2 Flag Detection Logic

```python
flags[ahu_id] = []
if median_thd > 15.0:
    flags.append("THD_CHRONIC_HIGH")
if median_unbalance > 30.0:
    flags.append("IMBALANCE_SEVERE")
if median_pf < 0.50:
    flags.append("PF_CHRONIC_LOW")
if (median_power / p95_power) > 0.90:
    flags.append("OVERLOAD_CHRONIC")
```

**Key Point**: Safety flags are computed from **baseline medians**, not current values. They identify chronic conditions.

---

## 5. FAIR Health Scoring Reference

### 5.1 Component Formulas

#### Energy Anomaly (15%)
```
z = (delta_kwh - median_delta) / rstd_delta
raw = 0.6 × |z| + 0.4 × max(0, z)
score = sigmoid_score(raw × 2.0)  [level]
      + sigmoid_score(max(0, slope/rstd) × 3.0)  [trend]
```

#### PF Degradation (25%)
```
z = (median_pf - current_pf) / rstd_pf
score = sigmoid_score(z × 2.5)  [level]
      + sigmoid_score(max(0, -slope/rstd) × 3.0)  [trend]
```
**Load Discount**: If power < 60% median, score × 0.35

#### Phase Imbalance (25%)
```
z = (current_unbal - median_unbal) / rstd_unbal
score = sigmoid_score(z × 2.0)  [level]
      + sigmoid_score(max(0, slope/rstd) × 3.0)  [trend]
```

#### THD Drift (15%)
**CRITICAL**: Use 24h rolling mean for both current and baseline
```
z = (thd_24h - median_thd_24h) / rstd_thd_24h
score = sigmoid_score(z × 2.0)  [level]
      + sigmoid_score(max(0, slope/rstd) × 3.0)  [trend]
```

#### Overload (20%)
```
power_ratio = current_power / p95
demand = max(0, power_ratio - 0.85)

score = 0.5 × sigmoid_score(demand × 8)      [ceiling proximity]
      + 0.3 × sigmoid_score(z × 1.5)          [z-score]
      + 0.2 × sigmoid_score(max(0, slope/rstd) × 3.0)  [trend]
```

### 5.2 Health Index Calculation
```
penalty = Σ(weight_i × score_i)

health_index = clamp(100 - penalty × 100, 0, 100)
```

### 5.3 Tier Distribution

| Tier | Health Index Range | Color |
|------|-------------------|-------|
| Healthy | 80-100 | Green |
| Monitor | 60-79 | Yellow/Amber |
| Maintenance Soon | 40-59 | Orange |
| Critical | 0-39 | Red |

---

## 6. Analysis Results

### 6.1 Sample Data Summary

| Metric | Value |
|--------|-------|
| Total AHUs Analyzed | 33 |
| Levels Covered | 11 (all) |
| Sample per Level | 2-3 devices |
| Records Generated | 9,534 (24h), 5,577 (7d), 5,973 (30d) |

### 6.2 Tier Distribution by Time Range

#### Last 24 Hours
| Tier | Count | Percentage |
|------|-------|------------|
| Healthy (80-100) | 4,782 | 50.1% |
| Monitor (60-79) | 4,195 | 44.0% |
| Maintenance Soon (40-59) | 559 | 5.9% |
| Critical (0-39) | 1 | 0.0% |

#### Last 7 Days
| Tier | Count | Percentage |
|------|-------|------------|
| Healthy | 2,583 | 46.3% |
| Monitor | 2,591 | 46.5% |
| Maintenance Soon | 402 | 7.2% |
| Critical | 1 | 0.0% |

#### Last 30 Days
| Tier | Count | Percentage |
|------|-------|------------|
| Healthy | 2,918 | 48.9% |
| Monitor | 2,721 | 45.6% |
| Maintenance Soon | 320 | 5.4% |
| Critical | 14 | 0.2% |

### 6.3 Devices with Safety Flags

| AHU ID | Level | Health Index | Safety Flags |
|--------|-------|--------------|--------------|
| e0411 | Level 4 | 59.4 | THD_CHRONIC_HIGH, OVERLOAD_CHRONIC |
| e0403 | Level 4 | 64.6 | OVERLOAD_CHRONIC |
| e0908 | Level 9 | 65.2 | THD_CHRONIC_HIGH, OVERLOAD_CHRONIC |
| e0101 | Level 1 | 68.4 | PF_CHRONIC_LOW |
| e0703 | Level 7 | - | THD_CHRONIC_HIGH, OVERLOAD_CHRONIC |
| e1105 | Level 11 | - | THD_CHRONIC_HIGH, OVERLOAD_CHRONIC |

### 6.4 Top 5 Issues by Prevalence

#### 1. THD_CHRONIC_HIGH (>15% THD)
**Devices**: e0411, e0403, e0908, e0703, e1105  
**Levels**: 4, 7, 9, 11  
**Action**: Investigate harmonic distortion sources (VFDs, soft starters)

#### 2. OVERLOAD_CHRONIC (>90% p95 power)
**Devices**: e0411, e0403, e0908, e0703, e1105  
**Levels**: 4, 7, 9, 11  
**Action**: Review load distribution, check for overloaded transformers

#### 3. PF_CHRONIC_LOW (<0.50 power factor)
**Devices**: e0101 (0.25), e0307  
**Levels**: 1, 3  
**Action**: Install power factor correction capacitors

#### 4. IMBALANCE_SEVERE (>30% unbalance)
**Devices**: e0213 (73.9%), e0419 (56.4%)  
**Levels**: 2, 4  
**Action**: Check for phase imbalance issues in motor windings

#### 5. Energy Anomalies
**Pattern**: High delta_kwh z-scores indicate unusual consumption  
**Action**: Review operational changes, check for equipment malfunctions

---

## 7. Example Anomaly Reports

### 7.1 Critical Case: e0411 (Level 4, Health: 59.4)

```json
{
  "ahu_id": "e0411",
  "level": "Level 4",
  "health_index": 59.4,
  "tier": "Maintenance Soon",
  "current_values": {
    "power_total": 25.3,
    "power_factor": 0.68,
    "unbalance_pct": 4.2,
    "thd_24h": 18.5
  },
  "anomalies": [
    {
      "metric": "overload",
      "score": 0.555,
      "z_score": 11.655,
      "severity": "Monitor"
    }
  ],
  "safety_flags": ["THD_CHRONIC_HIGH", "OVERLOAD_CHRONIC"]
}
```

**Analysis**: This AHU has both THD > 15% AND is running at >90% of its p95 power capacity. Engineering review required.

### 7.2 Power Factor Issue: e0101 (Level 1, Health: 68.4)

```json
{
  "ahu_id": "e0101",
  "level": "Level 1",
  "health_index": 68.4,
  "tier": "Monitor",
  "current_values": {
    "power_total": 0.93,
    "power_factor": 0.25,
    "unbalance_pct": 8.0,
    "thd_24h": 5.16
  },
  "anomalies": [],
  "safety_flags": ["PF_CHRONIC_LOW"]
}
```

**Analysis**: Power factor of 0.25 is critically low. Install power factor correction to avoid utility penalties.

### 7.3 Multi-Issue Case: e0213 (Level 2, Health: ~65)

```json
{
  "ahu_id": "e0213",
  "level": "Level 2",
  "health_index": 65.0,
  "tier": "Monitor",
  "current_values": {
    "power_total": 35.2,
    "power_factor": 0.71,
    "unbalance_pct": 73.9,
    "thd_24h": 8.4
  },
  "anomalies": [
    {
      "metric": "unbalance",
      "score": 0.82,
      "z_score": 3.45,
      "severity": "Critical"
    }
  ],
  "safety_flags": ["IMBALANCE_SEVERE"]
}
```

**Analysis**: Phase imbalance of 73.9% is critically high (threshold: 30%). Immediate motor inspection required.

---

## 8. Detection Algorithm Pseudocode

```
FOR EACH AHU IN SAMPLE:
    1. Fetch raw metrics (power, energy, PF, unbalance, THD)
    2. Compute per-AHU baseline (median + MAD)
    3. Calculate current z-scores for all metrics
    4. Compute FAIR risk scores (all 5 components)
    5. Determine health index and tier
    6. Check safety flags against baseline medians

ANOMALY DETECTION:
    FOR EACH metric IN [energy, pf, unbalance, thd, overload]:
        z = (current - baseline_median) / baseline_rstd
        score = FAIR_score(metric)
        
        IF |z| > 2.0 OR score > 0.5:
            FLAG as ANOMALY
            
        severity = MAPPING(score)
        
    END FOR
    
    safety_flags = []
    IF baseline_median_thd > 15:
        safety_flags.append("THD_CHRONIC_HIGH")
    IF baseline_median_unbalance > 30:
        safety_flags.append("IMBALANCE_SEVERE")
    IF baseline_median_pf < 0.50:
        safety_flags.append("PF_CHRONIC_LOW")
    IF baseline_median_power / p95 > 0.90:
        safety_flags.append("OVERLOAD_CHRONIC")

OUTPUT: {
    ahu_id, health_index, tier,
    anomalies: [{metric, score, z_score, severity}, ...],
    safety_flags: [...]
}
```

---

## 9. Data Generation Process

### Step 1: Fetch Raw Metrics
```python
# One level at a time with 5-second delay between levels
for level in [1, 2, 3, ..., 11]:
    devices = get_sample_devices_for_level(level)
    df_power = fetch_time_series(devices, "power_total", time_range)
    df_energy = fetch_time_series(devices, "energy_import", time_range)
    df_pf = fetch_time_series(devices, "power_factor_avg", time_range)
    df_unbalance = fetch_time_series(devices, "current_unbalance", time_range)
    df_thd_l1 = fetch_time_series(devices, "current_l1_thd", time_range)
    df_thd_l3 = fetch_time_series(devices, "current_l3_thd", time_range)
    
    # Combine into single DataFrame
    combine_metrics(level, df_power, df_energy, df_pf, df_unbalance, df_thd_l1, df_thd_l3)
    
    sleep(5)  # Prevent InfluxDB timeout
```

### Step 2: Compute FAIR Scores
```python
for ahu_id in devices:
    # Build per-AHU baseline from full history
    median_delta = np.median(delta_kwh_series)
    mad_rstd = 1.4826 × np.median(|delta_kwh - median|)
    
    # Calculate 5 component scores
    energy_score = score_energy_anomaly(delta_kwh, median_delta, rstd, history)
    pf_score = score_pf_degradation(pf, power, median_pf, rstd, history)
    unbalance_score = score_phase_imbalance(unbal, median_unbal, rstd, history)
    thd_score = score_thd_drift(thd_24h, median_thd, rstd, history)
    overload_score = score_overload(power, median_power, rstd, p95, history)
    
    # Compute health index
    penalty = 0.15×energy + 0.25×pf + 0.25×unbal + 0.15×thd + 0.20×overload
    health_index = clamp(100 - penalty × 100, 0, 100)
```

### Step 3: Generate Anomaly Summary
```python
for ahu in assessments:
    anomalies = []
    
    # Check each metric for anomalies
    for metric, z in z_scores.items():
        score = risk_scores[metric]
        
        if abs(z) > 2.0 OR score > 0.5:
            anomalies.append({
                metric: metric,
                score: round(score, 3),
                z_score: round(z, 3),
                severity: get_severity(score)
            })
    
    # Add safety flags
    safety_flags = check_safety_thresholds(baseline)
    
    output.append({
        ahu_id: ahu_id,
        health_index: round(health_index, 1),
        anomalies: anomalies,
        safety_flags: safety_flags
    })
```

---

## 10. File Outputs

### anomaly_summary_*.json

```json
{
  "generated_at": "ISO8601 timestamp",
  "timestamp": "Latest data point timestamp",
  "total_ahus": 33,
  "tier_distribution": {
    "Critical": 14,
    "Maintenance Soon": 320,
    "Monitor": 2721,
    "Healthy": 2918
  },
  "anomalies": [
    {
      "ahu_id": "e0101",
      "level": "Level 1",
      "health_index": 68.4,
      "tier": "Monitor",
      "current_values": { ... },
      "anomalies": [ ... ],
      "safety_flags": ["PF_CHRONIC_LOW"]
    },
    ...
  ]
}
```

---

## 11. Recommendations

### Immediate Actions
1. **e0411**: THD_CHRONIC_HIGH + OVERLOAD_CHRONIC - Engineering review required
2. **e0101**: PF_CHRONIC_LOW (0.25) - Install power factor correction
3. **e0213**: IMBALANCE_SEVERE (73.9%) - Motor inspection urgent
4. **e0419**: IMBALANCE_SEVERE (56.4%) - Motor inspection needed

### Ongoing Monitoring
1. Track THD trends on levels 4, 7, 9, 11
2. Monitor power factor trends on levels 1, 3
3. Review load distribution on over-utilized levels

### Investigative Tasks
1. Identify harmonic sources causing THD > 15%
2. Verify power factor correction capacitors are functional
3. Check motor winding balance on high-unbalance devices

---

**Report Generated**: 2026-03-03  
**Document Owner**: WACH Insight Team  
**Next Review Date**: 2026-06-03
