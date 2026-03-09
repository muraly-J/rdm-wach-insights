# Prediction Formula Implementation Report

**Date**: 2026-03-05  
**Status**: ✅ COMPLETE - All scoring functions updated and tested

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Background](#background)
3. [Implementation Details](#implementation-details)
   - [Exact Slot Fetching Function](#exact-slot-fetching-function)
   - [Minimum History Requirements](#minimum-history-requirements)
   - [Scoring Function Updates](#scoring-function-updates)
4. [Edge Case Handling](#edge-case-handling)
   - [AHUs with < 24 Hours History](#ahu-with--24-hours-history)
   - [AHUs with 24h-168h History](#ahu-with-24h-168h-history)
   - [AHUs with ≥ 168 Hours History](#ahu-with--168-hours-history)
5. [Test Results](#test-results)
6. [Code Examples](#code-examples)
7. [Usage Guide](#usage-guide)

---

## Executive Summary

This report documents the implementation of prediction formula handling for AHUs with insufficient history. The system now:

1. **Fetches exact hourly slots** (`t-24h`, `t-168h`, `t-336h`) for comparison
2. **Handles AHUs with < 14 days history** by returning level-only scores
3. **Enables trend calculation only when ≥ 168h (7 days) of data is available**

### Key Changes

| Component | Change | Impact |
|-----------|--------|--------|
| `influx_client.py` | Added `fetch_exact_slots()` function | Enables precise historical slot fetching |
| `fair_health_scoring.py` | Updated all 5 scoring functions | Level-only scores for < 168h history |
| `risk_engine.py` | Updated `calculate_7d_slope()` docstring | Clarifies minimum history requirement |

---

## Background

### The Problem

The WACH Insight health scoring system needed to handle AHUs with varying history lengths:

| Scenario | Issue |
|----------|-------|
| New AHU (installed < 24h ago) | No baseline data available |
| AHU with recent maintenance (24-168h) | Baseline exists but trend unreliable |
| AHU with full history (≥ 168h) | Full scoring possible |

### Requirements

1. **Exact slot fetching**: Fetch specific timestamps (t-24h, t-168h, t-336h) for comparison
2. **Graceful degradation**: When history is insufficient, return meaningful but limited scores
3. **No crashes**: NaN values and empty series should not cause exceptions

---

## Implementation Details

### Exact Slot Fetching Function

**File**: `backend/core/influx_client.py` (lines 274-365)

```python
def fetch_exact_slots(
    device_ids: list[str],
    metric: str,
    reference_time: datetime,
    slots_hours_ago: list[int]
) -> Dict[str, Dict[int, Optional[float]]]:
    """
    Fetch exact historical values at specific time slots (t-24h, t-168h, etc).

    This enables comparison of current value against specific historical points:
    - t:     Current hour
    - t-24h: Same hour yesterday
    - t-168h: Same hour last week (7 days ago)
    - t-336h: Two weeks ago (14 days ago)

    Args:
        device_ids: List of AHU IDs to fetch
        metric: Metric name (e.g., "power_total", "energy_import")
        reference_time: Current timestamp t
        slots_hours_ago: List of hours ago to fetch (e.g., [0, 24, 168, 336])

    Returns:
        Nested dict: {ahu_id: {hours_ago: value, ...}}
        Example: {"e0101": {0: 35.2, 24: 33.1, 168: 34.8, 336: 32.5}}
    """
```

**Example Usage**:
```python
from datetime import datetime, timezone

# Fetch current and historical values for comparison
now = datetime.now(timezone.utc)
slots = fetch_exact_slots(
    device_ids=["e0101", "e0102"],
    metric="power_total",
    reference_time=now,
    slots_hours_ago=[0, 24, 168, 336]
)

# Result:
# {
#   "e0101": {0: 35.2, 24: 33.1, 168: 34.8, 336: 32.5},
#   "e0102": {0: 42.1, 24: 41.5, 168: 43.0}
# }
```

### Minimum History Requirements

The scoring system now enforces two thresholds:

| Threshold | Action | Rationale |
|-----------|--------|-----------|
| **< 24h** | Return neutral score (0.5) | Insufficient data for baseline |
| **24h - 167h** | Level term only (trend = 0) | Baseline exists but trend unreliable |
| **≥ 168h** | Full scoring (level + trend) | Complete data available |

#### Code Pattern

```python
# In each scoring function:

if hist_series is None or len(hist_series) < 24:
    return 0.5, np.nan  # Neutral score when insufficient history

# ... validate inputs ...

if len(hist_clean) >= 168:
    # Full data available: compute trend
    slope_n = float(np.clip(ols_slope(hist_clean) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
else:
    # Insufficient data for trend: return level-only score (trend=0)
    tr = 0.0

score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
```

### Scoring Function Updates

#### 1. `score_energy_anomaly()`
- **Parameter**: Added `min_history_hours: int = 24`
- **Behavior**:
  - < 24h history → returns neutral score (0.5)
  - ≥ 168h history → full scoring with trend

#### 2. `score_power_factor()`
- **Parameter**: Added `min_history_hours: int = 24`
- **Behavior**:
  - NaN baseline → returns worst case (0.0)
  - < 168h history → level-only scoring

#### 3. `score_phase_imbalance()`
- **Parameter**: Added `min_history_hours: int = 24`
- **Behavior**:
  - NaN baseline → returns worst case (0.0)
  - < 168h history → level-only scoring

#### 4. `score_thd_drift()`
- **Parameter**: Added `min_history_hours: int = 24`
- **Behavior**:
  - NaN baseline → returns worst case (0.0)
  - < 168h history → level-only scoring

#### 5. `score_overload()`
- **Behavior**:
  - < 24h history → returns neutral score (0.5)
  - ≥ 168h history → full scoring with trend

---

## Edge Case Handling

### AHUs with < 24 Hours History

**Scenario**: New AHU installed or recently configured, less than one day of data.

```python
# Example: Energy Anomaly with only 3 hours of history
score, z = score_energy_anomaly(
    delta_kwh=1.5,
    ahu_median_delta=2.0,
    ahu_rstd_delta=0.5,
    hist_delta_series=np.array([1.0, 2.0, 3.0])  # Only 3 points
)
# Result: score=0.5, z=nan
```

**Behavior**: Returns neutral score (0.5) with NaN diagnostic z-value.

### AHUs with 24h - 168h History

**Scenario**: AHU has baseline data but insufficient for reliable trend calculation.

```python
# Example: Energy Anomaly with 48 hours of history
score, z = score_energy_anomaly(
    delta_kwh=2.5,
    ahu_median_delta=2.0,
    ahu_rstd_delta=0.5,
    hist_delta_series=np.random.randn(48) * 0.5 + 2.0  # 48 hourly points
)
# Result: score computed, trend=0 (level-only scoring)
```

**Behavior**: Score is computed using level term only. Trend component = 0.

### AHUs with ≥ 168 Hours History

**Scenario**: Full historical data available for complete scoring.

```python
# Example: Energy Anomaly with 168 hours of history
score, z = score_energy_anomaly(
    delta_kwh=2.5,
    ahu_median_delta=2.0,
    ahu_rstd_delta=0.5,
    hist_delta_series=np.random.randn(168) * 0.5 + 2.0
)
# Result: score=0.53, trend=computed
```

**Behavior**: Full scoring with both level and trend terms.

---

## Test Results

### Edge Case Tests (100% Passing)

```
=== Testing Scoring Functions with Edge Cases ===

Test 1: Energy Anomaly with < 24h history
  Short history (3 pts): score=0.50, z=nan
  ✓ PASS

Test 2: Energy Anomaly with exactly 168h history
  Full history (168 pts): score=0.53, z=1.000
  ✓ PASS

Test 3: Energy Anomaly with 48h history (level-only)
  Medium history (48 pts): score=0.53, z=1.0
  ✓ PASS

Test 4: Power Factor with NaN baseline
  NaN baseline: score=0.00 (0.0 = worst case)
  ✓ PASS

Test 5: Phase Imbalance with hist available but < 168h
  Hist (50 pts): score=0.70
  ✓ PASS

Test 6: THD Drift with hist available but < 168h
  Hist (50 pts): score=0.70
  ✓ PASS

Test 7: Overload with < 24h history
  Short history (10 pts): score=0.50
  ✓ PASS

=== All Edge Case Tests Passed ===
```

---

## Code Examples

### Example 1: Fetching Exact Slots for Comparison

```python
from datetime import datetime, timezone
from core.influx_client import fetch_exact_slots

# Fetch current and historical values for a single AHU
now = datetime.now(timezone.utc)
slots = fetch_exact_slots(
    device_ids=["e0101"],
    metric="power_total",
    reference_time=now,
    slots_hours_ago=[0, 24, 168, 336]
)

# Compare current vs historical values
current = slots["e0101"].get(0)
yesterday = slots["e0101"].get(24)
last_week = slots["e0101"].get(168)
two_weeks_ago = slots["e0101"].get(336)

if current and last_week:
    deviation_pct = (current - last_week) / last_week * 100
    print(f"Current power: {current:.1f} kW (deviation: {deviation_pct:.1f}% vs last week)")
```

### Example 2: Scoring with Limited History

```python
import numpy as np
from core.fair_health_scoring import score_energy_anomaly

# Scenario: AHU with only 12 hours of history
short_history = np.array([1.0, 1.5, 2.0, 1.8, 2.2] * 2 + [1.9, 2.1])  # 12 points
current_delta = 2.5

# Score will be neutral because history < 24h
score, z = score_energy_anomaly(
    delta_kwh=current_delta,
    ahu_median_delta=2.0,
    ahu_rstd_delta=0.5,
    hist_delta_series=short_history
)
print(f"Score: {score:.2f} (neutral for insufficient history)")
# Output: Score: 0.50
```

### Example 3: Full Scoring with Complete History

```python
import numpy as np
from core.fair_health_scoring import score_energy_anomaly

# Scenario: AHU with 7 days of hourly data
full_history = np.random.randn(168) * 0.5 + 2.0  # 168 hourly points
current_delta = 2.5

# Score will include trend component
score, z = score_energy_anomaly(
    delta_kwh=current_delta,
    ahu_median_delta=2.0,
    ahu_rstd_delta=0.5,
    hist_delta_series=full_history
)
print(f"Score: {score:.2f}, Z-score: {z:.3f}")
# Output: Score: 0.53, Z-score: 1.000
```

---

## Usage Guide

### Fetching Data for a Specific Time Range

```python
from core.influx_client import fetch_time_series

# Fetch power data for last 30 days
df = fetch_time_series(
    device_ids=["e0101", "e0102"],
    metric="power_total",
    time_range="last_30d"
)

# The DataFrame is resampled based on time range:
# - last_24h: 5-minute intervals
# - last_7d: 1-hour intervals
# - last_30d: 4-hour intervals
```

### Computing Health Score for AHU

```python
from datetime import datetime, timezone
import numpy as np
from core.influx_client import fetch_exact_slots
from core.fair_health_scoring import score_energy_anomaly

# Fetch current and historical values
now = datetime.now(timezone.utc)
slots = fetch_exact_slots(
    device_ids=["e0101"],
    metric="energy_import",
    reference_time=now,
    slots_hours_ago=[0, 24, 168]
)

# Get values
current_energy = slots["e0101"].get(0)
yesterday_energy = slots["e0101"].get(24)
last_week_energy = slots["e0101"].get(168)

# Compute delta_kwh (hourly energy consumption)
if current_energy and yesterday_energy:
    delta_kwh = current_energy - yesterday_energy
    
    # Score with available history
    score, z = score_energy_anomaly(
        delta_kwh=delta_kwh,
        ahu_median_delta=2.0,
        ahu_rstd_delta=0.5,
        hist_delta_series=np.array([2.0]*168)  # Example history
    )
```

---

## Files Modified

| File | Lines Changed | Description |
|------|---------------|-------------|
| `backend/core/influx_client.py` | 274-365 (new) | Added `fetch_exact_slots()` function |
| `backend/core/fair_health_scoring.py` | ~240-510 | Updated 5 scoring functions |
| `backend/core/risk_engine.py` | ~253-270 | Updated docstring for `calculate_7d_slope()` |

---

## Summary

### Key Achievements

| Goal | Status |
|------|--------|
| Fetch exact hourly slots (t-24h, t-168h, t-336h) | ✅ Implemented |
| Handle AHUs with < 24h history | ✅ Returns neutral score (0.5) |
| Handle AHUs with 24h-168h history | ✅ Level-only scoring |
| Handle AHUs with ≥ 168h history | ✅ Full scoring (level + trend) |
| All tests passing | ✅ 100% pass rate |

### Future Enhancements

1. **Slot-based anomaly detection**: Compare current value against same hour yesterday/last week
2. **Confidence scoring**: Weight scores based on history length
3. **Missing slot handling**: Provide fallback when historical slots are unavailable
