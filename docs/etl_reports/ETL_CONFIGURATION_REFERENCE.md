# ETL Pipeline Configuration Reference

## Complete Configuration Guide for WACH Insight ETL Pipeline

---

## 1. InfluxDB Configuration

### 1.1 Environment Variables
```bash
# backend/config.py
INFLUX_URL="http://localhost:8086"
INFLUX_TOKEN="<your_api_token>"
INFLUX_ORG="wach"
INFLUX_BUCKET="wach_bucket_3"
```

### 1.2 Configuration File
**File**: `backend/config.py`
```python
def get_influx_url() -> str:
    return os.getenv("INFLUX_URL", "http://localhost:8086")

def get_influx_token() -> str:
    return os.getenv("INFLUX_TOKEN", "")

def get_influx_org() -> str:
    return os.getenv("INFLUX_ORG", "wach")

def get_influx_bucket() -> str:
    return os.getenv("INFLUX_BUCKET", "wach_bucket_3")
```

### 1.3 Connection Configuration
```python
# backend/core/influx_client.py
_URL = get_influx_url()
_TOKEN = get_influx_token() or ""
_ORG = get_influx_org() or "wach"
_BUCKET = get_influx_bucket() or "wach_bucket_3"

client = InfluxDBClient(
    url=_URL,
    token=_TOKEN,
    org=_ORG,
    timeout=18_000_000  # 18 seconds
)
```

---

## 2. Time Range Configuration

### 2.1 Allowed Time Ranges
**File**: `backend/models/schemas.py`
```python
ALLOWED_TIME_RANGES = {
    "last_24h": "-24h",
    "last_7d":  "-7d",
    "last_30d": "-30d",
    "all_time": "-1y",   # InfluxDB needs concrete start; 1 year covers "all time"
}
```

### 2.2 Resampling Frequency
**File**: `backend/core/influx_client.py`
```python
_RESAMPLE_MAP = {
    "last_24h":  "5min",   # 12 readings per hour
    "last_7d":   "1h",     # 24 readings per day
    "last_30d":  "4h",     # 6 readings per day
    "all_time":  "1d",     # 1 reading per day
}
```

### 2.3 Time Range Mapping Table
| UI Parameter | Influx Query | Resample | Readings/Hour |
|--------------|--------------|----------|---------------|
| `last_24h` | `-24h` | 5min | 12 |
| `last_7d` | `-7d` | 1h | 1 |
| `last_30d` | `-30d` | 4h | 0.25 |
| `all_time` | `-1y` | 1d | 0.04 |

---

## 3. FAIR Algorithm Configuration

### 3.1 Weight Configuration
**File**: `scripts/generate_level1_health_scores.py`
```python
# FAIR Algorithm Weights (must sum to 1.0)
HEALTH_INDEX_WEIGHTS = {
    "energy_anomaly": 0.15,   # 15% weight
    "pf_degradation": 0.25,   # 25% weight
    "phase_imbalance": 0.25,  # 25% weight
    "thd_drift":      0.15,   # 15% weight
    "overload":       0.20,   # 20% weight
}

# Verify: 0.15 + 0.25 + 0.25 + 0.15 + 0.20 = 1.00 ✓
```

### 3.2 Level vs Trend Blend
```python
# FAIR Algorithm Constants
LEVEL_WEIGHT = 0.70   # "is it bad right now?"
TREND_WEIGHT = 0.30   # "is it getting worse?"

# Final score formula:
# score = LEVEL_WEIGHT × level_term + TREND_WEIGHT × trend_term
#       = 0.70 × level_term + 0.30 × trend_term
```

### 3.3 Sensitivity Factors
```python
SENSITIVITY = {
    "energy_anomaly":  2.0,   # Energy deviation sensitivity
    "pf_degradation":  2.5,   # PF signal amplification
    "phase_imbalance": 2.0,   # Unbalance sensitivity
    "thd_drift":       2.0,   # THD sensitivity
    "overload":        2.0,   # Load sensitivity
}
```

### 3.4 Minimum Robust Std Values
```python
MIN_RSTD = {
    "delta_kwh":          0.05,
    "power_factor_avg":   0.008,
    "current_unbalance":  0.15,
    "composite_thd_24h":  0.15,
    "power_total":        0.05,
}
```

---

## 4. Health Tier Configuration

### 4.1 Tier Thresholds
```python
HEALTH_TIERS = {
    "Critical":        (0, 39),
    "Maintenance Soon": (40, 59),
    "Monitor":         (60, 79),
    "Healthy":         (80, 100),
}
```

### 4.2 Health Index Formula
```python
def calculate_health_index(risk_scores):
    WEIGHTS = {
        "energy_anomaly": 0.15,
        "pf_degradation": 0.25,
        "phase_imbalance": 0.25,
        "thd_drift": 0.15,
        "overload": 0.20,
    }
    
    penalty = sum(WEIGHTS.get(k, 0) * score for k, score in risk_scores.items())
    health_index = 100 - (penalty * 100)
    
    return float(np.clip(health_index, 0.0, 100.0))
```

### 4.3 Tier Color Mapping
```javascript
// frontend/src/components/AhuHealthTrendDashboard.jsx
const TIER_COLORS = {
  Healthy: '#00c9b1',           // Teal
  Monitor: '#f5a623',           // Amber
  'Maintenance Soon': '#f5734e',// Orange
  Critical: '#ff4d6d',          // Red
};
```

### 4.4 Tier Threshold Lines
```javascript
const COMPONENT_CONFIG = {
  health_index: {
    label: 'Health Index',
    weight: null,
    min: 0, max: 100,
    unit: '',
    thresholdLines: [
      { value: 80, label: 'Healthy', color: '#00c9b145' },
      { value: 60, label: 'Monitor', color: '#f5a62345' },
      { value: 40, label: 'Maint.', color: '#f5734e45' },
    ]
  },
  // ... risk scores with 0.6 and 0.3 thresholds
};
```

---

## 5. Safety Flags Configuration

### 5.1 Flag Conditions
```python
# Thresholds for safety flag generation
THRESHOLDS = {
    "thd_chronic_high": 15.0,      # median THD > 15%
    "imbalance_severe": 30.0,      # median unbalance > 30%
    "pf_chronic_low": 0.50,        # median PF < 0.50
    "overload_chronic": 0.90,      # median power > 90% of p95
}
```

### 5.2 Safety Flag Generation Logic
```python
def compute_safety_flags(baseline, power_median, power_p95):
    """Compute safety flags based on baseline thresholds."""
    flags = []

    # THD_CHRONIC_HIGH: median 24h-THD > 15%
    thd_med = baseline.get("thd_median")
    if thd_med is not None and thd_med > 15.0:
        flags.append("THD_CHRONIC_HIGH")

    # IMBALANCE_SEVERE: median unbalance > 30%
    unbal_med = baseline.get("unbal_median")
    if unbal_med is not None and unbal_med > 30.0:
        flags.append("IMBALANCE_SEVERE")

    # PF_CHRONIC_LOW: median PF < 0.50
    pf_med = baseline.get("pf_median")
    if pf_med is not None and pf_med < 0.50:
        flags.append("PF_CHRONIC_LOW")

    # OVERLOAD_CHRONIC: median power > 90% of own p95
    if (power_median is not None and power_p95 is not None
            and power_p95 > 0 and power_median / power_p95 > 0.90):
        flags.append("OVERLOAD_CHRONIC")

    return ",".join(flags) if flags else ""
```

### 5.3 Valid Safety Flags
```python
VALID_FLAGS = {
    'THD_CHRONIC_HIGH',
    'IMBALANCE_SEVERE',
    'PF_CHRONIC_LOW',
    'OVERLOAD_CHRONIC'
}
```

---

## 6. FAIR Scoring Formulas

### 6.1 Energy Anomaly Score
```python
def score_energy_anomaly(delta_kwh, ahu_median_delta, ahu_rstd_delta, hist_delta_series):
    """
    Score: 1 · Energy Anomaly (weight 15%)
    
    Formula:
      z = (delta_kwh − median) / rstd
      raw = 0.6 × |z| + 0.4 × max(0, z)
      level = sigmoid(raw × sensitivity) [70%]
      trend = sigmoid(ols_slope / rstd × slope_sensitivity) [30%]
      
    Returns score ∈ [0, 1]
    """
    z = (delta_kwh - ahu_median_delta) / rstd
    raw = 0.6 * abs(z) + 0.4 * max(0.0, z)
    lv = sigmoid_score(raw * SENSITIVITY["energy_anomaly"])
    
    slope_n = ols_slope(hist_delta_series) / rstd
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    
    score = 0.70 * lv + 0.30 * tr
    return clamp01(score), round(z, 3)
```

### 6.2 PF Degradation Score
```python
def score_pf_degradation(pf, power, ahu_median_pf, ahu_rstd_pf, hist_pf_series):
    """
    Score: 2 · PF Degradation (weight 25%)
    
    Formula:
      z = (median_pf − current_pf) / rstd
      raw = z × sensitivity
      level = sigmoid(raw) [70%]
      trend = sigmoid(-slope / rstd × slope_sensitivity) [30%]
      
    Load Discount: if power < 60% × median_power, score × 0.35
    """
    z = (ahu_median_pf - pf) / rstd  # positive = below median = bad
    lv = sigmoid_score(z * SENSITIVITY["pf_degradation"])
    
    slope_n = ols_slope(hist_pf_series) / rstd
    tr = sigmoid_score(max(0.0, -slope_n) * SLOPE_SENS)
    
    score = 0.70 * lv + 0.30 * tr
    
    # Load discount
    if power < PF_DISCOUNT_THRESHOLD * ahu_median_pf:
        score *= PF_DISCOUNT_FACTOR
    
    return clamp01(score), round(z, 3)
```

### 6.3 Phase Imbalance Score
```python
def score_phase_imbalance(unbal, ahu_median_unbal, ahu_rstd_unbal, hist_unbal_series):
    """
    Score: 3 · Phase Imbalance (weight 25%)
    
    Formula:
      z = (current − median) / rstd
      level = sigmoid(z × sensitivity) [70%]
      trend = sigmoid(slope / rstd × slope_sensitivity) [30%]
    """
    z = (unbal - ahu_median_unbal) / rstd
    lv = sigmoid_score(z * SENSITIVITY["phase_imbalance"])
    
    slope_n = ols_slope(hist_unbal_series) / rstd
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    
    score = 0.70 * lv + 0.30 * tr
    return clamp01(score), round(z, 3)
```

### 6.4 THD Drift Score
```python
def score_thd_drift(thd_24h, ahu_median_thd, ahu_rstd_thd, hist_thd_24h_series):
    """
    Score: 4 · THD Drift (weight 15%)
    
    Formula:
      z = (current_thd − median_thd) / rstd
      level = sigmoid(z × sensitivity) [70%]
      trend = sigmoid(slope / rstd × slope_sensitivity) [30%]
    """
    z = (thd_24h - ahu_median_thd) / rstd
    lv = sigmoid_score(z * SENSITIVITY["thd_drift"])
    
    slope_n = ols_slope(hist_thd_24h_series) / rstd
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    
    score = 0.70 * lv + 0.30 * tr
    return clamp01(score), round(z, 3)
```

### 6.5 Overload Score
```python
def score_overload(power, ahu_median_power, ahu_rstd_power, ahu_p95_power, hist_power_series):
    """
    Score: 5 · Overload (weight 20%)
    
    Three sub-components:
      A. Ceiling term (50%): power_ratio = current / p95
         demand = max(0, power_ratio - 0.85)
         score_A = sigmoid(demand × 8)
         
      B. Z-score term (30%): z = (current - median) / rstd
         score_B = sigmoid(z × 1.5)
         
      C. Trend term (20%): slope_n = ols_slope / rstd
         score_C = sigmoid(max(0, slope_n) × slope_sensitivity)
         
      Final = 0.50 × score_A + 0.30 × score_B + 0.20 × score_C
    """
    power_ratio = power / ahu_p95_power
    demand = max(0.0, power_ratio - 0.85)
    score_A = sigmoid_score(demand * 8.0)
    
    z = (power - ahu_median_power) / rstd
    score_B = sigmoid_score(z * 1.5)
    
    slope_n = ols_slope(hist_power_series) / rstd
    score_C = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    
    score = 0.50 * score_A + 0.30 * score_B + 0.20 * score_C
    return clamp01(score), round(z, 3)
```

---

## 7. Helper Functions

### 7.1 Robust Parameters (Median + MAD)
```python
def robust_params(values):
    """
    Compute robust location (median) and scale (1.4826 × MAD).
    
    1.4826 × MAD equals std for a normal distribution.
    For heavy-tailed or bimodal distributions it is far more stable.
    
    Returns (median, rstd) where rstd >= MIN_RSTD
    """
    v = values[~np.isnan(values)]
    if len(v) < 3:
        median = float(np.nanmedian(values)) if len(values) > 0 else 0.0
        return median, MIN_RSTD.get('default', 0.01)
    
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    rstd = max(1.4826 * mad, MIN_RSTD.get('default', 0.01))
    
    return med, rstd
```

### 7.2 Sigmoid Scoring
```python
def sigmoid(x: float) -> float:
    """Standard sigmoid function mapping input to [0, 1]."""
    x = max(-500, min(500, x))
    return 1.0 / (1.0 + math.exp(-x))


def sigmoid_score(raw: float) -> float:
    """
    Convert raw penalty score to [0, 1] where raw=0 gives score=0.
    
    Standard sigmoid gives 0.5 at raw=0. We shift and rescale:
      score = clip(sigmoid(raw) * 2 - 1, 0, 1)
    
    Behaviour:
      raw = 0  → 0.00   (exactly at baseline, no concern)
      raw = 1  → 0.46   (1 std above/below)
      raw = 2  → 0.76   (2 std)
      raw = 3  → 0.91   (3 std)
    """
    raw = max(-500.0, min(500.0, float(raw)))
    s = sigmoid(raw) * 2.0 - 1.0
    return max(0.0, min(1.0, s))
```

### 7.3 OLS Slope Calculation
```python
def ols_slope(values):
    """
    Calculate OLS slope using linear regression.
    
    Closed-form (O(n), no matrix ops):
      β = [n·Σ(i·y) − Σ(i)·Σ(y)] / [n·Σ(i²) − (Σ(i))²]
    
    Returns slope in metric-units per hour.
    """
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    n = len(v)
    
    if n < 3:
        return 0.0
    
    i_arr = np.arange(n, dtype=float)
    num = n * np.dot(i_arr, v) - i_arr.sum() * v.sum()
    denom = n * np.dot(i_arr, i_arr) - i_arr.sum() ** 2
    
    return float(num / denom) if denom != 0 else 0.0
```

---

## 8. File Paths Configuration

### 8.1 Data Directory
```python
# backend/config.py
def get_data_dir() -> Path:
    """Get path to data directory."""
    return BASE_DIR / "data"
```

### 8.2 Output Paths
```python
# scripts/generate_level1_health_scores.py

def generate_all_time_ranges(output_dir=None):
    """Generate health scores for all time ranges: 24h, 7d, 30d"""
    if output_dir is None:
        output_dir = "/Users/rdmasia/wach-insight/data"

    os.makedirs(output_dir, exist_ok=True)

    time_ranges = [
        ("last_24h", "24h"),
        ("last_7d", "7d"),
        ("last_30d", "30d"),
    ]

    for range_key, range_name in time_ranges:
        raw_path = os.path.join(output_dir, f"level1_raw_metrics_{range_name}.csv")
        output_path = os.path.join(output_dir, f"level1_hourly_health_{range_name}.csv")
        # ... generate files
```

### 8.3 Output File Structure
```
data/
├── level1_raw_metrics_24h.csv      # Raw InfluxDB metrics
├── level1_raw_metrics_7d.csv
├── level1_raw_metrics_30d.csv
├── level1_hourly_health_24h.csv    # Final health scores
├── level1_hourly_health_7d.csv
└── level1_hourly_health_30d.csv
```

---

## 9. Script Execution Configuration

### 9.1 Command Line Arguments
```python
# scripts/generate_level1_health_scores.py

parser = argparse.ArgumentParser(description="Generate FAIR health scores for AHU fleet")
parser.add_argument("--fetch-only", action="store_true",
                   help="Only fetch raw data, don't compute scores")
parser.add_argument("--compute-only", action="store_true",
                   help="Only compute scores from existing raw data")
parser.add_argument("--range", type=str, default=None,
                   help="Time range: 24h, 7d, 30d (default: all ranges)")
parser.add_argument("--output", type=str, default=None,
                   help="Output CSV path for scores")
parser.add_argument("--raw-output", type=str, default=None,
                   help="Output CSV path for raw metrics")
parser.add_argument("--all-ranges", action="store_true",
                   help="Generate for all time ranges (24h, 7d, 30d)")
```

### 9.2 Usage Examples

**Generate all time ranges:**
```bash
python scripts/generate_level1_health_scores.py --all-ranges
```

**Generate specific time range:**
```bash
python scripts/generate_level1_health_scores.py --range 7d
```

**Fetch only (no compute):**
```bash
python scripts/generate_level1_health_scores.py --fetch-only
```

**Compute only (from existing raw data):**
```bash
python scripts/generate_level1_health_scores.py --compute-only
```

---

## 10. Frontend Configuration

### 10.1 CSV File Mapping
```javascript
// frontend/src/components/AhuHealthTrendDashboard.jsx

const csvFileMap = {
  '24h': '/level1_hourly_health_24h.csv',
  '7d': '/level1_hourly_health_7d.csv',
  '30d': '/level1_hourly_health_30d.csv'
};

const timeRangeMap = {
  '24h': 'last_24h',
  '7d': 'last_7d',
  '30d': 'last_30d'
};
```

### 10.2 Cache Busting
```javascript
// Fetch with cache busting to ensure fresh data on range switch
const cacheBuster = Date.now()
const csvFileBase = csvFileMap[timeRange] || '/level1_hourly_health.csv'
const csvFile = `${csvFileBase}?t=${cacheBuster}`

// Or use no-store directive
const response = await fetch(csvFile, { cache: 'no-store' })
```

### 10.3 Chart Configuration
```javascript
const COMPONENT_CONFIG = {
  health_index: {
    label: 'Health Index',
    weight: null,
    min: 0, max: 100,
    unit: '',
    thresholdLines: [
      { value: 80, label: 'Healthy', color: '#00c9b145' },
      { value: 60, label: 'Monitor', color: '#f5a62345' },
      { value: 40, label: 'Maint.', color: '#f5734e45' },
    ]
  },
  energy_anomaly: {
    label: 'Energy Anomaly',
    weight: 0.15,
    min: 0, max: 1,
    unit: '',
    thresholdLines: [
      { value: 0.6, label: 'High', color: '#ff4d6d45' },
      { value: 0.3, label: 'Elev.', color: '#f5a62345' },
    ]
  },
  pf_degradation: { /* ... */ },
  phase_imbalance: { /* ... */ },
  thd_drift: { /* ... */ },
  overload: { /* ... */ },
};
```

---

## 11. Complete Configuration Summary

| Category | Parameter | Value | Location |
|----------|-----------|-------|----------|
| InfluxDB URL | INFLUX_URL | `http://localhost:8086` | config.py |
| Influx Token | INFLUX_TOKEN | `<api_token>` | config.py |
| Organization | INFLUX_ORG | `wach` | config.py |
| Bucket | INFLUX_BUCKET | `wach_bucket_3` | config.py |
| Time Range 24h | last_24h | `-24h` | schemas.py |
| Time Range 7d | last_7d | `-7d` | schemas.py |
| Time Range 30d | last_30d | `-30d` | schemas.py |
| Resample 24h | 5min | 12/hour | influx_client.py |
| Resample 7d | 1h | 24/day | influx_client.py |
| Resample 30d | 4h | 6/day | influx_client.py |
| Level Weight | LEVEL_WEIGHT | 0.70 | generate_level1_health_scores.py |
| Trend Weight | TREND_WEIGHT | 0.30 | generate_level1_health_scores.py |
| SLOPE_SENS | SLOPE_SENS | 3.0 | generate_level1_health_scores.py |
| PF Discount | PF_DISCOUNT_THRESHOLD | 0.60 | generate_level1_health_scores.py |
| PF Discount Factor | PF_DISCOUNT_FACTOR | 0.35 | generate_level1_health_scores.py |
| THD Rolling Window | THD_ROLLING_H | 24h | generate_level1_health_scores.py |
| Trend Window | TREND_WINDOW_H | 168h (7d) | generate_level1_health_scores.py |

---

**Document Version**: 1.0  
**Last Updated**: March 3, 2026  
**Configuration Status**: COMPLETE
