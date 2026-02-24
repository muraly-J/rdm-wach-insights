"""
risk_engine.py
──────────────
Rule-based electrical risk scoring system for AHU fleet.

This module implements the "Electrical Risk Check" - a deterministic, 
interpretable risk assessment system that requires no training data.

Output Schema (per AHU):
{
  "ahu_id": "wach_e0101",
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
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta

from backend.config import get_data_dir
from backend.core.influx_client import fetch_time_series, fetch_ranking, get_available_devices


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
    "Critical":       (0, 39),
    "MaintenanceSoon": (40, 59),
    "Monitor":        (60, 79),
    "Healthy":        (80, 100),
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
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────

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
    
    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
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
# ──────────────────────────────────────────────

def energy_anomaly_score(
    current_energy: float,
    historical_median: float,
    deviation_direction: str = "both"
) -> float:
    """
    Calculate energy anomaly score based on deviation from historical median.
    
    Args:
        current_energy: Current hourly energy consumption (kWh)
        historical_median: Historical same-weekday-same-hour median
        deviation_direction: "high" (only high deviations), 
                             "low" (only low deviations),
                             "both" (both directions)
    
    Returns:
        Energy anomaly score in [0, 1]
    """
    if historical_median == 0:
        return 0.5  # Neutral score
    
    deviation_pct = (current_energy - historical_median) / historical_median
    
    if deviation_direction == "high":
        if deviation_pct > 0:
            # High is more concerning for overload
            return sigmoid(5 * deviation_pct)
        return 0.0
    elif deviation_direction == "low":
        if deviation_pct < 0:
            return sigmoid(-5 * deviation_pct)
        return 0.0
    else:  # both directions
        # Both high and low are notable
        if deviation_pct >= 0:
            return sigmoid(5 * deviation_pct)
        else:
            return sigmoid(-5 * deviation_pct)


def power_factor_risk_score(
    current_pf: float,
    historical_mean_pf: float,
    pf_slope_7d_normalized: float,
    power_ratio: float
) -> float:
    """
    Calculate Power Factor risk score.
    
    PF Rule (from requirements):
    pf_risk_score = sigmoid(
        5 * max(0, (0.87 - current_pf) / 0.87)    # how far below 0.87 the current PF is
        + 10 * max(0, -pf_slope_7d_normalized)      # how fast PF is declining
        - 3 * (1 - power_ratio)                     # discount if under light load (low PF is expected)
    )
    
    Args:
        current_pf: Current power factor (0-1)
        historical_mean_pf: Historical mean PF for this AHU
        pf_slope_7d_normalized: 7-day PF slope (normalized)
        power_ratio: Current power / P95 rated power
    
    Returns:
        PF risk score in [0, 1]
    """
    baseline = THRESHOLDS["pf_baseline"]
    
    # How far below 0.87 the current PF is
    pf_deficit = max(0, (baseline - current_pf) / baseline)
    
    # How fast PF is declining (negative slope = bad)
    pf_decline = max(0, -pf_slope_7d_normalized)
    
    # Discount if under light load (low PF is expected at low loads)
    load_penalty = 3 * (1 - power_ratio)
    
    raw_score = (
        SIGMOID_K["power_factor"] * pf_deficit
        + 10 * pf_decline
        - load_penalty
    )
    
    return sigmoid(raw_score)


def phase_imbalance_risk_score(
    current_unbalance: float,
    unbalance_slope_7d_normalized: float
) -> float:
    """
    Calculate Phase Imbalance risk score.
    
    NEMA MG1 thresholds: 2% = warning, 5% = critical
    
    Imbalance Rule (from requirements):
    imbalance_risk_score = sigmoid(
        4 * max(0, (current_unbalance - 2.0) / 3.0)   # above 2% NEMA warning
        + 8 * max(0, unbalance_slope_7d_normalized)     # rising trend
    )
    
    Args:
        current_unbalance: Current phase unbalance percentage (0-100)
        unbalance_slope_7d_normalized: 7-day unbalance slope (normalized)
    
    Returns:
        Phase imbalance risk score in [0, 1]
    """
    warn_threshold = THRESHOLDS["imbalance_warn"]
    
    # Above 2% NEMA warning threshold
    above_warning = max(0, (current_unbalance - warn_threshold) / 3.0)
    
    # Rising trend
    rising_trend = max(0, unbalance_slope_7d_normalized)
    
    raw_score = (
        SIGMOID_K["phase_imbalance"] * above_warning
        + 8 * rising_trend
    )
    
    return sigmoid(raw_score)


def thd_risk_score(
    composite_thd_24h_mean: float,
    thd_slope_7d_l1_normalized: float,
    voltage_thd: Optional[float] = None
) -> float:
    """
    Calculate THD (Total Harmonic Distortion) risk score.
    
    IEEE 519 thresholds: baseline ~3.5%, limit ~5%
    
    THD Rule (from requirements):
    thd_risk_score = sigmoid(
        3 * max(0, (composite_thd_24h_mean - 3.5) / 1.5)   # above 3.5% baseline
        + 6 * max(0, thd_slope_7d_l1_normalized)             # rising trend
    )
    
    Args:
        composite_thd_24h_mean: 24-hour rolling mean of max(THD_L1, THD_L3)
        thd_slope_7d_l1_normalized: 7-day THD slope (normalized)
        voltage_thd: Optional voltage THD for origin diagnosis
    
    Returns:
        THD risk score in [0, 1]
    """
    baseline = THRESHOLDS["thd_baseline"]
    
    # Above 3.5% baseline
    above_baseline = max(0, (composite_thd_24h_mean - baseline) / 1.5)
    
    # Rising trend
    rising_trend = max(0, thd_slope_7d_l1_normalized)
    
    raw_score = (
        SIGMOID_K["thd_drift"] * above_baseline
        + 6 * rising_trend
    )
    
    return sigmoid(raw_score)


def overload_risk_score(
    max_demand_ratio: float,
    power_slope_7d_normalized: float,
    imbalance_under_load_normalized: float
) -> float:
    """
    Calculate Overload risk score.
    
    Overload Rule (from requirements):
    overload_risk_score = sigmoid(
        5 * max(0, max_demand_ratio - 0.85)          # approaching historical max
        + 3 * max(0, power_slope_7d_normalized)       # rising trend
        + 2 * imbalance_under_load_normalized         # stress interaction
    )
    
    Args:
        max_demand_ratio: Current power / historical p99 (0-1)
        power_slope_7d_normalized: 7-day power slope (normalized)
        imbalance_under_load_normalized: Phase unbalance under high load
    
    Returns:
        Overload risk score in [0, 1]
    """
    baseline = THRESHOLDS["overload_baseline"]
    
    # Approaching historical max
    approaching_max = max(0, max_demand_ratio - baseline)
    
    # Rising trend
    rising_trend = max(0, power_slope_7d_normalized)
    
    # Stress interaction
    stress_interaction = imbalance_under_load_normalized
    
    raw_score = (
        SIGMOID_K["overload"] * approaching_max
        + 3 * rising_trend
        + 2 * stress_interaction
    )
    
    return sigmoid(raw_score)


def calculate_ahu_health_index(risk_scores: Dict[str, float]) -> Tuple[float, str]:
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
        weighted_sum += score * weight
    
    health_index = 100 - (weighted_sum * 100)
    health_index = max(0, min(100, health_index))  # Clamp to [0, 100]
    
    health_tier = get_health_tier(health_index)
    
    return round(health_index, 1), health_tier


# ──────────────────────────────────────────────────────────────────────────────
# DATA FETCHING AND PROCESSING
# ──────────────────────────────────────────────

def fetch_ahu_metrics(ahu_id: str, time_range: str = "last_30d") -> Dict[str, Any]:
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
        "ahu_id": ahu_id,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Fetch time series data
    df = fetch_time_series(
        device_ids=[ahu_id],
        metric="power_total",
        time_range=time_range
    )
    
    if df.empty:
        return {"ahu_id": ahu_id, "error": "No data available", "data_quality": {"missing_data_pct": 100.0}}
    
    # Get latest value
    latest = df.iloc[-1] if len(df) > 0 else None
    
    # Calculate basic metrics
    power_total = float(latest[ahu_id]) if latest is not None and ahu_id in latest.index else None
    
    # Get energy (from same df if available)
    energy_df = fetch_time_series(
        device_ids=[ahu_id],
        metric="energy_import",
        time_range=time_range
    )
    
    energy_value = float(energy_df.iloc[-1][ahu_id]) if not energy_df.empty else None
    
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
    
    # Calculate metrics from the full time range
    days_data = len(df)
    
    # Energy-based metrics
    if energy_df is not None and not energy_df.empty:
        hourly_energy = df[ahu_id].mean() * 1  # approximate hourly kWh from power
        energy_values = df[ahu_id].dropna()
        
        # Historical same-weekday-same-hour median would need more complex logic
        # For MVP, use overall mean as baseline
        historical_energy_median = energy_values.median() if len(energy_values) > 0 else None
    else:
        historical_energy_median = None
    
    # PF metrics
    pf_values = pf_df[ahu_id].dropna() if not pf_df.empty else pd.Series()
    historical_pf_mean = pf_values.mean() if len(pf_values) > 0 else None
    pf_slope = calculate_7d_slope(pf_df, ahu_id) if len(pf_df) > 0 else 0
    
    # Power metrics
    power_values = df[ahu_id].dropna()
    historical_power_max = power_values.quantile(0.99) if len(power_values) > 0 else None
    current_power = float(df.iloc[-1][ahu_id]) if not df.empty else None
    
    # Power ratio (current / P99)
    max_demand_ratio = current_power / historical_power_max if (current_power and historical_power_max and historical_power_max > 0) else 0
    
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
            "power_ratio": current_power / historical_power_max if (current_power and historical_power_max) else None,
            "slope_7d": power_slope,
        },
        "energy": {
            "current": energy_value,
            "historical_median": historical_energy_median,
        },
        "power_factor": {
            "current": pf_value,
            "historical_mean": historical_pf_mean,
            "slope_7d_normalized": pf_slope,
        },
        "phase_imbalance": {
            "current": unbalance_value,
            "slope_7d_normalized": unbalance_slope,
        },
        "thd": {
            "composite_24h_mean": composite_thd,
            "slope_7d_l1_normalized": calculate_7d_slope(thd_l1_df, ahu_id) if not thd_l1_df.empty else 0,
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
    from backend.models.schemas import ALLOWED_DEVICES
    
    fleet_data = []
    
    for ahu_id in sorted(ALLOWED_DEVICES):
        metrics = fetch_ahu_metrics(ahu_id, time_range)
        
        if "error" in metrics:
            continue
        
        fleet_data.append({
            "ahu_id": ahu_id,
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
    devices_filter: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate risk assessment for entire fleet.
    
    Args:
        time_range: Data period to analyze
        cluster_by_level: Group AHUs by building level for peer comparison
        devices_filter: Optional list of device IDs to process (None = all devices)
    
    Returns:
        Dict with fleet summary and individual assessments
    """
    from backend.models.schemas import ALLOWED_DEVICES
    
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
            historical_mean_pf=metrics["power_factor"]["historical_mean"] or 0.9,
            pf_slope_7d_normalized=metrics["power_factor"]["slope_7d_normalized"] or 0,
            power_ratio=metrics["power"]["power_ratio"] or 0.5
        )
        
        imbalance_risk = phase_imbalance_risk_score(
            current_unbalance=metrics["phase_imbalance"]["current"] or 2.0,
            unbalance_slope_7d_normalized=metrics["phase_imbalance"]["slope_7d_normalized"] or 0
        )
        
        thd_risk = thd_risk_score(
            composite_thd_24h_mean=metrics["thd"]["composite_24h_mean"] or 3.0,
            thd_slope_7d_l1_normalized=metrics["thd"]["slope_7d_l1_normalized"] or 0
        )
        
        overload_risk = overload_risk_score(
            max_demand_ratio=metrics["power"]["power_ratio"] or 0.5,
            power_slope_7d_normalized=metrics["power"]["slope_7d"] or 0,
            imbalance_under_load_normalized=metrics["phase_imbalance"]["current"] / 10 if metrics["phase_imbalance"]["current"] else 0
        )
        
        # Energy anomaly (simplified - compare to mean)
        energy_median = metrics["energy"]["historical_median"]
        energy_current = metrics["energy"]["current"]
        
        if energy_median and energy_current:
            energy_anomaly = energy_anomaly_score(
                current_energy=energy_current,
                historical_median=energy_median
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
            "ahu_id": ahu_id,
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


def generate_fleet_summary(assessments: List[Dict]) -> Dict[str, Any]:
    """
    Generate fleet-level summary from individual assessments.
    
    Returns:
        Dict with fleet statistics and top lists
    """
    valid_assessments = [a for a in assessments if "error" not in a]
    
    # Count by tier
    tier_counts = {"Healthy": 0, "Monitor": 0, "MaintenanceSoon": 0, "Critical": 0}
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
            {"ahu_id": a["ahu_id"], "health_index": a["health_index"]}
            for a in sorted_by_health[:5]
        ],
        "top_5_rising_risk": [
            {"ahu_id": a["ahu_id"], "overload_score": a["risk_scores"]["overload"]["score"]}
            for a in rising_risk
        ],
        "top_5_improved": [
            {"ahu_id": a["ahu_id"], "health_index": a["health_index"]}
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


def get_pf_signal(pf_data: Dict) -> str:
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


def get_unbalance_signal(unbalance_data: Dict) -> str:
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


def get_thd_signal(thd_data: Dict) -> str:
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


def get_overload_signal(power_data: Dict) -> str:
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
# API ROUTE HELPERS
# ──────────────────────────────────────────────

async def get_electrical_risk_check(
    time_range: str = "last_30d",
    cluster_by_level: bool = True
) -> Dict[str, Any]:
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


async def get_ahu_risk_details(ahu_id: str, time_range: str = "last_30d") -> Dict[str, Any]:
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
        historical_mean_pf=metrics["power_factor"]["historical_mean"] or 0.9,
        pf_slope_7d_normalized=metrics["power_factor"]["slope_7d_normalized"] or 0,
        power_ratio=metrics["power"]["power_ratio"] or 0.5
    )
    
    imbalance_risk = phase_imbalance_risk_score(
        current_unbalance=metrics["phase_imbalance"]["current"] or 2.0,
        unbalance_slope_7d_normalized=metrics["phase_imbalance"]["slope_7d_normalized"] or 0
    )
    
    thd_risk = thd_risk_score(
        composite_thd_24h_mean=metrics["thd"]["composite_24h_mean"] or 3.0,
        thd_slope_7d_l1_normalized=metrics["thd"]["slope_7d_l1_normalized"] or 0
    )
    
    overload_risk = overload_risk_score(
        max_demand_ratio=metrics["power"]["power_ratio"] or 0.5,
        power_slope_7d_normalized=metrics["power"]["slope_7d"] or 0,
        imbalance_under_load_normalized=metrics["phase_imbalance"]["current"] / 10 if metrics["phase_imbalance"]["current"] else 0
    )
    
    energy_median = metrics["energy"]["historical_median"]
    energy_current = metrics["energy"]["current"]
    energy_anomaly = energy_anomaly_score(
        current_energy=energy_current or 0,
        historical_median=energy_median or 1
    ) if energy_median else 0.5
    
    risk_scores = {
        "energy_anomaly": energy_anomaly,
        "power_factor": pf_risk,
        "phase_imbalance": imbalance_risk,
        "thd_drift": thd_risk,
        "overload": overload_risk,
    }
    
    health_index, health_tier = calculate_ahu_health_index(risk_scores)
    
    return {
        "ahu_id": ahu_id,
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
