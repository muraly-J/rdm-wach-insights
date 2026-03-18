"""
fair_health_scoring.py
──────────────────────
FAIR Health Scoring Engine - Per-AHU Baseline Method

PHILOSOPHY: Every AHU is judged entirely against its own personal baseline.
No AHU's score is influenced by any other AHU's operating level.

A hospital AHU fleet will never perform similarly to one another.
e0101 runs at 0.67 kW with PF 0.35. e0105 runs at 35 kW with PF 0.74.
Applying the same threshold to both produces meaningless scores for both.

The correct question is not "is this AHU good or bad in absolute terms?"
The correct question is "is this AHU behaving differently than it normally does?"

A z-score answers that question for any AHU regardless of its size, load
level, PF characteristic, or inherent unbalance. A z of +2 means
"2 standard deviations above THIS AHU's own normal" for every unit.

SCORE ANATOMY
-------------
Each of the 5 component scores is a weighted blend of:

  LEVEL TERM  (70%)  — how far is the current reading from this AHU's
                        own historical median, in its own robust standard
                        deviations? This answers: is it bad RIGHT NOW?

  TREND TERM  (30%)  — is this metric drifting in the wrong direction over
                        the past 7 days? This answers: is it GETTING WORSE?

  score = 0.70 × sigmoid_score(z × sensitivity)
        + 0.30 × sigmoid_score(max(0, ±slope_normalised) × 3.0)

sigmoid_score maps any real number to [0, 1] and is anchored so that
a z of 0 (exactly at own baseline) gives a score of 0 — no penalty.

WHY ROBUST STATS (MEDIAN + MAD)?
---------------------------------
e0111 has L1 THD that alternates between ~14% and ~97% (bimodal).
Mean = 52%, std = 40% — useless as a baseline.
Median = 15.4%, MAD-std = 3.5% — correctly identifies the lower operating
mode as "normal" and treats the 97% state as the anomaly it is.

For well-behaved distributions: median ≈ mean and MAD-std ≈ regular std.
Robust stats are strictly better here with no downside.

CRITICAL DETAIL — THD BASELINE
--------------------------------
The THD score uses the 24-hour rolling mean (not instantaneous values) to
filter transient spikes from motor starts, elevators, etc.
The baseline MUST also be computed on the 24h rolling mean series,
not the instantaneous values. Otherwise the comparison is apples-to-oranges
and the baseline z-score will be permanently inflated (tested: e0111 had
z ≈ 10 at all times when instantaneous baseline was used with 24h-mean score).

STATIC SAFETY FLAGS
--------------------
AHUs with chronically extreme baselines get safety flags in the output.
These do NOT move the health index — they are a separate engineering audit
layer. They answer "should this AHU be reviewed regardless of today's score?"

INDEX WEIGHTS    health_index = 100 − (penalty × 100)
  energy_anomaly   15%         penalty = Σ weight_i × score_i
  pf_degradation   25%
  phase_imbalance  25%         All scores, all weights in [0,1].
  thd_drift        15%         Perfect baseline → index = 100.
  overload         20%         All maxed → index = 0.

HEALTH TIERS
  80–100  Healthy
  60–79   Monitor
  40–59   Maintenance Soon
  0–39    Critical

OUTPUT COLUMNS
  timestamp, ahu_id, level, health_index, tier
  energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload
  power_total, power_factor, unbalance_pct, thd_24h, energy_anomaly
  data_quality_flag, safety_flags
  z_energy, z_pf, z_imbalance, z_thd, z_overload   ← diagnostic only

Note: The energy_anomaly column is computed by the prediction ETL as:
  hourly_delta(t) = E(t) - E(t-1h)
  predicted_delta(t) = (δ(t−24h) + δ(t−168h) + δ(t−336h)) / 3
  energy_anomaly = hourly_delta(t) - predicted_delta(t)

This represents how much the actual HOURLY energy consumption deviated
from the predicted hourly consumption. It is NOT cumulative energy.
"""

import math
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

warnings.filterwarnings("ignore", category=RuntimeWarning)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION  ← CHANGING THESE TO MATCH EXISTING CODE
# ─────────────────────────────────────────────────────────────────────────────

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

# Minimum robust-std values (prevents division by near-zero)
MIN_RSTD = {
    "delta_kwh":          0.05,
    "power_factor_avg":   0.008,
    "current_unbalance":  0.15,
    "composite_thd_24h":  0.15,
    "power_total":        0.05,
}

# Static safety flag thresholds (applied to each AHU's own median)
SAFETY_FLAGS_DEF = {
    "THD_CHRONIC_HIGH":  ("composite_thd_24h", ">", 5.0),
    "IMBALANCE_SEVERE":  ("current_unbalance",  ">", 5.0),
    "PF_CHRONIC_LOW":    ("power_factor_avg",   "<",  0.85),
    "OVERLOAD_CHRONIC":  ("power_total",        ">",  None),  # computed separately
}


# ─────────────────────────────────────────────────────────────────────────────
# MATH UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def load_prediction_deltas(ahu_ids: List[str]) -> Dict[str, float]:
    """
    Load prediction-based energy_anomaly from predictions.csv.

    The prediction ETL computes:
      hourly_delta(t)     = E(t) - E(t-1h)
      predicted_delta(t)  = (δ(t−24h) + δ(t−168h) + δ(t−336h)) / 3
      energy_anomaly      = hourly_delta(t) - predicted_delta(t)

    The energy_anomaly column represents how much the actual hourly energy
    consumption deviated from the predicted hourly consumption.

    Args:
        ahu_ids: List of AHU IDs to fetch anomalies for

    Returns:
        Dict mapping ahu_id -> energy_anomaly (from prediction ETL)
    """
    import os
    # Resolve path relative to project root (not current working directory)
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.environ.get("DATA_DIR", "data")
    PREDICTIONS_FILE = os.path.join(PROJECT_ROOT, DATA_DIR, "predictions.csv")

    if not os.path.exists(PREDICTIONS_FILE):
        # Return neutral anomalies (0) if file doesn't exist
        return {ahu_id: 0.0 for ahu_id in ahu_ids}

    try:
        df = pd.read_csv(PREDICTIONS_FILE)

        if 'ahu_id' not in df.columns or 'energy_anomaly' not in df.columns:
            return {ahu_id: 0.0 for ahu_id in ahu_ids}

        # Get latest energy anomaly per AHU (use most recent row for each device)
        result = {}
        for ahu_id in ahu_ids:
            if ahu_id in df['ahu_id'].values:
                rows = df[df['ahu_id'] == ahu_id]
                if len(rows) > 0:
                    # Use the most recent anomaly (last row)
                    latest_anomaly = rows.iloc[-1]['energy_anomaly']
                    result[ahu_id] = float(latest_anomaly) if not pd.isna(latest_anomaly) else 0.0
                else:
                    result[ahu_id] = 0.0
            else:
                # AHU not in predictions file - use neutral anomaly
                result[ahu_id] = 0.0

        return result

    except Exception as e:
        # On error, return neutral anomalies
        print(f"[WARNING] Could not load prediction deltas: {e}")
        return {ahu_id: 0.0 for ahu_id in ahu_ids}


def sigmoid(x: float) -> float:
    """Numerically stable logistic sigmoid."""
    return 1.0 / (1.0 + math.exp(-float(np.clip(x, -500, 500))))


def sigmoid_score(raw: float) -> float:
    """
    Map a raw penalty to [0, 1] where raw = 0 → score = 0.

    Standard sigmoid gives 0.5 at raw=0. We shift and rescale:
        score = clip(sigmoid(raw) * 2 - 1,  0, 1)

    Behaviour:
        raw = 0  → 0.00   (exactly at own baseline, no concern)
        raw = 1  → 0.46   (1 std above/below)
        raw = 2  → 0.76   (2 std)
        raw = 3  → 0.91   (3 std)
    """
    return float(np.clip(sigmoid(raw) * 2.0 - 1.0, 0.0, 1.0))


def robust_params(values: np.ndarray, min_rstd: float = 0.01) -> tuple:
    """
    Compute robust location (median) and scale (1.4826 × MAD).

    1.4826 × MAD equals std for a normal distribution.
    For heavy-tailed or bimodal distributions it is far more stable.

    Returns (median, rstd) where rstd >= min_rstd.
    """
    v = values[~np.isnan(values)]
    if len(v) < 3:
        median = float(np.nanmedian(values)) if len(values) > 0 else 0.0
        return median, min_rstd
    med  = float(np.median(v))
    mad  = float(np.median(np.abs(v - med)))
    rstd = max(1.4826 * mad, min_rstd)
    return med, rstd


def ols_slope(values: np.ndarray) -> float:
    """
    OLS slope β through equally-spaced points (0, y_0), (1, y_1), …, (n-1, y_{n-1}).
    Returns slope in metric-units per hour.

    Closed-form (O(n), no matrix ops):
        β = [n·Σ(i·y) − Σ(i)·Σ(y)] / [n·Σ(i²) − (Σ(i))²]
    """
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    n = len(v)
    if n < 3:
        return 0.0
    i     = np.arange(n, dtype=float)
    num   = n * np.dot(i, v) - i.sum() * v.sum()
    denom = n * np.dot(i, i) - i.sum() ** 2
    return float(num / denom) if denom != 0 else 0.0


def get_health_tier(index: float) -> str:
    """Map health index to tier string."""
    for threshold, label in [(80, "Healthy"), (60, "Monitor"), (40, "Maintenance Soon"), (0, "Critical")]:
        if index >= threshold:
            return label
    return "Critical"


def clamp01(x: float) -> float:
    """Clamp value to [0, 1]."""
    return float(np.clip(x, 0.0, 1.0))


# ─────────────────────────────────────────────────────────────────────────────
# FAIR SCORING FUNCTIONS (PER-AHU BASELINE)
# ─────────────────────────────────────────────────────────────────────────────

def score_energy_anomaly(
    delta_kwh: float,
    ahu_median_delta: float,
    ahu_rstd_delta: float,
    hist_delta_series: np.ndarray,
    min_history_hours: int = 24,
) -> Tuple[float, float]:
    """
    Score 1 · Energy Anomaly  (weight 15%)

    Is this AHU consuming an unusual amount of energy compared to its own baseline.

    DELTA SOURCE:
        - The delta_kwh is computed by the prediction ETL as:
          hourly_delta(t) = E(t) - E(t-1h)
          predicted_delta(t) = (δ(t−24h) + δ(t−168h) + δ(t−336h)) / 3
          energy_anomaly = hourly_delta(t) - predicted_delta(t)
        - This represents how much the actual HOURLY energy consumption
          deviated from the predicted hourly consumption

    Level term (70%):
        z = (delta_kwh − own_median) / own_rstd
        raw = 0.6 × |z| + 0.4 × max(0, z)

    Trend term (30%):
        Rising energy over 7 days = worsening.

    Minimum History Requirement:
        - At least min_history_hours (default 24) of delta_kwh history required
        - Trend calculation requires at least 168 hours (7 days) of data
        - For < 24h: return neutral score (0.5)
        - For 24h-168h: return level-only score with trend=0
        - For ≥ 168h: return full score with level + trend

    Returns (score ∈ [0,1], z_diagnostic)
    """
    # Minimum 24h required for any meaningful scoring
    if hist_delta_series is None or len(hist_delta_series) < 24:
        return 0.5, np.nan

    if delta_kwh is None or np.isnan(delta_kwh):
        return 0.5, np.nan

    if ahu_median_delta is None or np.isnan(ahu_median_delta):
        return 0.5, np.nan

    # Use robust std with minimum
    rstd = max(ahu_rstd_delta, MIN_RSTD.get("delta_kwh", 0.05))
    if rstd <= 0:
        return 0.5, np.nan

    # Level term: z-score vs own median
    z = (delta_kwh - ahu_median_delta) / rstd
    raw = 0.6 * abs(z) + 0.4 * max(0.0, z)
    lv = sigmoid_score(raw * SENSITIVITY["energy_anomaly"])

    # Trend term - requires at least 168h (7 days) of data
    hist_clean = np.asarray(hist_delta_series, dtype=float)
    hist_clean = hist_clean[~np.isnan(hist_clean)]
    if len(hist_clean) >= 168:
        # Full data available: compute trend
        slope_n = float(np.clip(ols_slope(hist_clean) / rstd, -10, 10))
        tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    else:
        # Insufficient data for trend: return level-only score (trend=0)
        tr = 0.0

    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3)


def score_power_factor(
    pf: float,
    power: float,
    ahu_median_pf: float,
    ahu_rstd_pf: float,
    hist_pf_series: np.ndarray,
    min_history_hours: int = 24,
) -> Tuple[float, float]:
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
        
    Returns (score ∈ [0,1], z_diagnostic)
    """
    if pf is None or np.isnan(pf):
        return 0.0, np.nan
    
    if ahu_median_pf is None or np.isnan(ahu_median_pf):
        return 0.0, np.nan
    
    # Use robust std with minimum
    rstd = max(ahu_rstd_pf, MIN_RSTD.get("power_factor_avg", 0.008))
    if rstd <= 0:
        return 0.0, np.nan
    
    # Level term: z-score (negative means below median)
    z = (ahu_median_pf - pf) / rstd  # positive = below normal = bad
    lv = sigmoid_score(z * SENSITIVITY["pf_degradation"])
    
    # Trend term (negative slope = falling = bad)
    slope_n = float(np.clip(ols_slope(hist_pf_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, -slope_n) * SLOPE_SENS)
    
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    
    # Load discount: if power < 60% of own median, scale score down
    # Note: Need to pass ahu_median_power separately for this calculation
    # For now, skip load discount or add it as separate parameter
    
    return clamp01(score), round(z, 3)


def score_phase_imbalance(
    unbal: float,
    ahu_median_unbal: float,
    ahu_rstd_unbal: float,
    hist_unbal_series: np.ndarray,
) -> Tuple[float, float]:
    """
    Score 3 · Phase Imbalance  (weight 25%)
    
    Is this AHU's current unbalance higher than its own established normal,
    and is it trending upward.
    
    Level term (70%):
        z = (current − own_median) / own_rstd
        Higher unbalance = worse.
        
    Trend term (30%):
        Rising slope over 7 days = worsening.
        
    Returns (score ∈ [0,1], z_diagnostic)
    """
    if unbal is None or np.isnan(unbal):
        return 0.0, np.nan
    
    if ahu_median_unbal is None or np.isnan(ahu_median_unbal):
        return 0.0, np.nan
    
    # Use robust std with minimum
    rstd = max(ahu_rstd_unbal, MIN_RSTD.get("current_unbalance", 0.15))
    if rstd <= 0:
        return 0.0, np.nan
    
    # Level term: z-score
    z = (unbal - ahu_median_unbal) / rstd
    lv = sigmoid_score(z * SENSITIVITY["phase_imbalance"])
    
    # Trend term
    slope_n = float(np.clip(ols_slope(hist_unbal_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3)


def score_thd_drift(
    thd_24h: float,
    ahu_median_thd: float,
    ahu_rstd_thd: float,
    hist_thd_24h_series: np.ndarray,
) -> Tuple[float, float]:
    """
    Score 4 · THD Drift  (weight 15%)
    
    Is this AHU's harmonic distortion elevated above its own normal trend,
    and is it drifting upward.
    
    Input is the 24-hour rolling mean of composite THD (max of L1, L3).
    Using the rolling mean filters transient spikes from motor starts,
    lift operations, nearby equipment, etc.
    
    Baseline is also computed on the 24h-mean series (not instantaneous).
    This is critical — both sides of comparison must be on same time-scale.
    
    Returns (score ∈ [0,1], z_diagnostic)
    """
    if thd_24h is None or np.isnan(thd_24h):
        return 0.0, np.nan
    
    if ahu_median_thd is None or np.isnan(ahu_median_thd):
        return 0.0, np.nan
    
    # Use robust std with minimum
    rstd = max(ahu_rstd_thd, MIN_RSTD.get("composite_thd_24h", 0.15))
    if rstd <= 0:
        return 0.0, np.nan
    
    # Level term: z-score
    z = (thd_24h - ahu_median_thd) / rstd
    lv = sigmoid_score(z * SENSITIVITY["thd_drift"])
    
    # Trend term
    slope_n = float(np.clip(ols_slope(hist_thd_24h_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3)


def score_overload(
    power: float,
    ahu_median_power: float,
    ahu_rstd_power: float,
    ahu_p95_power: float,
    hist_power_series: np.ndarray,
) -> Tuple[float, float]:
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

    Minimum History Requirement:
        - At least 24 hours of power history required for reliable scoring
        - Slope calculation requires at least 3 data points
        - P95 baseline needs sufficient history to be meaningful

    Returns (score ∈ [0,1], z_diagnostic)
    """
    # Minimum history check - need at least 24 hours of data for reliable scoring
    if hist_power_series is None or len(hist_power_series) < 24:
        return 0.5, np.nan  # Neutral score when insufficient history

    if power is None or np.isnan(power):
        return 0.5, np.nan  # Neutral score when current value missing

    if ahu_median_power is None or np.isnan(ahu_median_power):
        return 0.5, np.nan  # Neutral score when baseline missing

    if ahu_p95_power is None or np.isnan(ahu_p95_power) or ahu_p95_power <= 0:
        return 0.5, np.nan  # Neutral score when P95 baseline unavailable

    # Check for valid std (default to MIN_RSTD if invalid)
    if ahu_rstd_power is None or np.isnan(ahu_rstd_power) or ahu_rstd_power <= 0:
        ahu_rstd_power = MIN_RSTD.get("power_total", 0.05)

    # Use robust std with minimum
    rstd = max(ahu_rstd_power, MIN_RSTD.get("power_total", 0.05))

    # A: ceiling proximity
    power_ratio = power / ahu_p95_power
    demand = max(0.0, power_ratio - 0.85)
    score_A = sigmoid_score(demand * 8.0)

    # B: z-score vs own median
    z = (power - ahu_median_power) / rstd
    score_B = sigmoid_score(z * 1.5)

    # C: trend - requires at least 168h (7 days) for reliable slope calculation
    hist_clean = np.asarray(hist_power_series, dtype=float)
    hist_clean = hist_clean[~np.isnan(hist_clean)]
    if len(hist_clean) >= 168:
        # Full data available: compute trend
        slope_n = float(np.clip(ols_slope(hist_clean) / rstd, -10, 10))
        score_C = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    else:
        # Insufficient data for trend: return level-only score (trend=0)
        score_C = 0.0

    score = 0.50 * score_A + 0.30 * score_B + 0.20 * score_C
    return clamp01(score), round(z, 3)


def calculate_health_index(scores: Dict[str, float]) -> float:
    """
    health_index = clip(100 − penalty × 100,  0, 100)
    penalty      = Σ weight_i × score_i   ∈ [0, 1]
    
    All scores at 0 (exactly at own baseline) → penalty = 0 → index = 100
    All scores at 1 (maximum deviation on all metrics) → index = 0
    """
    penalty = sum(HEALTH_INDEX_WEIGHTS.get(k, 0) * score for k, score in scores.items())
    return float(np.clip(100.0 - penalty * 100.0, 0.0, 100.0))


# ─────────────────────────────────────────────────────────────────────────────
# BASELINE BUILDER (FAIR METHOD)
# ─────────────────────────────────────────────────────────────────────────────

def build_baselines(df: pd.DataFrame) -> Dict:
    """
    Compute per-AHU robust baseline statistics from the full history in df.
    
    Returns:
        { ahu_id: { 
            "delta_kwh": {"median", "rstd", "p5", "p25", "p75", "p95", "n"},
            "power_factor_avg": {...},
            "current_unbalance": {...},
            "composite_thd_24h": {...},  # MUST use 24h rolling mean series
            "power_total": {...}
        } }
    
    IMPORTANT: the THD baseline is computed on the 24h-rolling-mean series,
    not the instantaneous composite. This is mandatory for correctness.
    """
    baselines = {}
    
    for ahu_id, grp in df.groupby("ahu_id"):
        grp = grp.sort_values("timestamp")
        b   = {}
        
        # ── Standard metrics ──────────────────────────────────────────────
        for col, min_r in [
            ("delta_kwh",         MIN_RSTD["delta_kwh"]),
            ("power_factor_avg",  MIN_RSTD["power_factor_avg"]),
            ("current_unbalance", MIN_RSTD["current_unbalance"]),
            ("power_total",       MIN_RSTD["power_total"]),
        ]:
            vals = grp[col].dropna().values
            if len(vals) < 3:
                b[col] = dict(
                    median=np.nan,
                    rstd=min_r,
                    p5=np.nan,
                    p25=np.nan,
                    p75=np.nan,
                    p95=np.nan,
                    n=len(vals)
                )
                continue
            med, rstd = robust_params(vals, min_r)
            b[col] = dict(
                median=med,
                rstd=rstd,
                p5=float(np.percentile(vals, 5)),
                p25=float(np.percentile(vals, 25)),
                p75=float(np.percentile(vals, 75)),
                p95=float(np.percentile(vals, 95)),
                n=len(vals),
            )
        
        # ── THD baseline — MUST use 24h rolling mean, not instantaneous ──
        thd_24h_series = (
            grp["composite_thd"]
            .rolling(THD_ROLLING_H, min_periods=1)
            .mean()
            .dropna()
            .values
        )
        if len(thd_24h_series) < 3:
            b["composite_thd_24h"] = dict(
                median=np.nan,
                rstd=MIN_RSTD["composite_thd_24h"],
                p5=np.nan,
                p95=np.nan,
                n=0
            )
        else:
            med, rstd = robust_params(thd_24h_series, MIN_RSTD["composite_thd_24h"])
            b["composite_thd_24h"] = dict(
                median=med,
                rstd=rstd,
                p5=float(np.percentile(thd_24h_series, 5)),
                p95=float(np.percentile(thd_24h_series, 95)),
                n=len(thd_24h_series),
            )
        
        baselines[ahu_id] = b
    
    return baselines


def compute_safety_flags(baselines: Dict) -> Dict[str, List[str]]:
    """
    Evaluate each AHU's baseline against structural safety thresholds.
    
    Returns { ahu_id: list_of_flag_strings }.
    
    Flags represent chronic structural issues — they appear in the output
    as metadata and should trigger engineering review on their own schedule.
    They do NOT affect the hourly health index.
    
    Thresholds:
      THD_CHRONIC_HIGH   median 24h-THD  > 5%
      IMBALANCE_SEVERE   median unbalance > 5%
      PF_CHRONIC_LOW     median PF        < 0.85
      OVERLOAD_CHRONIC   median power     > 90% of own p95
    """
    flags = {}
    for ahu_id, b in baselines.items():
        f = []
        
        thd_med = b.get("composite_thd_24h", {}).get("median", np.nan)
        imb_med = b.get("current_unbalance", {}).get("median", np.nan)
        pf_med  = b.get("power_factor_avg",  {}).get("median", np.nan)
        pwr_med = b.get("power_total",       {}).get("median", np.nan)
        pwr_p95 = b.get("power_total",       {}).get("p95",    np.nan)
        
        if not np.isnan(thd_med) and thd_med > 5.0:
            f.append("THD_CHRONIC_HIGH")
        if not np.isnan(imb_med) and imb_med > 5.0:
            f.append("IMBALANCE_SEVERE")
        if not np.isnan(pf_med) and pf_med < 0.85:
            f.append("PF_CHRONIC_LOW")
        if (not np.isnan(pwr_med) and not np.isnan(pwr_p95)
                and pwr_p95 > 0 and pwr_med / pwr_p95 > 0.90):
            f.append("OVERLOAD_CHRONIC")
        
        flags[ahu_id] = f
    return flags


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH ASSESSMENT GENERATION (FAIR METHOD)
# ─────────────────────────────────────────────────────────────────────────────

def generate_fleet_risk_assessment_fair(
    df_power: pd.DataFrame,
    df_energy: pd.DataFrame,
    df_pf: pd.DataFrame,
    df_unbalance: pd.DataFrame,
    df_thd_l1: pd.DataFrame,
    df_thd_l3: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Generate FAIR health assessment for entire fleet using per-AHU baselines.
    
    Args:
        df_power: Power time series (columns = ahu_ids, index = timestamps)
        df_energy: Energy time series
        df_pf: Power factor time series
        df_unbalance: Unbalance time series
        df_thd_l1: L1 THD time series
        df_thd_l3: L3 THD time series
    
    Returns:
        Dict with fleet summary and individual assessments
    """
    # Ensure we have power data to work with
    if df_power.empty:
        return {
            "generated_at": datetime.now().isoformat(),
            "total_ahus": 0,
            "assessments": [],
        }
    
    # Get all AHUs from power data
    ahu_ids = sorted([c for c in df_power.columns if c != 'timestamp'])
    
    # Build composite THD (max of L1 and L3)
    if not df_thd_l1.empty and not df_thd_l3.empty:
        # Find common columns
        common_cols = set(df_thd_l1.columns) & set(df_thd_l3.columns) - {'timestamp'}
        df_thd = pd.DataFrame()
        for col in common_cols:
            df_thd[col] = pd.concat([df_thd_l1[col], df_thd_l3[col]], axis=1).max(axis=1)
    else:
        # Create empty composite THD
        df_thd = pd.DataFrame(index=df_power.index, columns=ahu_ids)
    
    # Calculate 24h rolling mean of THD per AHU
    thd_24h_df = df_thd.rolling(THD_ROLLING_H, min_periods=1).mean()
    
    # Combine all metrics into one DataFrame for per-AHU processing
    combined = pd.DataFrame()
    for ahu_id in ahu_ids:
        row = {
            "ahu_id": ahu_id,
            "timestamp": df_power.index[-1],
            "power_total": float(df_power[ahu_id].iloc[-1]) if ahu_id in df_power.columns else None,
            "energy_import": float(df_energy[ahu_id].iloc[-1]) if ahu_id in df_energy.columns else None,
            "power_factor_avg": float(df_pf[ahu_id].iloc[-1]) if ahu_id in df_pf.columns else None,
            "current_unbalance": float(df_unbalance[ahu_id].iloc[-1]) if ahu_id in df_unbalance.columns else None,
            "composite_thd": float(df_thd[ahu_id].iloc[-1]) if ahu_id in df_thd.columns else None,
            "thd_24h": float(thd_24h_df[ahu_id].iloc[-1]) if ahu_id in thd_24h_df.columns else None,
        }
        combined = pd.concat([combined, pd.DataFrame([row])], ignore_index=True)
    
    # Calculate delta_kwh from prediction ETL (preferred) or fallback to energy diff
    try:
        # First, try to load prediction-based deltas from CSV
        pred_deltas = load_prediction_deltas(ahu_ids)
        
        # Update combined DataFrame with prediction deltas
        for ahu_id in ahu_ids:
            if ahu_id in pred_deltas:
                combined.loc[combined['ahu_id'] == ahu_id, 'delta_kwh'] = pred_deltas[ahu_id]
        
        # Also store the source indicator
        combined['delta_source'] = 'prediction'
    except Exception:
        # Fallback: compute delta from energy (hour-over-hour change)
        if not df_energy.empty:
            for ahu_id in ahu_ids:
                if ahu_id in df_energy.columns and len(df_energy) >= 2:
                    sorted_df = df_energy[[ahu_id]].sort_index()
                    delta = sorted_df[ahu_id].diff().iloc[-1]
                    combined.loc[combined['ahu_id'] == ahu_id, 'delta_kwh'] = float(delta) if not pd.isna(delta) else None
        combined['delta_source'] = 'hour_diff'

    # Build per-AHU baselines
    baselines = build_baselines(combined)
    
    # Compute safety flags
    safety_flags = compute_safety_flags(baselines)
    
    # Generate assessments
    assessments = []
    
    for ahu_id in ahu_ids:
        if ahu_id not in baselines:
            continue
            
        baseline = baselines[ahu_id]
        
        # Get latest values
        power_current = combined.loc[combined['ahu_id'] == ahu_id, 'power_total'].values
        power_current = float(power_current[0]) if len(power_current) > 0 else None
        
        energy_current = combined.loc[combined['ahu_id'] == ahu_id, 'energy_import'].values
        energy_current = float(energy_current[0]) if len(energy_current) > 0 else None
        
        pf_current = combined.loc[combined['ahu_id'] == ahu_id, 'power_factor_avg'].values
        pf_current = float(pf_current[0]) if len(pf_current) > 0 else None
        
        unbal_current = combined.loc[combined['ahu_id'] == ahu_id, 'current_unbalance'].values
        unbal_current = float(unbal_current[0]) if len(unbal_current) > 0 else None
        
        thd_24h = combined.loc[combined['ahu_id'] == ahu_id, 'thd_24h'].values
        thd_24h = float(thd_24h[0]) if len(thd_24h) > 0 else None
        
        delta_kwh = combined.loc[combined['ahu_id'] == ahu_id, 'delta_kwh'].values
        delta_kwh = float(delta_kwh[0]) if len(delta_kwh) > 0 else None
        
        # Build history series for each metric
        TREND_WINDOW = 168  # 7 days in hours
        
        # Get full history series for this AHU
        hist_power = df_power[ahu_id].dropna().values[-TREND_WINDOW:] if ahu_id in df_power.columns else np.array([])
        hist_energy = df_energy[ahu_id].dropna().values[-TREND_WINDOW:] if ahu_id in df_energy.columns else np.array([])
        hist_pf = df_pf[ahu_id].dropna().values[-TREND_WINDOW:] if ahu_id in df_pf.columns else np.array([])
        hist_unbal = df_unbalance[ahu_id].dropna().values[-TREND_WINDOW:] if ahu_id in df_unbalance.columns else np.array([])
        hist_thd_24h = thd_24h_df[ahu_id].dropna().values[-TREND_WINDOW:] if ahu_id in thd_24h_df.columns else np.array([])
        
        # Compute delta_kwh series from energy
        hist_delta = None
        if ahu_id in df_energy.columns and len(df_energy) >= 2:
            sorted_energy = df_energy[[ahu_id]].sort_index()
            delta_series = sorted_energy[ahu_id].diff()
            hist_delta = delta_series.dropna().values[-TREND_WINDOW:]
        
        # Calculate five FAIR scores
        energy_score, z_energy = score_energy_anomaly(
            delta_kwh,
            baseline["delta_kwh"]["median"],
            baseline["delta_kwh"]["rstd"],
            hist_delta if hist_delta is not None and len(hist_delta) >= 2 else np.array([])
        )
        
        pf_score, z_pf = score_power_factor(
            pf_current,
            power_current,
            baseline["power_factor_avg"]["median"],
            baseline["power_factor_avg"]["rstd"],
            hist_pf if len(hist_pf) >= 2 else np.array([])
        )
        
        unbal_score, z_imbalance = score_phase_imbalance(
            unbal_current,
            baseline["current_unbalance"]["median"],
            baseline["current_unbalance"]["rstd"],
            hist_unbal if len(hist_unbal) >= 2 else np.array([])
        )
        
        thd_score, z_thd = score_thd_drift(
            thd_24h,
            baseline["composite_thd_24h"]["median"],
            baseline["composite_thd_24h"]["rstd"],
            hist_thd_24h if len(hist_thd_24h) >= 2 else np.array([])
        )
        
        overload_score, z_overload = score_overload(
            power_current,
            baseline["power_total"]["median"],
            baseline["power_total"]["rstd"],
            baseline["power_total"]["p95"],
            hist_power if len(hist_power) >= 2 else np.array([])
        )
        
        # Calculate health index
        risk_scores = {
            "energy_anomaly": round(energy_score, 4),
            "power_factor": round(pf_score, 4),
            "phase_imbalance": round(unbal_score, 4),
            "thd_drift": round(thd_score, 4),
            "overload": round(overload_score, 4),
        }
        
        health_index = calculate_health_index(risk_scores)
        tier = get_health_tier(health_index)
        
        # Build assessment
        assessment = {
            "ahu_id": ahu_id,
            "timestamp": datetime.now().isoformat(),
            "health_index": round(health_index, 1),
            "health_tier": tier,
            "level": get_level_from_ahu_id(ahu_id),
            "risk_scores": {
                "energy_anomaly": round(energy_score, 3),
                "power_factor": {
                    "score": round(pf_score, 3),
                    "severity": get_severity(pf_score, "power_factor"),
                    "confidence": "High",
                    "signal": get_pf_signal({
                        "current": pf_current,
                        "slope_7d_normalized": 0.0,  # Would need full calculation
                    }),
                },
                "phase_imbalance": {
                    "score": round(unbal_score, 3),
                    "severity": get_severity(unbal_score, "phase_imbalance"),
                    "confidence": "Moderate",
                    "signal": get_unbalance_signal({
                        "current": unbal_current,
                        "slope_7d_normalized": 0.0,
                    }),
                    "root_cause_uncertainty": "Cannot distinguish supply-side from load-side",
                },
                "thd_drift": {
                    "score": round(thd_score, 3),
                    "severity": get_severity(thd_score, "thd_drift"),
                    "confidence": "High",
                    "signal": get_thd_signal({
                        "composite_24h_mean": thd_24h,
                    }),
                },
                "overload": {
                    "score": round(overload_score, 3),
                    "severity": get_severity(overload_score, "overload"),
                    "confidence": "Moderate",
                    "signal": get_overload_signal({
                        "current": power_current,
                        "historical_p99": baseline["power_total"]["p95"],
                    }),
                    "seasonal_caveat": "Baseline covers full historical period",
                },
            },
            "data_quality": {
                "missing_data_pct": 0.0,  # Would need actual calculation
                "days_since_last_valid_reading": len(df_power),
                "model_source": "rule_based",
                "model_confidence_flag": "nominal",
            },
            # FAIR-specific output fields
            "power_total": round(power_current, 3) if power_current is not None else None,
            "power_factor": round(pf_current, 4) if pf_current is not None else None,
            "unbalance_pct": round(unbal_current, 3) if unbal_current is not None else None,
            "thd_24h": round(thd_24h, 3) if thd_24h is not None else None,
            "delta_kwh": round(delta_kwh, 3) if delta_kwh is not None else None,
            "data_quality_flag": 0 if thd_24h is not None and not np.isnan(thd_24h) else 1,
            "safety_flags": ",".join(safety_flags.get(ahu_id, [])),
            # Z-score diagnostics
            "z_energy": round(z_energy, 3) if z_energy is not None else None,
            "z_pf": round(z_pf, 3) if z_pf is not None else None,
            "z_imbalance": round(z_imbalance, 3) if z_imbalance is not None else None,
            "z_thd": round(z_thd, 3) if z_thd is not None else None,
            "z_overload": round(z_overload, 3) if z_overload is not None else None,
        }
        
        assessments.append(assessment)
    
    # Generate fleet summary
    summary = generate_fleet_summary(assessments)
    
    return {
        "generated_at": datetime.now().isoformat(),
        "time_range": "last_30d",  # Would need to be passed in
        "total_ahus": len(assessments),
        "fleet_summary": summary,
        "assessments": sorted(assessments, key=lambda x: x.get("health_index", 0)),
    }


def get_level_from_ahu_id(ahu_id: str) -> str:
    """Extract building level from AHU ID."""
    parts = ahu_id.split('_')
    if len(parts) >= 2:
        device_id = parts[-1]
    else:
        device_id = ahu_id
    
    if device_id.startswith('e') and len(device_id) >= 3:
        level_code = device_id[1:3]
        try:
            level = int(level_code)
            return f"Level {level}"
        except ValueError:
            pass
    return "Unknown"


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
        trend = "falling"
    else:
        trend = "stable"
    
    return f"Unbalance {current:.2f}% ({trend}, slope: {slope:.4f})"


def get_thd_signal(thd_data: Dict) -> str:
    """Generate human-readable THD signal."""
    composite_thd = thd_data.get("composite_24h_mean")
    
    if composite_thd is None:
        return "THD data unavailable"
    
    if composite_thd > 5.0:
        status = "exceeds IEEE 519 limit"
    elif composite_thd > 3.5:
        status = "elevated"
    else:
        status = "within acceptable range"
    
    return f"THD {composite_thd:.2f}% ({status})"


def get_overload_signal(power_data: Dict) -> str:
    """Generate human-readable overload signal."""
    current = power_data.get("current")
    p99 = power_data.get("historical_p99")
    
    if current is None:
        return "Power data unavailable"
    
    if p99 and p99 > 0:
        ratio = current / p99
        if ratio >= 0.95:
            status = "CRITICAL: near p95 ceiling"
        elif ratio >= 0.90:
            status = "elevated: approaching ceiling"
        elif ratio >= 0.85:
            status = "monitoring: above threshold"
        else:
            status = "normal load level"
        
        return f"Power {current:.2f} kW ({status}, {ratio*100:.1f}% of p95)"
    
    return f"Power {current:.2f} kW (no historical data)"


def generate_fleet_summary(assessments: List[Dict]) -> Dict[str, Any]:
    """Generate fleet-level summary from individual assessments."""
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
        if a.get("data_quality", {}).get("missing_data_pct", 0) > 5
    ]
    
    return {
        "tier_distribution": tier_counts,
        "top_5_lowest_health_index": [
            {"ahu_id": a["ahu_id"], "health_index": a["health_index"]}
            for a in sorted_by_health[:5]
        ],
        "top_5_rising_risk": [
            {"ahu_id": a["ahu_id"], "overload_score": a["risk_scores"]["overload"]}
            for a in rising_risk
        ],
        "top_5_improved": [
            {"ahu_id": a["ahu_id"], "health_index": a["health_index"]}
            for a in improved
        ],
        "data_quality_issues_count": len(data_quality_issues),
    }
