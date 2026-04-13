from __future__ import annotations
"""
risk_engine.py
──────────────
Rule-based electrical risk scoring system for AHU fleet.

This module implements the "Electrical Risk Check" - a deterministic,
interpretable risk assessment system that requires no training data.

Output Schema (per AHU):
{
  "device_id": "wach_e0101",
  "timestamp": "2026-02-23T14:00:00+08:00",
  "health_index": 84,
  "health_tier": "Healthy",
  "energy": {...},
  "risk_scores": {
    "power_factor": {...},
    "phase_imbalance": {...},
    "thd_drift": {...},
    "overload": {...}
  },
  "data_quality": {...}
}

Cluster Grouping Strategy:
- AHUs are grouped by LEVEL (e.g., e01xx = Level 1, e11xx = Level 11)
- Peer percentile ranking compares AHUs within the same level
- Rationale: Electrical loads and conditions are similar within a building level

Author: Rule-Based Baseline System (Stage 2B MVP)
"""

import asyncio
import math
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

# Import prediction delta loader for energy anomaly scoring
from core.fair_health_scoring import load_prediction_deltas
from core.influx_client import fetch_time_series, get_available_devices

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION: Risk Scoring Weights and Thresholds
# ──────────────────────────────────────────────────────────────

# Health Index weights (must sum to 1.0)
HEALTH_INDEX_WEIGHTS = {
    "energy_anomaly": 0.15,
    "power_factor":   0.25,
    "phase_imbalance": 0.25,
    "thd_drift":      0.15,
    "overload":       0.20,
}

# Risk tier thresholds
HEALTH_TIERS = {
    "Critical":        (0, 39),
    "Maintenance Soon": (40, 59),
    "Monitor":         (60, 79),
    "Healthy":         (80, 100),
}

# Sigmoid scaling factors (from requirements)
SIGMOID_K = {
    "power_factor":     5.0,   # steepness for PF
    "phase_imbalance":  4.0,   # steepness for unbalance
    "thd_drift":        3.0,   # steepness for THD
    "overload":         5.0,   # steepness for overload
}

# Thresholds (from requirements)
THRESHOLDS = {
    # Power Factor: baseline 0.87 (typical good PF)
    "pf_baseline":       0.87,

    # Phase Imbalance: NEMA MG1 thresholds
    "imbalance_warn":    2.0,   # 2% = warning threshold
    "imbalance_critical": 5.0,  # 5% = critical

    # THD: IEEE 519 thresholds
    "thd_baseline":      3.5,   # typical baseline
    "thd_critical":      5.0,   # IEEE 519 limit

    # Overload: compared against historical max
    "overload_baseline": 0.85,  # 85% of historical max is concerning
}

# ──────────────────────────────────────────────────────────────────────────────
# ROBUST STATISTICS CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

# Minimum robust-std values (prevents division by near-zero)
MIN_RSTD = {
    "delta_kwh":          0.05,
    "power_factor_avg":   0.008,
    "current_unbalance":  0.15,
    "composite_thd_24h":  0.15,
    "power_total":        0.05,
}

# Sensitivity factors for each score
SENSITIVITY = {
    "energy_anomaly":  2.0,
    "pf_degradation":  2.5,
    "phase_imbalance": 2.0,
    "thd_drift":       2.0,
    "overload":        2.0,
}

# Level vs trend blend
LEVEL_WEIGHT = 0.70   # "is it bad right now?"
TREND_WEIGHT = 0.30   # "is it getting worse?"

# Slope sensitivity (after normalising slope by own robust-std)
SLOPE_SENS = 3.0

# PF load discount
PF_DISCOUNT_THRESHOLD = 0.60   # below 60% of own median power
PF_DISCOUNT_FACTOR    = 0.35   # reduce score to 35% of computed value

# THD uses 24h rolling mean to filter transient spikes
THD_ROLLING_H = 24

# Slope computed over this many hours of history
TREND_WINDOW_H = 168   # 7 days


# ──────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────

def robust_params(values):
    """
    Compute robust location (median) and scale (1.4826 × MAD).

    1.4826 × MAD equals std for a normal distribution.
    For heavy-tailed or bimodal distributions it is far more stable.

    Returns (median, rstd) where rstd >= MIN_RSTD.
    """
    import numpy as np

    v = values[~np.isnan(values)]
    if len(v) < 3:
        median = float(np.nanmedian(values)) if len(values) > 0 else 0.0
        return median, MIN_RSTD.get('default', 0.01)

    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    rstd = max(1.4826 * mad, MIN_RSTD.get('default', 0.01))
    return med, rstd

def sigmoid(x: float) -> float:
    """
    Standard sigmoid function mapping input to [0, 1].
    Used for normalizing risk scores.
    """
    # Clamp to avoid overflow
    x = max(-500, min(500, x))
    return 1.0 / (1.0 + math.exp(-x))


def normalize_to_01(value: float, min_val: float, max_val: float) -> float:
    """Normalize a value to [0, 1] range."""
    if max_val - min_val == 0:
        return 0.5  # Neutral score if no range
    normalized = (value - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, normalized))


def detect_bimodality(values: np.ndarray, threshold: float = 2.0) -> tuple[bool, float]:
    """
    Detect bimodal distribution using the Dip Test approximation.

    For a bimodal distribution, the distance between modes is large compared
    to the spread within each mode. This creates a "dip" in the CDF.

    Simplified bimodality indicator:
        - Compute gaps between consecutive points after sorting
        - Large gaps suggest mode separation
        - Ratio of largest gap to median gap indicates bimodality

    Args:
        values: Input array of numeric values
        threshold: Bimodality score above which distribution is considered bimodal

    Returns:
        (is_bimodal: bool, bimodality_score: float)
        - is_bimodal: True if distribution appears bimodal
        - bimodality_score: 0-1 scale (higher = more bimodal)
    """
    import numpy as np

    v = values[~np.isnan(values)]
    if len(v) < 10:  # Need enough data for meaningful analysis
        return False, 0.0

    # Sort values
    sorted_vals = np.sort(v)

    # Compute gaps between consecutive points
    gaps = np.diff(sorted_vals)

    if len(gaps) < 2:
        return False, 0.0

    # Median gap (typical spacing)
    median_gap = float(np.median(gaps))

    if median_gap == 0:
        return False, 0.0

    # Largest gap (potential mode separation)
    max_gap = float(np.max(gaps))

    # Bimodality score: ratio of largest to median gap
    bimodality_score = min(1.0, (max_gap / median_gap - 1) / 5.0)

    is_bimodal = bimodality_score >= threshold

    return is_bimodal, min(1.0, bimodality_score)


def percentile_rank(value: float, series: pd.Series) -> int:
    """Calculate percentile rank (0-100) of value against series."""
    if len(series) == 0:
        return 50
    return int((series < value).mean() * 100)


def get_health_tier(health_index: float) -> str:
    """Map health index to tier string."""
    for tier, (low, high) in HEALTH_TIERS.items():
        if low <= health_index <= high:
            return tier
    return "Critical"  # fallback for out-of-range values


def calculate_7d_slope(df: pd.DataFrame, column: str) -> float:
    """
    Calculate 7-day slope using linear regression.
    Returns normalized slope (change per day).

    Minimum History Requirement:
        - At least 7 daily data points required for slope calculation
        - If history < 168h (7 days), return 0.0 (no trend)
    """
    if column not in df.columns:
        return 0.0

    # Resample to daily for slope calculation
    daily = df[column].resample('1d').mean()

    if len(daily) < 7:
        return 0.0

    # Linear regression: slope = cov(x,y) / var(x)
    x = list(range(len(daily)))
    y = daily.values
    y = pd.Series(y).interpolate().fillna(method='bfill').fillna(method='ffill')

    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)

    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y, strict=False))
    denominator = sum((xi - x_mean) ** 2 for xi in x)

    if denominator == 0:
        return 0.0

    slope = numerator / denominator

    # Normalize: convert to per-day change relative to range
    value_range = max(y) - min(y) if max(y) != min(y) else 1.0
    return slope / value_range if value_range > 0 else 0.0


def get_level_from_ahu_id(ahu_id: str) -> str:
    """
    Extract building level from AHU ID.
    e0101 → Level 1, e0505 → Level 5, e1108 → Level 11
    """
    # Extract level prefix (e.g., "e01" from "e0101")
    parts = ahu_id.split('_')
    if len(parts) >= 2:
        device_id = parts[-1]  # e.g., "e0101"
    else:
        device_id = ahu_id

    if device_id.startswith('e') and len(device_id) >= 3:
        level_code = device_id[1:3]  # "01", "02", etc.
        try:
            level = int(level_code)
            return f"Level {level}"
        except ValueError:
            pass
    return "Unknown"


# ──────────────────────────────────────────────────────────────────────────────
# RISK SCORING FUNCTIONS (THE CORE RULE ENGINE)
# ──────────────────────────────────────

def sigmoid_score(raw: float) -> float:
    """
    Map raw penalty to [0, 1] where raw=0 gives score=0.

    Standard sigmoid gives 0.5 at raw=0. We shift and rescale:
        score = clip(sigmoid(raw) * 2 - 1, 0, 1)

    Behaviour:
        raw = 0  → 0.00   (exactly at own baseline, no concern)
        raw = 1  → 0.46   (1 std above/below)
        raw = 2  → 0.76   (2 std)
        raw = 3  → 0.91   (3 std)
    """
    raw = max(-500.0, min(500.0, float(raw)))
    s = 1.0 / (1.0 + math.exp(-raw))
    return float(np.clip(s * 2.0 - 1.0, 0.0, 1.0))


def ols_slope(values):
    """
    OLS slope β through equally-spaced points (0, y_0), (1, y_1), …, (n-1, y_{n-1}).
    Returns slope in metric-units per hour.

    Closed-form (O(n), no matrix ops):
        β = [n·Σ(i·y) − Σ(i)·Σ(y)] / [n·Σ(i²) − (Σ(i))²]
    """
    import numpy as np
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    n = len(v)
    if n < 3:
        return 0.0
    i     = np.arange(n, dtype=float)
    num   = n * np.dot(i, v) - i.sum() * v.sum()
    denom = n * np.dot(i, i) - i.sum() ** 2
    return float(num / denom) if denom != 0 else 0.0


def clamp01(x: float) -> float:
    """Clamp value to [0, 1]."""
    return float(np.clip(x, 0.0, 1.0))


def new_energy_anomaly_score(
    delta_kwh: float,
    ahu_median_delta: float,
    ahu_rstd_delta: float,
    hist_delta_series,
) -> float:
    """
    Score 1 · Energy Anomaly  (weight 15%)

    Is this AHU consuming an unusual amount of energy this hour compared
    to what IT normally consumes.

    Level term (70%):
        z = (delta_kwh − own_median) / own_rstd
        raw = 0.6 × |z| + 0.4 × max(0, z)

    Trend term (30%):
        Rising energy over 7 days = worsening.

    Returns score ∈ [0,1]
    """
    import numpy as np

    if delta_kwh is None or np.isnan(delta_kwh) or delta_kwh < 0:
        return 0.0

    if ahu_median_delta is None or np.isnan(ahu_median_delta):
        return 0.0

    # Use robust std
    rstd = max(ahu_rstd_delta, MIN_RSTD.get("delta_kwh", 0.05))
    if rstd <= 0:
        return 0.0

    z = (delta_kwh - ahu_median_delta) / rstd
    raw = 0.6 * abs(z) + 0.4 * max(0.0, z)
    lv = sigmoid_score(raw * SENSITIVITY["energy_anomaly"])

    # Trend term
    slope_n = float(np.clip(ols_slope(hist_delta_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)

    return clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)


def new_power_factor_risk_score(
    pf: float,
    power: float,
    ahu_median_pf: float,
    ahu_rstd_pf: float,
    hist_pf_series,
) -> float:
    """
    Score 2 · PF Degradation  (weight 25%)

    Is this AHU's power factor lower than its own established normal,
    and is it trending downward.

    Level term (70%):
        z = (own_median_PF − current_PF) / own_rstd_PF
        Positive z = PF below own median = penalty.

    Trend term (30%):
        Declining slope = PF getting worse over 7 days.

    Load discount:
        If power < 60% of own median power, scale score × 0.35.
        Motors naturally have poor PF at light load — this is not degradation.

    Returns score ∈ [0,1]
    """
    import numpy as np

    if pf is None or np.isnan(pf):
        return 0.0

    if ahu_median_pf is None or np.isnan(ahu_median_pf):
        return 0.0

    rstd = max(ahu_rstd_pf, MIN_RSTD.get("power_factor_avg", 0.008))
    if rstd <= 0:
        return 0.0

    z = (ahu_median_pf - pf) / rstd   # positive = below own normal = bad
    lv = sigmoid_score(z * SENSITIVITY["pf_degradation"])

    slope_n = float(np.clip(ols_slope(hist_pf_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, -slope_n) * SLOPE_SENS)

    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)

    # Load discount
    if (power is not None and not np.isnan(power)
        and ahu_median_pf > 0
        and power < PF_DISCOUNT_THRESHOLD * ahu_median_pf):
        score *= PF_DISCOUNT_FACTOR

    return clamp01(score)


def new_phase_imbalance_score(
    unbal: float,
    ahu_median_unbal: float,
    ahu_rstd_unbal: float,
    hist_unbal_series,
) -> float:
    """
    Score 3 · Phase Imbalance  (weight 25%)

    Is this AHU's current unbalance higher than its own established normal,
    and is it trending upward.

    Level term (70%):
        z = (current − own_median) / own_rstd
        Higher unbalance = worse.

    Trend term (30%):
        Rising slope over 7 days = worsening.

    Returns score ∈ [0,1]
    """
    import numpy as np

    if unbal is None or np.isnan(unbal):
        return 0.0

    if ahu_median_unbal is None or np.isnan(ahu_median_unbal):
        return 0.0

    rstd = max(ahu_rstd_unbal, MIN_RSTD.get("current_unbalance", 0.15))
    if rstd <= 0:
        return 0.0

    z = (unbal - ahu_median_unbal) / rstd
    lv = sigmoid_score(z * SENSITIVITY["phase_imbalance"])

    slope_n = float(np.clip(ols_slope(hist_unbal_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)

    return clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)


def new_thd_drift_score(
    thd_24h: float,
    ahu_median_thd: float,
    ahu_rstd_thd: float,
    hist_thd_24h_series,
) -> float:
    """
    Score 4 · THD Drift  (weight 15%)

    Is this AHU's harmonic distortion elevated above its own normal trend,
    and is it drifting upward.

    Input is the 24-hour rolling mean of composite THD (max of L1, L3).
    Using the rolling mean filters transient spikes from motor starts,
    lift operations, nearby equipment, etc.

    Baseline is also computed on the 24h-mean series (not instantaneous).
    This is critical — both sides of comparison must be on same time-scale.

    Returns (0.0, nan) if no THD data available for this AHU.
    Returns score ∈ [0,1]
    """
    import numpy as np

    if thd_24h is None or np.isnan(thd_24h):
        return 0.0

    if ahu_median_thd is None or np.isnan(ahu_median_thd):
        return 0.0

    rstd = max(ahu_rstd_thd, MIN_RSTD.get("composite_thd_24h", 0.15))
    if rstd <= 0:
        return 0.0

    z = (thd_24h - ahu_median_thd) / rstd
    lv = sigmoid_score(z * SENSITIVITY["thd_drift"])

    slope_n = float(np.clip(ols_slope(hist_thd_24h_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)

    return clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)


def new_overload_score(
    power: float,
    ahu_median_power: float,
    ahu_rstd_power: float,
    ahu_p95_power: float,
    hist_power_series,
) -> float:
    """
    Score 5 · Overload  (weight 20%)

    Is this AHU approaching or exceeding its own historical power ceiling,
    and is load trending upward.

    Three sub-components, all relative to this AHU's own history:

    A. Ceiling term (50%):
        power_ratio = current_power / own_p95_power
        demand = max(0, power_ratio − 0.85)
        score_A = sigmoid_score(demand × 8)

    B. Z-score term (30%):
        z = (current − own_median) / own_rstd
        score_B = sigmoid_score(z × 1.5)

    C. Trend term (20%):
        Rising load over 7 days = worsening.

    Final = 0.50 × score_A + 0.30 × score_B + 0.20 × score_C

    Size-neutral: e0105 (35 kW) and e0101 (0.67 kW) each judged
    against their own ceilings. Running at 95% of own p95 is concerning
    for both, regardless of absolute wattage.

    Returns score ∈ [0,1]
    """
    import numpy as np

    if power is None or np.isnan(power):
        return 0.0

    if ahu_median_power is None or np.isnan(ahu_median_power):
        return 0.0

    if ahu_p95_power is None or np.isnan(ahu_p95_power) or ahu_p95_power <= 0:
        return 0.0

    rstd = max(ahu_rstd_power, MIN_RSTD.get("power_total", 0.05))

    # A: ceiling proximity
    power_ratio = power / ahu_p95_power
    demand = max(0.0, power_ratio - 0.85)
    score_A = sigmoid_score(demand * 8.0)

    # B: z-score vs own mean
    z = (power - ahu_median_power) / rstd
    score_B = sigmoid_score(z * 1.5)

    # C: trend
    slope_n = float(np.clip(ols_slope(hist_power_series) / rstd, -10, 10))
    score_C = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)

    score = 0.50 * score_A + 0.30 * score_B + 0.20 * score_C
    return clamp01(score)


# ──────────────────────────────────────────────────────────────────────────────
# RISK SCORING FUNCTIONS (THE CORE RULE ENGINE)
# ──────────────────────────────────────────────

def energy_anomaly_score(
    current_energy: float,
    ahu_mean_delta_kwh: float,
    ahu_std_delta_kwh: float,
    min_history_hours: int = 24,
) -> float:
    """
    Calculate energy anomaly score using FAIR per-AHU baseline method.

    Purely relative - compares current hourly energy consumption to THIS AHU's
    own historical distribution. No absolute fleet comparison needed.

    Uses z-score: how many SDs above own mean is current consumption?
    This makes it inherently fair across differently-sized AHUs.

    Minimum History Requirement:
        - At least min_history_hours (default 24) of delta_kwh history
        - Slope calculation requires at least 3 data points

    Args:
        current_energy: Current delta_kwh (hourly energy consumption)
        ahu_mean_delta_kwh: This AHU's mean hourly energy
        ahu_std_delta_kwh: This AHU's hourly energy standard deviation
        min_history_hours: Minimum hours of history required (default 24)

    Returns:
        Energy anomaly score in [0, 1]
    """
    # Minimum history check
    if min_history_hours < 3:
        min_history_hours = 3

    # Handle missing/invalid data
    if current_energy is None or np.isnan(current_energy):
        return 0.5  # Neutral score when current value missing

    if ahu_mean_delta_kwh is None or np.isnan(ahu_mean_delta_kwh):
        return 0.5  # Neutral score when baseline missing

    # Minimum std to avoid division by zero
    MIN_STD_POWER = 0.05
    ahu_std_delta_kwh = max(ahu_std_delta_kwh, MIN_STD_POWER) if ahu_std_delta_kwh else MIN_STD_POWER

    # Compute z-score: how many SDs above own mean?
    z = (current_energy - ahu_mean_delta_kwh) / ahu_std_delta_kwh

    # Reference formula: raw = 0.6 * |z| + 0.4 * max(0, z)
    raw = 0.6 * abs(z) + 0.4 * max(0.0, z)

    return sigmoid_score(raw)


def power_factor_risk_score(
    current_pf: float,
    ahu_mean_pf: float,
    ahu_std_pf: float,
    fleet_median_pf: float,
    fleet_p5_pf: float,
    pf_slope_7d_normalized: float,
    power_ratio: float,
    current_power: float = None,
    ahu_mean_power: float = None,
) -> float:
    """
    Calculate Power Factor risk score using FAIR per-AHU baseline method.

    Uses blend of:
      - RELATIVE: how many SDs below THIS AHU's own mean PF (uses std)
      - ABSOLUTE: where this PF sits in fleet distribution
      - LOAD DISCOUNT: if running below 60% of own mean power, discount PF concern

    PF load discount: if running below 60% of own mean power,
    discount PF penalty significantly (low PF at low load is normal).

    Args:
        current_pf: Current power factor (0-1)
        ahu_mean_pf: This AHU's historical mean PF
        ahu_std_pf: This AHU's PF standard deviation
        fleet_median_pf: Fleet median PF
        fleet_p5_pf: Fleet 5th percentile PF
        pf_slope_7d_normalized: 7-day PF slope (normalized)
        power_ratio: Current power / historical p95
        current_power: Current power reading for load discount
        ahu_mean_power: AHU's mean power for load discount threshold

    Returns:
        PF risk score in [0, 1]
    """
    # Minimum std to avoid division by zero
    MIN_STD_PF = 0.005
    ahu_std_pf = max(ahu_std_pf, MIN_STD_PF) if ahu_std_pf else MIN_STD_PF

    # Handle missing/invalid current PF
    if current_pf is None or np.isnan(current_pf):
        return 0.5  # Neutral score when current value missing

    # Handle missing baseline
    if ahu_mean_pf is None or np.isnan(ahu_mean_pf):
        return 0.5  # Neutral score when baseline missing

    # Handle invalid fleet values (NaN or invalid denominator)
    if fleet_median_pf is None or np.isnan(fleet_median_pf):
        fleet_median_pf = 0.0
    if fleet_p5_pf is None or np.isnan(fleet_p5_pf):
        fleet_p5_pf = 0.0

    # RELATIVE: how many SDs below own mean? (lower PF = worse)
    if ahu_mean_pf:
        z_score = (current_pf - ahu_mean_pf) / ahu_std_pf
        # Flip: below mean = positive z = penalty
        z_score = -z_score
    else:
        z_score = 0.0

    # Raw score from z (use sensitivity of 2.5 like learn_from_this.py)
    raw_relative = max(0, z_score * 2.5)

    # ABSOLUTE: fleet-calibrated (uses actual fleet p5 and median)
    # For PF, lower is worse, so use p5 as the "bad" threshold
    # Guard against zero denominator
    denom = fleet_median_pf - fleet_p5_pf
    if denom > 0:
        raw_absolute = max(0, (fleet_median_pf - current_pf) / denom)
    else:
        raw_absolute = 0.0

    # Blend relative (60%) and absolute (40%)
    rel_score = sigmoid_score(raw_relative)
    abs_score = clamp01(raw_absolute)  # Clamp absolute score to [0,1]
    score = 0.60 * rel_score + 0.40 * abs_score

    # LOAD DISCOUNT: if below 60% of own mean power, discount score by 65%
    # Use module-level constants for consistency
    if (current_power is not None and ahu_mean_power is not None
        and ahu_mean_power > 0
        and current_power < PF_DISCOUNT_THRESHOLD * ahu_mean_power):
        score *= PF_DISCOUNT_FACTOR

    return float(max(0.0, min(1.0, score)))


def phase_imbalance_risk_score(
    current_unbalance: float,
    ahu_mean_unbalance: float,
    ahu_std_unbalance: float,
    fleet_median_unbalance: float,
    fleet_p95_unbalance: float,
    unbalance_slope_7d_normalized: float = 0.0
) -> float:
    """
    Calculate Phase Imbalance risk score using FAIR per-AHU baseline method.

    Uses blend of:
      - RELATIVE: how many SDs above THIS AHU's own typical unbalance
      - ABSOLUTE: where this sits in the fleet's unbalance distribution

    This handles AHUs with chronic high unbalance fairly:
      - They get HIGH absolute score (top of fleet distribution)
      - But LOW relative score when stable
      - Final: moderate unless deteriorating

    Args:
        current_unbalance: Current phase unbalance percentage
        ahu_mean_unbalance: This AHU's historical mean unbalance
        ahu_std_unbalance: This AHU's unbalance standard deviation
        fleet_median_unbalance: Fleet median unbalance
        fleet_p95_unbalance: Fleet 95th percentile unbalance
        unbalance_slope_7d_normalized: 7-day slope (normalized)

    Returns:
        Phase imbalance risk score in [0, 1]
    """
    # Minimum std to avoid division by zero
    MIN_STD_UNBAL = 0.10
    ahu_std_unbalance = max(ahu_std_unbalance, MIN_STD_UNBAL) if ahu_std_unbalance else MIN_STD_UNBAL

    # Handle missing/invalid current unbalance
    if current_unbalance is None or np.isnan(current_unbalance):
        return 0.5  # Neutral score when current value missing

    # Handle missing baseline
    if ahu_mean_unbalance is None or np.isnan(ahu_mean_unbalance):
        return 0.5  # Neutral score when baseline missing

    # Handle invalid fleet values (NaN or invalid denominator)
    if fleet_median_unbalance is None or np.isnan(fleet_median_unbalance):
        fleet_median_unbalance = 0.0
    if fleet_p95_unbalance is None or np.isnan(fleet_p95_unbalance):
        fleet_p95_unbalance = 1.0

    # RELATIVE: how many SDs above own mean?
    z_score = (current_unbalance - ahu_mean_unbalance) / ahu_std_unbalance
    raw_relative = z_score * 2.0

    # ABSOLUTE: where does this sit in fleet distribution?
    # Guard against zero denominator
    denom = fleet_p95_unbalance - fleet_median_unbalance
    if denom > 0:
        raw_absolute = max(0, (current_unbalance - fleet_median_unbalance) / denom)
    else:
        raw_absolute = 0.0

    # Blend relative (60%) and absolute (40%)
    score = 0.60 * sigmoid_score(raw_relative) + 0.40 * clamp01(raw_absolute)

    return float(max(0.0, min(1.0, score)))


def thd_risk_score(
    composite_thd_24h_mean: float,
    ahu_mean_thd: float,
    ahu_std_thd: float,
    fleet_median_thd: float,
    fleet_p95_thd: float,
    thd_slope_7d_normalized: float = 0.0
) -> float:
    """
    Calculate THD (Total Harmonic Distortion) risk score using FAIR method.

    Uses blend of:
      - RELATIVE: how many SDs above THIS AHU's own typical THD
      - ABSOLUTE: where this sits in the fleet's THD distribution

    Special case: AHUs without THD data should return 0.0 (handled by caller).

    Args:
        composite_thd_24h_mean: 24-hour rolling mean of max(THD_L1, THD_L3)
        ahu_mean_thd: This AHU's historical mean composite THD
        ahu_std_thd: This AHU's THD standard deviation
        fleet_median_thd: Fleet median composite THD
        fleet_p95_thd: Fleet 95th percentile composite THD
        thd_slope_7d_normalized: 7-day THD slope (normalized)

    Returns:
        THD risk score in [0, 1]
    """
    # Minimum std to avoid division by zero
    MIN_STD_THD = 0.10
    ahu_std_thd = max(ahu_std_thd, MIN_STD_THD) if ahu_std_thd else MIN_STD_THD

    # Handle missing/invalid current THD
    if composite_thd_24h_mean is None or np.isnan(composite_thd_24h_mean):
        return 0.5  # Neutral score when current value missing

    # Handle missing baseline
    if ahu_mean_thd is None or np.isnan(ahu_mean_thd):
        return 0.5  # Neutral score when baseline missing

    # Handle invalid fleet values (NaN or invalid denominator)
    if fleet_median_thd is None or np.isnan(fleet_median_thd):
        fleet_median_thd = 0.0
    if fleet_p95_thd is None or np.isnan(fleet_p95_thd):
        fleet_p95_thd = 1.0

    # RELATIVE: how many SDs above own mean?
    z_score = (composite_thd_24h_mean - ahu_mean_thd) / ahu_std_thd
    raw_relative = z_score * 2.0

    # ABSOLUTE: where does this sit in fleet distribution?
    # Guard against zero denominator
    denom = fleet_p95_thd - fleet_median_thd
    if denom > 0:
        raw_absolute = max(0, (composite_thd_24h_mean - fleet_median_thd) / denom)
    else:
        raw_absolute = 0.0

    # Blend relative (60%) and absolute (40%)
    score = 0.60 * sigmoid_score(raw_relative) + 0.40 * clamp01(raw_absolute)

    return float(max(0.0, min(1.0, score)))


def overload_risk_score(
    current_power: float,
    ahu_p95_power: float,
    ahu_mean_power: float,
    fleet_median_delta_kwh: float,
    fleet_p95_delta_kwh: float,
    min_history_hours: int = 24,
) -> float:
    """
    Calculate Overload risk score using FAIR per-AHU baseline method.

    Uses each AHU's OWN p95 as the ceiling reference (size-neutral):
      - e0105 (35 kW mean) uses its own p95 as ceiling
      - e0101 (0.67 kW mean) uses its own p95 as ceiling

    Score starts accumulating above 85% of the AHU's own p95.
    Also includes z-score of current power vs own mean.

    Minimum History Requirement:
        - At least min_history_hours (default 24) of power history
        - P95 baseline needs sufficient data to be meaningful

    Args:
        current_power: Current power reading
        ahu_p95_power: This AHU's 95th percentile power (ceiling reference)
        ahu_mean_power: This AHU's mean power
        fleet_median_delta_kwh: Fleet median energy consumption
        fleet_p95_delta_kwh: Fleet 95th percentile energy
        min_history_hours: Minimum hours of history required (default 24)

    Returns:
        Overload risk score in [0, 1]
    """
    # Minimum history check
    if min_history_hours < 3:
        min_history_hours = 3

    # Minimum std to avoid division by zero
    MIN_STD_POWER = 0.05

    # Check for missing/invalid data
    if current_power is None or np.isnan(current_power):
        return 0.5  # Neutral score when current value missing

    if ahu_mean_power is None or np.isnan(ahu_mean_power):
        return 0.5  # Neutral score when baseline missing

    if ahu_p95_power is None or np.isnan(ahu_p95_power) or ahu_p95_power <= 0:
        return 0.5  # Neutral score when P95 baseline unavailable

    # Relative: how far above own p95 ceiling?
    power_ratio = current_power / ahu_p95_power
    demand_term = max(0.0, power_ratio - 0.85)
    rel_score = sigmoid_score(demand_term * 8.0)

    # Also include z-score of current power vs own mean
    if ahu_mean_power is not None:
        std = max(abs(ahu_mean_power) * 0.15, MIN_STD_POWER)  # approximate std
        z_pwr = (current_power - ahu_mean_power) / std if std > 0 else 0
        rel_score = float(max(0.0, min(1.0, 0.7 * rel_score + 0.3 * sigmoid_score(z_pwr * 1.5))))

    # Absolute: fleet context (use delta_kwh fleet stats)
    denom = fleet_p95_delta_kwh - fleet_median_delta_kwh
    if denom > 0:
        abs_score = max(0, (current_power - fleet_median_delta_kwh) / denom)
    else:
        abs_score = 0.0

    # Blend relative (60%) and absolute (40%)
    score = 0.60 * rel_score + 0.40 * abs_score

    return float(max(0.0, min(1.0, score)))


def calculate_ahu_health_index(risk_scores: dict[str, float]) -> tuple[float, str]:
    """
    Calculate unified AHU Health Index from individual risk scores.

    health_index = 100 - weighted_sum(
        energy_anomaly_score × 0.15,
        pf_risk_score        × 0.25,
        imbalance_risk_score × 0.25,
        thd_risk_score       × 0.15,
        overload_risk_score  × 0.20
    )

    Args:
        risk_scores: Dict with keys: energy_anomaly, power_factor,
                     phase_imbalance, thd_drift, overload

    Returns:
        Tuple of (health_index: float, health_tier: str)
    """
    weighted_sum = 0.0
    for metric, score in risk_scores.items():
        weight = HEALTH_INDEX_WEIGHTS.get(metric, 0)
        # Handle NaN scores - treat as neutral (0.5) to avoid corrupting calculation
        if score is None or np.isnan(score):
            score = 0.5
        weighted_sum += score * weight

    health_index = 100 - (weighted_sum * 100)
    health_index = max(0, min(100, health_index))  # Clamp to [0, 100]

    health_tier = get_health_tier(health_index)

    return round(health_index, 1), health_tier

def calculate_ahu_health_index_fair(risk_scores: dict[str, float]) -> tuple[float, str]:
    """
    Calculate unified AHU Health Index from individual risk scores (FAIR method).

    Same formula as calculate_ahu_health_index but explicit about weights.
    health_index = 100 - penalty × 100
    where penalty = Σ weight_i × score_i

    All scores at 0 (exactly at own baseline) → index = 100
    All scores at 1 (maximum deviation on all metrics) → index = 0

    Args:
        risk_scores: Dict with keys: energy_anomaly, power_factor,
                     phase_imbalance, thd_drift, overload

    Returns:
        Tuple of (health_index: float, health_tier: str)
    """
    penalty = 0.0
    for metric, score in risk_scores.items():
        weight = HEALTH_INDEX_WEIGHTS.get(metric, 0)
        penalty += score * weight

    health_index = 100 - (penalty * 100)
    health_index = max(0, min(100, health_index))  # Clamp to [0, 100]

    health_tier = get_health_tier(health_index)
    return round(health_index, 1), health_tier


    return round(health_index, 1), health_tier


# ──────────────────────────────────────────────────────────────────────────────
# DATA FETCHING AND PROCESSING
# ──────────────────────────────────────────────

def fetch_ahu_metrics(ahu_id: str, time_range: str = "last_30d") -> dict[str, Any]:
    """
    Fetch all required metrics for a single AHU.

    Required metrics:
    - power_total, energy_import
    - power_factor_avg, power_factor_l1, power_factor_l2, power_factor_l3
    - current_unbalance, volts_unbalance
    - current_l1_thd, current_l3_thd, volts_l1_thd, volts_l3_thd
    - max_power_demand (or derived from power_total)

    Returns:
        Dict with metric values and historical data
    """
    metrics = {
        "device_id": ahu_id,
        "timestamp": datetime.now().isoformat(),
    }

    # Fetch time series data
    df = fetch_time_series(
        device_ids=[ahu_id],
        metric="power_total",
        time_range=time_range
    )

    if df.empty:
        return {"device_id": ahu_id, "error": "No data available", "data_quality": {"missing_data_pct": 100.0}}

    # Get latest value
    latest = df.iloc[-1] if len(df) > 0 else None

    # Calculate basic metrics
    float(latest[ahu_id]) if latest is not None and ahu_id in latest.index else None

    # Get energy (from same df if available)
    energy_df = fetch_time_series(
        device_ids=[ahu_id],
        metric="energy_import",
        time_range=time_range
    )

    energy_value = float(energy_df.iloc[-1][ahu_id]) if not energy_df.empty else None

    # Load prediction-based delta_kwh from CSV (for energy anomaly comparison)
    try:
        pred_deltas = load_prediction_deltas([ahu_id])
        pred_deltas.get(ahu_id)
    except Exception:
        pass

    # Compute historical baseline from InfluxDB energy data (hour-over-hour changes)
    delta_kwh_series = None
    if not energy_df.empty and len(energy_df) >= 2:
        try:
            energy_df_sorted = energy_df.sort_index()
            # Compute ALL deltas for proper statistics
            delta_kwh_series = energy_df_sorted[ahu_id].diff().dropna()
        except (IndexError, TypeError):
            delta_kwh_series = None
    # Use the most recent delta as current value for energy_anomaly_score
    delta_kwh = float(delta_kwh_series.iloc[-1]) if (delta_kwh_series is not None and len(delta_kwh_series) > 0) else None

    # Get power factor
    pf_df = fetch_time_series(
        device_ids=[ahu_id],
        metric="power_factor_avg",
        time_range=time_range
    )
    pf_value = float(pf_df.iloc[-1][ahu_id]) if not pf_df.empty else None

    # Get current unbalance
    unbalance_df = fetch_time_series(
        device_ids=[ahu_id],
        metric="current_unbalance",
        time_range=time_range
    )
    unbalance_value = float(unbalance_df.iloc[-1][ahu_id]) if not unbalance_df.empty else None

    # Get THD metrics
    thd_l1_df = fetch_time_series(
        device_ids=[ahu_id],
        metric="current_l1_thd",
        time_range=time_range
    )
    thd_l1_value = float(thd_l1_df.iloc[-1][ahu_id]) if not thd_l1_df.empty else None

    thd_l3_df = fetch_time_series(
        device_ids=[ahu_id],
        metric="current_l3_thd",
        time_range=time_range
    )
    thd_l3_value = float(thd_l3_df.iloc[-1][ahu_id]) if not thd_l3_df.empty else None

    # Composite THD (max of L1 and L3)
    composite_thd = max(thd_l1_value or 0, thd_l3_value or 0)

    # Calculate THD statistics from time series data
    thd_combined_df = pd.DataFrame()
    if not thd_l1_df.empty:
        thd_combined_df['l1'] = thd_l1_df[ahu_id]
    if not thd_l3_df.empty:
        thd_combined_df['l3'] = thd_l3_df[ahu_id]

    # Calculate composite THD time series for stats
    if not thd_combined_df.empty:
        composite_thd_series = thd_combined_df.max(axis=1)
        historical_thd_mean = composite_thd_series.mean()
        historical_thd_std = composite_thd_series.std()
    else:
        historical_thd_mean = None
        historical_thd_std = None

    # Calculate metrics from the full time range
    days_data = len(df)

    # Energy-based metrics
    if energy_df is not None and not energy_df.empty:
        df[ahu_id].mean() * 1  # approximate hourly kWh from power
        energy_values = energy_df[ahu_id].dropna()

        # Compute historical baseline from InfluxDB energy data (hour-over-hour changes)
        if len(energy_df) >= 2:
            energy_df_sorted = energy_df.sort_index()
            delta_kwh_series = energy_df_sorted[ahu_id].diff().dropna()
            historical_energy_median = delta_kwh_series.median() if len(delta_kwh_series) > 0 else None
        else:
            historical_energy_median = energy_values.median() if len(energy_values) > 0 else None
    else:
        historical_energy_median = None

    # PF metrics
    pf_values = pf_df[ahu_id].dropna() if not pf_df.empty else pd.Series()
    historical_pf_mean = pf_values.mean() if len(pf_values) > 0 else None
    historical_pf_std = pf_values.std() if len(pf_values) > 0 else None
    pf_slope = calculate_7d_slope(pf_df, ahu_id) if len(pf_df) > 0 else 0

    # Power metrics
    power_values = df[ahu_id].dropna()
    historical_power_max = power_values.quantile(0.99) if len(power_values) > 0 else None
    historical_power_mean = power_values.mean() if len(power_values) > 0 else None
    current_power = float(df.iloc[-1][ahu_id]) if not df.empty else None

    # Power ratio (current / P99)
    current_power / historical_power_max if (current_power and historical_power_max and historical_power_max > 0) else 0

    # Power slope
    power_slope = calculate_7d_slope(df, ahu_id) if len(df) > 0 else 0

    # Imbalance metrics
    unbalance_values = unbalance_df[ahu_id].dropna() if not unbalance_df.empty else pd.Series()
    historical_unbalance_mean = unbalance_values.mean() if len(unbalance_values) > 0 else None
    unbalance_slope = calculate_7d_slope(unbalance_df, ahu_id) if len(unbalance_df) > 0 else 0

    # Data quality
    total_points = len(df)
    missing_points = df[ahu_id].isna().sum() if not df.empty else 0
    missing_pct = (missing_points / total_points * 100) if total_points > 0 else 0

    metrics.update({
        "power": {
            "current": current_power,
            "historical_p99": historical_power_max,
            "mean_power": historical_power_mean,
            "power_ratio": current_power / historical_power_max if (current_power and historical_power_max) else None,
            "slope_7d": power_slope,
        },
        "energy": {
            "current": energy_value,
            "historical_median": historical_energy_median,
            "delta_kwh": delta_kwh,  # Current delta value
            "delta_series": delta_kwh_series,  # Full delta series for scoring
        },
        "power_factor": {
            "current": pf_value,
            "historical_mean": historical_pf_mean,
            "historical_std": historical_pf_std,
            "slope_7d_normalized": pf_slope,
        },
        "phase_imbalance": {
            "current": unbalance_value,
            "historical_mean": historical_unbalance_mean,
            "historical_std": unbalance_values.std() if len(unbalance_values) > 0 else None,
            "slope_7d_normalized": unbalance_slope,
        },
        "thd": {
            "composite_24h_mean": composite_thd,
            "ahu_mean_thd": historical_thd_mean,
            "ahu_std_thd": historical_thd_std,
            "slope_7d_normalized": calculate_7d_slope(thd_l1_df, ahu_id) if not thd_l1_df.empty else 0,
            "voltage_thd": None,  # Can add if needed
        },
        "data_quality": {
            "missing_data_pct": round(missing_pct, 2),
            "days_since_last_valid_reading": days_data,
        },
    })

    return metrics


def fetch_fleet_metrics(time_range: str = "last_30d") -> pd.DataFrame:
    """
    Fetch metrics for all AHUs in the fleet.

    Returns DataFrame with columns:
    - ahu_id, power_current, energy_current, pf_current, unbalance_current,
      thd_composite, pf_slope, unbalance_slope, power_slope
    """
    from models.schemas import ALLOWED_DEVICES

    fleet_data = []

    for ahu_id in sorted(ALLOWED_DEVICES):
        metrics = fetch_ahu_metrics(ahu_id, time_range)

        if "error" in metrics:
            continue

        fleet_data.append({
            "device_id": ahu_id,
            "power_current": metrics["power"]["current"],
            "energy_current": metrics["energy"]["current"],
            "pf_current": metrics["power_factor"]["current"],
            "unbalance_current": metrics["phase_imbalance"]["current"],
            "thd_composite": metrics["thd"]["composite_24h_mean"],
            "pf_slope_7d": metrics["power_factor"]["slope_7d_normalized"],
            "unbalance_slope_7d": metrics["phase_imbalance"]["slope_7d_normalized"],
            "power_slope_7d": metrics["power"]["power_ratio"],
            "max_demand_ratio": metrics["power"]["power_ratio"],
        })

    return pd.DataFrame(fleet_data)


def generate_fleet_risk_assessment(
    time_range: str = "last_30d",
    cluster_by_level: bool = True,
    devices_filter: list[str] | None = None
) -> dict[str, Any]:
    """
    Generate risk assessment for entire fleet.

    Args:
        time_range: Data period to analyze
        cluster_by_level: Group AHUs by building level for peer comparison
        devices_filter: Optional list of device IDs to process (None = all devices)

    Returns:
        Dict with fleet summary and individual assessments
    """

    # Get only devices that have data in the specified time range
    available_devices = get_available_devices(time_range)

    # Apply device filter if provided
    if devices_filter:
        available_devices = [d for d in available_devices if d in devices_filter]

    # Fetch metrics only for devices that have data
    assessments = []

    for ahu_id in available_devices:
        metrics = fetch_ahu_metrics(ahu_id, time_range)

        if "error" in metrics:
            # Device exists but has no data for this range, skip silently
            continue

        # Calculate individual risk scores
        pf_risk = power_factor_risk_score(
            current_pf=metrics["power_factor"]["current"] or 0.8,
            ahu_mean_pf=metrics["power_factor"]["historical_mean"] or 0.9,
            ahu_std_pf=metrics["power_factor"]["historical_std"] or 0.01,
            fleet_median_pf=0.9,
            fleet_p5_pf=0.85,
            pf_slope_7d_normalized=metrics["power_factor"]["slope_7d_normalized"] or 0,
            power_ratio=metrics["power"]["power_ratio"] or 0.5,
            current_power=metrics["power"]["current"],
            ahu_mean_power=metrics["power"]["mean_power"]
        )

        imbalance_risk = phase_imbalance_risk_score(
            current_unbalance=metrics["phase_imbalance"]["current"] or 2.0,
            ahu_mean_unbalance=metrics["phase_imbalance"].get("historical_mean", 2.0),
            ahu_std_unbalance=metrics["phase_imbalance"].get("historical_std", 0.5),
            fleet_median_unbalance=3.0,
            fleet_p95_unbalance=5.0,
            unbalance_slope_7d_normalized=metrics["phase_imbalance"]["slope_7d_normalized"] or 0
        )

        thd_risk = thd_risk_score(
            composite_thd_24h_mean=float(metrics["thd"]["composite_24h_mean"] or 3.0),
            ahu_mean_thd=float(metrics["thd"].get("ahu_mean_thd") or 2.5),
            ahu_std_thd=float(metrics["thd"].get("ahu_std_thd") or 0.5),
            fleet_median_thd=2.5,
            fleet_p95_thd=4.0,
            thd_slope_7d_normalized=float(metrics["thd"].get("slope_7d_normalized") or 0)
        )

        overload_risk = overload_risk_score(
            current_power=metrics["power"]["current"],
            ahu_p95_power=metrics["power"].get("historical_p95", metrics["power"]["historical_p99"]),
            ahu_mean_power=metrics["power"].get("mean_power", metrics["power"]["current"]),
            fleet_median_delta_kwh=0.5,
            fleet_p95_delta_kwh=1.0
        )

        # Energy anomaly uses delta_series for proper statistics
        delta_series = metrics["energy"].get("delta_series")

        if delta_series is not None and len(delta_series) > 0:
            # Compute statistics from full series
            ahu_mean_delta = delta_series.mean()
            ahu_std_delta = delta_series.std() if len(delta_series) > 1 else 0.1
            # Current delta is the most recent value
            current_delta = float(delta_series.iloc[-1])
            energy_anomaly = energy_anomaly_score(
                current_energy=current_delta,
                ahu_mean_delta_kwh=ahu_mean_delta,
                ahu_std_delta_kwh=ahu_std_delta
            )
        else:
            energy_anomaly = 0.5

        # Calculate health index
        risk_scores = {
            "energy_anomaly": energy_anomaly,
            "power_factor": pf_risk,
            "phase_imbalance": imbalance_risk,
            "thd_drift": thd_risk,
            "overload": overload_risk,
        }

        health_index, health_tier = calculate_ahu_health_index(risk_scores)

        # Determine cluster/level
        level = get_level_from_ahu_id(ahu_id) if cluster_by_level else "Fleet"

        assessments.append({
            "device_id": ahu_id,
            "timestamp": datetime.now().isoformat(),
            "health_index": health_index,
            "health_tier": health_tier,
            "level": level,
            "energy": {
                "forecast_24h_kwh": round(metrics["power"]["current"] * 24, 1) if metrics["power"]["current"] else None,
                "normal_range_kwh": [
                    round((metrics["energy"]["historical_median"] or 0) * 0.8, 1),
                    round((metrics["energy"]["historical_median"] or 0) * 1.2, 1)
                ] if metrics["energy"]["historical_median"] else None,
                "deviation_probability_pct": round((metrics["power"]["current"] / metrics["energy"]["historical_median"] - 1) * 100, 1) if (metrics["power"]["current"] and metrics["energy"]["historical_median"]) else None,
                "trend_7d": "increasing" if (metrics["power"]["slope_7d"] and metrics["power"]["slope_7d"] > 0.1) else
                            "decreasing" if (metrics["power"]["slope_7d"] and metrics["power"]["slope_7d"] < -0.1) else "stable",
            },
            "risk_scores": {
                "energy_anomaly": round(energy_anomaly, 3),
                "power_factor": {
                    "score": round(pf_risk, 3),
                    "severity": get_severity(pf_risk, "power_factor"),
                    "confidence": "High",
                    "signal": get_pf_signal(metrics["power_factor"]),
                },
                "phase_imbalance": {
                    "score": round(imbalance_risk, 3),
                    "severity": get_severity(imbalance_risk, "phase_imbalance"),
                    "confidence": "Moderate",
                    "signal": get_unbalance_signal(metrics["phase_imbalance"]),
                    "root_cause_uncertainty": "Cannot distinguish supply-side from load-side",
                },
                "thd_drift": {
                    "score": round(thd_risk, 3),
                    "severity": get_severity(thd_risk, "thd_drift"),
                    "confidence": "High",
                    "signal": get_thd_signal(metrics["thd"]),
                },
                "overload": {
                    "score": round(overload_risk, 3),
                    "severity": get_severity(overload_risk, "overload"),
                    "confidence": "Moderate",
                    "signal": get_overload_signal(metrics["power"]),
                    "seasonal_caveat": "Baseline covers full historical period",
                },
            },
            "safety_flags": compute_safety_flags(metrics),
            "data_quality": {
                **metrics["data_quality"],
                "model_source": "rule_based",
                "model_confidence_flag": "nominal" if metrics["data_quality"]["missing_data_pct"] < 10 else "degraded",
            },
        })

    # Generate fleet summary
    summary = generate_fleet_summary(assessments)

    return {
        "generated_at": datetime.now().isoformat(),
        "time_range": time_range,
        "total_ahus": len([a for a in assessments if "error" not in a]),
        "fleet_summary": summary,
        "assessments": sorted(assessments, key=lambda x: x.get("health_index", 0)),
    }


def generate_fleet_summary(assessments: list[dict]) -> dict[str, Any]:
    """
    Generate fleet-level summary from individual assessments.

    Returns:
        Dict with fleet statistics and top lists
    """
    valid_assessments = [a for a in assessments if "error" not in a]

    # Count by tier
    tier_counts = {"Healthy": 0, "Monitor": 0, "Maintenance Soon": 0, "Critical": 0}
    for a in valid_assessments:
        tier = a.get("health_tier", "Unknown")
        if tier in tier_counts:
            tier_counts[tier] += 1

    # Sort by health index (lowest first)
    sorted_by_health = sorted(valid_assessments, key=lambda x: x.get("health_index", 100))

    # Find rising risk (most negative health trend)
    # For now, use current risk scores as proxy
    rising_risk = sorted(
        valid_assessments,
        key=lambda x: (
            x["risk_scores"]["overload"]["score"] +
            x["risk_scores"]["phase_imbalance"]["score"]
        ),
        reverse=True
    )[:5]

    # Find improved units (highest health index)
    improved = sorted(valid_assessments, key=lambda x: x.get("health_index", 0), reverse=True)[:5]

    # Data quality issues
    data_quality_issues = [
        a for a in valid_assessments
        if a["data_quality"]["missing_data_pct"] > 5
    ]

    return {
        "tier_distribution": tier_counts,
        "top_5_lowest_health_index": [
            {"device_id": a["device_id"], "health_index": a["health_index"]}
            for a in sorted_by_health[:5]
        ],
        "top_5_rising_risk": [
            {"device_id": a["device_id"], "overload_score": a["risk_scores"]["overload"]["score"]}
            for a in rising_risk
        ],
        "top_5_improved": [
            {"device_id": a["device_id"], "health_index": a["health_index"]}
            for a in improved
        ],
        "data_quality_issues_count": len(data_quality_issues),
    }


def get_severity(score: float, risk_type: str) -> str:
    """Map risk score to severity level."""
    if score >= 0.8:
        return "Critical"
    elif score >= 0.6:
        return "Attention Required"
    elif score >= 0.4:
        return "Monitor"
    else:
        return "Normal"


def get_pf_signal(pf_data: dict) -> str:
    """Generate human-readable PF signal."""
    current = pf_data.get("current")
    slope = pf_data.get("slope_7d_normalized", 0)

    if current is None:
        return "PF data unavailable"

    if slope > 0.1:
        trend = "improving"
    elif slope < -0.1:
        trend = "declining"
    else:
        trend = "stable"

    return f"PF {current:.3f} ({trend}, slope: {slope:.4f})"


def get_unbalance_signal(unbalance_data: dict) -> str:
    """Generate human-readable unbalance signal."""
    current = unbalance_data.get("current")
    slope = unbalance_data.get("slope_7d_normalized", 0)

    if current is None:
        return "Unbalance data unavailable"

    if slope > 0.1:
        trend = "rising"
    elif slope < -0.1:
        trend = "improving"
    else:
        trend = "stable"

    return f"Unbalance {current:.2f}% ({trend} trend)"


def get_thd_signal(thd_data: dict) -> str:
    """Generate human-readable THD signal."""
    composite = thd_data.get("composite_24h_mean")

    if composite is None:
        return "THD data unavailable"

    if composite >= 5.0:
        level = "Critical (exceeds IEEE 519)"
    elif composite >= 3.5:
        level = "Elevated"
    else:
        level = "Normal"

    return f"L1/L3 THD {composite:.2f}% ({level})"


def get_overload_signal(power_data: dict) -> str:
    """Generate human-readable overload signal."""
    ratio = power_data.get("power_ratio")
    slope = power_data.get("slope_7d", 0)

    if ratio is None:
        return "Load data unavailable"

    pct = int(ratio * 100)

    if ratio >= 0.9:
        level = "Approaching capacity limit"
    elif ratio >= 0.8:
        level = "Near historical max"
    else:
        level = "Within normal range"

    trend = "increasing" if slope > 0.1 else "decreasing" if slope < -0.1 else "stable"

    return f"Power at {pct}% of historical max ({level}, trend: {trend})"



# ──────────────────────────────────────────────────────────────────────────────
# SAFETY FLAGS COMPUTATION
# ──────────────────────────────────────────────────────────────────────────────

SAFETY_FLAGS_DEF = {
    "THD_CHRONIC_HIGH":   ("composite_thd_24h", ">", 5.0),
    "IMBALANCE_SEVERE":   ("current_unbalance",  ">", 5.0),
    "PF_CHRONIC_LOW":     ("power_factor_avg",   "<",  0.85),
    "OVERLOAD_CHRONIC":   ("power_total",        ">",  None),  # computed separately
}


def compute_safety_flags(metrics: dict) -> list[str]:
    """
    Evaluate AHU metrics against structural safety thresholds.

    Returns list of flag strings for this AHU.

    Thresholds (from fair_health_scoring.py SAFETY_FLAGS_DEF):
      THD_CHRONIC_HIGH   composite_thd_24h > 5.0%
      IMBALANCE_SEVERE   current_unbalance  > 5.0%
      PF_CHRONIC_LOW     power_factor_avg   < 0.85
      OVERLOAD_CHRONIC   power_total        > 90% of own p95
    """
    flags = []

    # THD check
    thd_val = metrics.get("thd", {}).get("composite_24h_mean")
    if thd_val is not None and thd_val > 5.0:
        flags.append("THD_CHRONIC_HIGH")

    # Imbalance check
    unbal_val = metrics.get("phase_imbalance", {}).get("current")
    if unbal_val is not None and unbal_val > 5.0:
        flags.append("IMBALANCE_SEVERE")

    # PF check
    pf_val = metrics.get("power_factor", {}).get("current")
    if pf_val is not None and pf_val < 0.85:
        flags.append("PF_CHRONIC_LOW")

    # Overload check: power > 90% of p95
    power_val = metrics.get("power", {}).get("current")
    historical_p95 = metrics.get("power", {}).get("historical_p95")
    if (power_val is not None and historical_p95 is not None
        and historical_p95 > 0 and power_val / historical_p95 > 0.90):
        flags.append("OVERLOAD_CHRONIC")

    return flags


# ──────────────────────────────────────────────────────────────────────────────
# API ROUTE HELPERS
# ──────────────────────────────────────────────

async def get_electrical_risk_check(
    time_range: str = "last_30d",
    cluster_by_level: bool = True
) -> dict[str, Any]:
    """
    Main entry point for Electrical Risk Check API endpoint.

    Usage:
        GET /api/electrical-risk?time_range=last_30d
    """
    return await asyncio.to_thread(
        generate_fleet_risk_assessment,
        time_range=time_range,
        cluster_by_level=cluster_by_level
    )


async def get_ahu_risk_details(ahu_id: str, time_range: str = "last_30d") -> dict[str, Any]:
    """
    Get detailed risk assessment for a single AHU.

    Usage:
        GET /api/electrical-risk/{ahu_id}
    """
    metrics = fetch_ahu_metrics(ahu_id, time_range)

    if "error" in metrics:
        return {"error": metrics["error"]}

    # Calculate all risk scores
    pf_risk = power_factor_risk_score(
        current_pf=metrics["power_factor"]["current"] or 0.8,
        ahu_mean_pf=metrics["power_factor"]["historical_mean"] or 0.9,
        ahu_std_pf=metrics["power_factor"]["historical_std"] or 0.01,
        fleet_median_pf=0.9,
        fleet_p5_pf=0.85,
        pf_slope_7d_normalized=metrics["power_factor"]["slope_7d_normalized"] or 0,
        power_ratio=metrics["power"]["power_ratio"] or 0.5,
        current_power=metrics["power"]["current"],
        ahu_mean_power=metrics["power"]["mean_power"]
    )

    imbalance_risk = phase_imbalance_risk_score(
        current_unbalance=metrics["phase_imbalance"]["current"] or 2.0,
        ahu_mean_unbalance=metrics["phase_imbalance"].get("historical_mean", 2.0),
        ahu_std_unbalance=metrics["phase_imbalance"].get("historical_std", 0.5),
        fleet_median_unbalance=3.0,
        fleet_p95_unbalance=5.0,
        unbalance_slope_7d_normalized=metrics["phase_imbalance"]["slope_7d_normalized"] or 0
    )

    thd_risk = thd_risk_score(
        composite_thd_24h_mean=float(metrics["thd"]["composite_24h_mean"] or 3.0),
        ahu_mean_thd=float(metrics["thd"].get("ahu_mean_thd") or 2.5),
        ahu_std_thd=float(metrics["thd"].get("ahu_std_thd") or 0.5),
        fleet_median_thd=2.5,
        fleet_p95_thd=4.0,
        thd_slope_7d_normalized=float(metrics["thd"].get("slope_7d_normalized") or 0)
    )

    overload_risk = overload_risk_score(
        current_power=metrics["power"]["current"],
        ahu_p95_power=metrics["power"].get("historical_p95", metrics["power"]["historical_p99"]),
        ahu_mean_power=metrics["power"].get("mean_power", metrics["power"]["current"]),
        fleet_median_delta_kwh=0.5,
        fleet_p95_delta_kwh=1.0
    )

    # Energy anomaly uses delta_series for proper statistics
    delta_series = metrics["energy"].get("delta_series")

    if delta_series is not None and len(delta_series) > 0:
        # Compute statistics from full series
        ahu_mean_delta = delta_series.mean()
        ahu_std_delta = delta_series.std() if len(delta_series) > 1 else 0.1
        # Current delta is the most recent value
        current_delta = float(delta_series.iloc[-1])
        energy_anomaly = energy_anomaly_score(
            current_energy=current_delta,
            ahu_mean_delta_kwh=ahu_mean_delta,
            ahu_std_delta_kwh=ahu_std_delta
        )
    else:
        energy_anomaly = 0.5

    risk_scores = {
        "energy_anomaly": energy_anomaly,
        "power_factor": pf_risk,
        "phase_imbalance": imbalance_risk,
        "thd_drift": thd_risk,
        "overload": overload_risk,
    }

    health_index, health_tier = calculate_ahu_health_index(risk_scores)

    return {
        "device_id": ahu_id,
        "timestamp": datetime.now().isoformat(),
        "health_index": health_index,
        "health_tier": health_tier,
        "energy": {
            "forecast_24h_kwh": round(metrics["power"]["current"] * 24, 1) if metrics["power"]["current"] else None,
            "normal_range_kwh": [
                round((metrics["energy"]["historical_median"] or 0) * 0.8, 1),
                round((metrics["energy"]["historical_median"] or 0) * 1.2, 1)
            ] if metrics["energy"]["historical_median"] else None,
            "deviation_probability_pct": round((metrics["power"]["current"] / metrics["energy"]["historical_median"] - 1) * 100, 1) if (metrics["power"]["current"] and metrics["energy"]["historical_median"]) else None,
            "trend_7d": "increasing" if (metrics["power"]["slope_7d"] and metrics["power"]["slope_7d"] > 0.1) else
                        "decreasing" if (metrics["power"]["slope_7d"] and metrics["power"]["slope_7d"] < -0.1) else "stable",
        },
        "risk_scores": {
            "energy_anomaly": energy_anomaly,
            "power_factor": {
                "score": round(pf_risk, 3),
                "severity": get_severity(pf_risk, "power_factor"),
                "confidence": "High",
                "signal": get_pf_signal(metrics["power_factor"]),
            },
            "phase_imbalance": {
                "score": round(imbalance_risk, 3),
                "severity": get_severity(imbalance_risk, "phase_imbalance"),
                "confidence": "Moderate",
                "signal": get_unbalance_signal(metrics["phase_imbalance"]),
                "root_cause_uncertainty": "Cannot distinguish supply-side from load-side",
            },
            "thd_drift": {
                "score": round(thd_risk, 3),
                "severity": get_severity(thd_risk, "thd_drift"),
                "confidence": "High",
                "signal": get_thd_signal(metrics["thd"]),
            },
            "overload": {
                "score": round(overload_risk, 3),
                "severity": get_severity(overload_risk, "overload"),
                "confidence": "Moderate",
                "signal": get_overload_signal(metrics["power"]),
                "seasonal_caveat": "Baseline covers full historical period",
            },
        },
        "data_quality": {
            **metrics["data_quality"],
            "model_source": "rule_based",
            "model_confidence_flag": "nominal" if metrics["data_quality"]["missing_data_pct"] < 10 else "degraded",
        },
    }
