# Learning History & Architecture Notes

## CSV Architecture Update (March 12, 2026)

The dual CSV architecture was implemented to enable hourly granularity for the 24h health index chart. This separation addresses the original problem where only 1 data point was displayed for 24h charts.

**Files Created:**
- [README_CSV_ARCHITECTURE.md](./README_CSV_ARCHITECTURE.md) - Quick start guide
- [data_flows.md](./data_flows.md) - Complete data flow diagrams
- [csv_file_formats.md](./csv_file_formats.md) - CSV schema documentation
- [health_index_chart.md](./health_index_chart.md) - Chart integration guide

**Problem Solved:**
- Before: 24h chart showed only 1 data point (daily aggregate)
- After: 24h chart shows 24 hourly data points for smooth visualization

WHY THE PREVIOUS APPROACH WAS UNFAIR
──────────────────────────────────────
The original scoring applied fixed engineering thresholds fleet-wide:
  - NEMA MG1 5% for phase imbalance
  - IEEE 519 5% for THD
  - 0.87 for power factor

For this fleet these thresholds are not appropriate reference points:
  - 58% of all unbalance readings exceed 5%
  - 72% of all THD readings exceed 5%
  - 94% of all PF readings are below 0.87

Using these thresholds locks most AHUs at near-maximum scores on three
of five components every single hour. The index has almost no dynamic
range. A genuine deterioration event is invisible against the noise of
permanently-maxed scores.

THE FAIR APPROACH
──────────────────
For each metric, the score is a BLEND of two components:

  RELATIVE SCORE (60% weight):
    How many standard deviations is the current reading from THIS AHU's
    own 7-day mean? Detects CHANGE from each unit's personal baseline.
    Inherently fair to size and operating level differences.

  ABSOLUTE SCORE (40% weight):
    Where does this reading sit within the FLEET's actual distribution?
    Uses fleet percentiles computed from this data, not external standards.
    Ensures that genuinely extreme values (fleet outliers) still register.

  FINAL SCORE = 0.60 * relative_score + 0.40 * absolute_score

This means:
  - An AHU with chronically high unbalance that is STABLE scores moderately
    (high absolute, low relative) — it is acknowledged but not in alarm.
  - The same AHU getting meaningfully WORSE scores high (high on both) — alarm.
  - A well-behaved AHU that spikes scores high on relative — alarm.
  - e0111 with genuinely anomalous THD (52% L1) scores high on both — correct.

INDEX WEIGHTS (unchanged from original):
  energy_anomaly  : 0.15
  pf_degradation  : 0.25
  phase_imbalance : 0.25
  thd_drift       : 0.15
  overload        : 0.20

OUTPUT CSV SCHEMA:
  timestamp, ahu_id, level, health_index,
  energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload,
  [diagnostic columns: raw values + subscores]
"""

import math
import numpy as np
import pandas as pd
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────────────

INPUT_CSV  = Path("/mnt/user-data/uploads/level1_raw_metrics.csv")
OUTPUT_CSV = Path("/mnt/user-data/outputs/level1_raw_metrics_health_fair.csv")
LEVEL_NAME = "Level 1"

# Index component weights — must sum to 1.0
WEIGHTS = {
    "energy_anomaly":  0.15,
    "pf_degradation":  0.25,
    "phase_imbalance": 0.25,
    "thd_drift":       0.15,
    "overload":        0.20,
}

# Blend ratio: how much of each score comes from relative vs absolute
RELATIVE_WEIGHT = 0.60   # within-AHU z-score component
ABSOLUTE_WEIGHT = 0.40   # fleet-percentile component

# Slope weight: how much the 7-day trend adds on top of level
SLOPE_BOOST = 0.25       # at most 25% additional penalty from trend direction

# PF load discount: if running below this fraction of own mean power,
# discount PF concern (low PF at low load is physically normal)
PF_LOAD_DISCOUNT_THRESHOLD = 0.60   # below 60% of own mean power
PF_LOAD_DISCOUNT_FACTOR    = 0.65   # discount PF penalty by 65%

# Minimum std denominators to avoid division-by-zero
MIN_STD_POWER    = 0.05
MIN_STD_PF       = 0.005
MIN_STD_UNBAL    = 0.10
MIN_STD_THD      = 0.10

# Health tier boundaries
TIER_BOUNDARIES = [
    (80, "Healthy"),
    (60, "Monitor"),
    (40, "Maintenance Soon"),
    (0,  "Critical"),
]

# ─── Math helpers ─────────────────────────────────────────────────────────────

def sigmoid(x: float) -> float:
    x = max(-500.0, min(500.0, float(x)))
    return 1.0 / (1.0 + math.exp(-x))


def sigmoid_score(raw: float) -> float:
    """
    Convert a raw penalty into [0, 1] where raw=0 → score=0.
    sigmoid(0)=0.5, so we shift: sigmoid(raw)*2 - 1, then clamp.
    This means no penalty when the metric sits exactly at baseline.
    """
    return float(np.clip(sigmoid(raw) * 2.0 - 1.0, 0.0, 1.0))


def relative_score(current: float, ahu_mean: float, ahu_std: float,
                   higher_is_worse: bool = True, sensitivity: float = 2.0) -> float:
    """
    Compute how many standard deviations the current value is from the
    AHU's own mean, then pass through sigmoid_score.

    higher_is_worse=True  : positive deviation from mean = bad (unbalance, THD)
    higher_is_worse=False : negative deviation from mean = bad (PF — lower is worse)
    sensitivity           : scales the z-score before sigmoid; higher = more sensitive
    """
    z = (current - ahu_mean) / ahu_std
    if not higher_is_worse:
        z = -z              # flip so that "below mean" = positive z = penalty
    return sigmoid_score(z * sensitivity)


def absolute_score_higher_is_worse(current: float,
                                    fleet_median: float,
                                    fleet_p95: float) -> float:
    """
    Where does this value sit in the fleet distribution?
    Score = 0 at fleet median and below.
    Score = 1 at fleet p95 and above.
    Linear interpolation between.
    """
    denom = fleet_p95 - fleet_median
    if denom <= 0:
        return 0.0
    return float(np.clip((current - fleet_median) / denom, 0.0, 1.0))


def absolute_score_lower_is_worse(current: float,
                                   fleet_median: float,
                                   fleet_p5: float) -> float:
    """
    For metrics where LOWER = worse (e.g. PF).
    Score = 0 at fleet median and above.
    Score = 1 at fleet p5 and below.
    Linear interpolation between.
    """
    denom = fleet_median - fleet_p5
    if denom <= 0:
        return 0.0
    return float(np.clip((fleet_median - current) / denom, 0.0, 1.0))


def blend(rel: float, abs_: float) -> float:
    return float(RELATIVE_WEIGHT * rel + ABSOLUTE_WEIGHT * abs_)


def ols_slope_normalized(values: np.ndarray, std: float) -> float:
    """
    OLS slope over equally-spaced points, divided by the AHU's own std.
    Returns a dimensionless drift rate. Positive = rising over the window.
    """
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    n = len(v)
    if n < 3:
        return 0.0
    i = np.arange(n, dtype=float)
    num   = n * np.dot(i, v) - i.sum() * v.sum()
    denom = n * np.dot(i, i) - i.sum() ** 2
    slope = (num / denom) if denom != 0 else 0.0
    return float(np.clip(slope / max(std, 1e-6), -5.0, 5.0))


def tier_label(index: float) -> str:
    for threshold, label in TIER_BOUNDARIES:
        if index >= threshold:
            return label
    return "Critical"


# ─── Baseline computation ─────────────────────────────────────────────────────

def compute_baselines(df: pd.DataFrame) -> tuple[dict, dict]:
    """
    Returns:
      ahu_baselines : {ahu_id: {metric: {mean, std, p5, p25, p75, p95}}}
      fleet_stats   : {metric: {p5, median, p95}}
    """
    ahu_baselines = {}

    for ahu_id, grp in df.groupby("ahu_id"):
        b = {}
        for col in ["power_total", "power_factor_avg", "current_unbalance",
                    "current_l1_thd", "current_l3_thd", "delta_kwh"]:
            vals = grp[col].dropna()
            if len(vals) < 2:
                b[col] = dict(mean=np.nan, std=1.0, p5=np.nan, p25=np.nan,
                              p75=np.nan, p95=np.nan, n=0)
                continue
            b[col] = dict(
                mean = float(vals.mean()),
                std  = float(max(vals.std(), {
                    "power_total":       MIN_STD_POWER,
                    "power_factor_avg":  MIN_STD_PF,
                    "current_unbalance": MIN_STD_UNBAL,
                    "current_l1_thd":    MIN_STD_THD,
                    "current_l3_thd":    MIN_STD_THD,
                    "delta_kwh":         MIN_STD_POWER,
                }.get(col, 0.01))),
                p5   = float(np.percentile(vals, 5)),
                p25  = float(np.percentile(vals, 25)),
                p75  = float(np.percentile(vals, 75)),
                p95  = float(np.percentile(vals, 95)),
                n    = len(vals),
            )
        ahu_baselines[ahu_id] = b

    # Composite THD baseline
    df["composite_thd"] = df[["current_l1_thd", "current_l3_thd"]].max(axis=1)
    for ahu_id, grp in df.groupby("ahu_id"):
        vals = grp["composite_thd"].dropna()
        if len(vals) < 2:
            ahu_baselines[ahu_id]["composite_thd"] = dict(
                mean=np.nan, std=MIN_STD_THD, p5=np.nan, p95=np.nan, n=0)
        else:
            ahu_baselines[ahu_id]["composite_thd"] = dict(
                mean = float(vals.mean()),
                std  = float(max(vals.std(), MIN_STD_THD)),
                p5   = float(np.percentile(vals, 5)),
                p95  = float(np.percentile(vals, 95)),
                n    = len(vals),
            )

    # Fleet-wide statistics — use actual fleet distribution, not external standards
    fleet_stats = {}
    for col, key in [
        ("current_unbalance", "unbalance"),
        ("composite_thd",     "thd"),
        ("power_factor_avg",  "pf"),
        ("delta_kwh",         "delta_kwh"),
    ]:
        vals = df[col].dropna()
        fleet_stats[key] = dict(
            p5     = float(np.percentile(vals, 5)),
            median = float(np.percentile(vals, 50)),
            p75    = float(np.percentile(vals, 75)),
            p95    = float(np.percentile(vals, 95)),
        )

    return ahu_baselines, fleet_stats


# ─── Score functions ──────────────────────────────────────────────────────────

def score_energy_anomaly(delta_kwh_current, baseline: dict,
                         fleet_stats: dict) -> float:
    """
    Score 1: Energy Anomaly  (weight 0.15)

    How unusual is this hour's energy consumption for this specific AHU?
    Purely relative — size-neutral by construction.

    z = (delta_kwh - ahu_mean_delta_kwh) / ahu_std_delta_kwh

    We care about both directions but weight overconsumption slightly higher:
        raw = 0.6 * |z|  +  0.4 * max(0, z)

    No absolute component: comparing energy consumption across differently-sized
    AHUs is not meaningful. The relative score is the right measure here.
    """
    if delta_kwh_current is None or np.isnan(delta_kwh_current) or delta_kwh_current < 0:
        return 0.0

    b = baseline.get("delta_kwh", {})
    mean = b.get("mean", np.nan)
    std  = b.get("std",  1.0)

    if np.isnan(mean):
        return 0.0

    z   = (delta_kwh_current - mean) / std
    raw = 0.6 * abs(z) + 0.4 * max(0.0, z)
    return sigmoid_score(raw)


def score_pf_degradation(pf_current, power_current, baseline: dict,
                         fleet_stats: dict) -> float:
    """
    Score 2: Power Factor Degradation  (weight 0.25)

    RELATIVE:  is PF lower than this AHU's own typical PF?
    ABSOLUTE:  is PF low relative to the fleet's actual PF distribution?
    SLOPE:     is PF trending downward? (minor additional weight)

    LOAD DISCOUNT: if the unit is running well below its own mean power
    (< 60% of own mean), discount the PF score significantly. Low PF at
    very light load is physically expected — not degradation.

    This handles AHUs like e0101 (mean PF 0.35) and e0113 (mean PF 0.42)
    fairly: they're not penalized every hour for their inherent operating
    characteristics. They're penalized when their PF gets worse than usual.
    """
    if pf_current is None or np.isnan(pf_current):
        return 0.0

    b_pf    = baseline.get("power_factor_avg", {})
    b_pwr   = baseline.get("power_total", {})
    pf_mean = b_pf.get("mean", np.nan)
    pf_std  = b_pf.get("std",  MIN_STD_PF)

    if np.isnan(pf_mean):
        return 0.0

    # Relative: how many SDs below own mean? (lower PF = worse)
    rel = relative_score(pf_current, pf_mean, pf_std,
                         higher_is_worse=False, sensitivity=2.5)

    # Absolute: fleet-calibrated (uses actual fleet p5 and median)
    abs_ = absolute_score_lower_is_worse(
        pf_current,
        fleet_median = fleet_stats["pf"]["median"],
        fleet_p5     = fleet_stats["pf"]["p5"],
    )

    score = blend(rel, abs_)

    # Load discount
    pwr_mean = b_pwr.get("mean", np.nan)
    if (not np.isnan(power_current) and not np.isnan(pwr_mean)
            and pwr_mean > 0
            and power_current < PF_LOAD_DISCOUNT_THRESHOLD * pwr_mean):
        score *= (1.0 - PF_LOAD_DISCOUNT_FACTOR)

    return float(np.clip(score, 0.0, 1.0))


def score_phase_imbalance(unbal_current, baseline: dict,
                          fleet_stats: dict) -> float:
    """
    Score 3: Phase Imbalance  (weight 0.25)

    RELATIVE:  how much above this AHU's own typical unbalance?
    ABSOLUTE:  where does this sit in the fleet's unbalance distribution?

    This is the component most distorted by fixed thresholds.
    With fleet median unbalance at ~5.6% and many AHUs running at
    20-80%, NEMA 5% is meaningless. This scoring uses actual fleet
    percentiles as the reference.

    e0120 (mean 78% unbalance): absolute score is HIGH (it's at the top
    of the fleet distribution) but relative score stays LOW when stable.
    Final score: moderate. Reflects: known chronic issue, but stable.

    If e0120 then spikes to 95%: both scores HIGH → alarm correctly.
    """
    if unbal_current is None or np.isnan(unbal_current):
        return 0.0

    b    = baseline.get("current_unbalance", {})
    mean = b.get("mean", np.nan)
    std  = b.get("std",  MIN_STD_UNBAL)

    if np.isnan(mean):
        return 0.0

    rel  = relative_score(unbal_current, mean, std,
                          higher_is_worse=True, sensitivity=2.0)
    abs_ = absolute_score_higher_is_worse(
        unbal_current,
        fleet_median = fleet_stats["unbalance"]["median"],
        fleet_p95    = fleet_stats["unbalance"]["p95"],
    )

    return float(np.clip(blend(rel, abs_), 0.0, 1.0))


def score_thd_drift(thd_24h_mean, baseline: dict,
                    fleet_stats: dict, has_thd_data: bool) -> float:
    """
    Score 4: THD Drift  (weight 0.15)

    Uses 24h rolling mean of composite THD (max of L1 and L3) to filter
    transient spikes.

    RELATIVE:  how much above this AHU's own typical THD level?
    ABSOLUTE:  where does this sit in the fleet's THD distribution?

    Special case: e0112 has no L1 or L3 THD data. Score returns 0.0
    and the data_quality_flag is set by the caller.

    Special case: e0111 has L1 THD averaging 52%. Both its relative
    and absolute scores will be elevated — which is correct, because
    52% THD is a genuine electrical anomaly regardless of what its
    own baseline says.
    """
    if not has_thd_data or thd_24h_mean is None or np.isnan(thd_24h_mean):
        return 0.0

    b    = baseline.get("composite_thd", {})
    mean = b.get("mean", np.nan)
    std  = b.get("std",  MIN_STD_THD)

    if np.isnan(mean):
        return 0.0

    rel  = relative_score(thd_24h_mean, mean, std,
                          higher_is_worse=True, sensitivity=2.0)
    abs_ = absolute_score_higher_is_worse(
        thd_24h_mean,
        fleet_median = fleet_stats["thd"]["median"],
        fleet_p95    = fleet_stats["thd"]["p95"],
    )

    return float(np.clip(blend(rel, abs_), 0.0, 1.0))


def score_overload(power_current, baseline: dict,
                   fleet_stats: dict) -> float:
    """
    Score 5: Overload  (weight 0.20)

    Is this AHU approaching or exceeding its own historical ceiling?

    Uses each AHU's OWN p95 as the ceiling reference — not a fleet-wide
    value. This is size-neutral by construction:
      - e0105 (35 kW mean) uses its own p95 as the ceiling
      - e0101 (0.67 kW mean) uses its own p95 as the ceiling

    power_ratio = current_power / ahu_p95_power

    Score starts accumulating above 85% of the AHU's own p95.

    ABSOLUTE component: where does current power sit relative to fleet?
    This catches cases where an AHU is running unusually hard even if
    it hasn't broken its own personal ceiling yet.
    """
    if power_current is None or np.isnan(power_current):
        return 0.0

    b       = baseline.get("power_total", {})
    p95_pwr = b.get("p95", np.nan)
    pwr_mean = b.get("mean", np.nan)
    pwr_std  = b.get("std", MIN_STD_POWER)

    if np.isnan(p95_pwr) or p95_pwr <= 0:
        return 0.0

    # Relative: how far above own p95 ceiling?
    power_ratio = power_current / p95_pwr
    demand_term = max(0.0, power_ratio - 0.85)
    rel = sigmoid_score(demand_term * 8.0)

    # Also include z-score of current power vs own mean
    # (catches unusual load even if ceiling not reached)
    if not np.isnan(pwr_mean):
        z_pwr = (power_current - pwr_mean) / pwr_std
        rel   = float(np.clip(0.7 * rel + 0.3 * sigmoid_score(z_pwr * 1.5), 0.0, 1.0))

    # Absolute: fleet context
    # Use delta_kwh fleet stats to give absolute reference
    abs_ = absolute_score_higher_is_worse(
        power_current,
        fleet_median = fleet_stats["delta_kwh"]["median"],
        fleet_p95    = fleet_stats["delta_kwh"]["p95"],
    )

    return float(np.clip(blend(rel, abs_), 0.0, 1.0))


def compute_health_index(scores: dict) -> float:
    """
    health_index = 100 - (weighted_penalty × 100)
    Clamped to [0, 100].
    """
    penalty = sum(WEIGHTS[k] * scores[k] for k in WEIGHTS)
    return round(float(np.clip(100.0 - penalty * 100.0, 0.0, 100.0)), 1)


# ─── Main pipeline ────────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    df = pd.read_csv(INPUT_CSV)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values(["ahu_id", "timestamp"]).reset_index(drop=True)

    print(f"  {len(df)} rows, {df['ahu_id'].nunique()} AHUs, "
          f"{df['timestamp'].nunique()} timestamps")

    # ── Compute delta_kwh (energy consumed each hour) ──────────────────────
    # Since intervals are exactly 1 hour, delta_kwh ≈ power_total
    # but we compute from energy_import to stay accurate
    df["delta_kwh"] = df.groupby("ahu_id")["energy_import"].diff()

    # Invalidate negative deltas (meter resets or data errors)
    n_resets = (df["delta_kwh"] < 0).sum()
    if n_resets > 0:
        print(f"  Nulling {n_resets} negative delta_kwh values (meter resets)")
        df.loc[df["delta_kwh"] < 0, "delta_kwh"] = np.nan

    # ── Composite THD ──────────────────────────────────────────────────────
    # L2 THD is absent fleet-wide. Use max of L1 and L3.
    df["composite_thd"] = df[["current_l1_thd", "current_l3_thd"]].max(axis=1)

    # Flag AHUs with no THD data at all
    thd_available = df.groupby("ahu_id")["composite_thd"].apply(
        lambda x: x.notna().any()
    ).to_dict()

    # ── 24h rolling mean THD per AHU ──────────────────────────────────────
    df["thd_24h_mean"] = (
        df.groupby("ahu_id")["composite_thd"]
          .transform(lambda x: x.rolling(24, min_periods=1).mean())
    )

    # ── Compute baselines ──────────────────────────────────────────────────
    print("Computing per-AHU baselines and fleet statistics...")
    ahu_baselines, fleet_stats = compute_baselines(df.copy())

    print("\n  Fleet statistics used for absolute scoring:")
    print(f"    Unbalance  — median: {fleet_stats['unbalance']['median']:.1f}%  "
          f"p95: {fleet_stats['unbalance']['p95']:.1f}%")
    print(f"    THD        — median: {fleet_stats['thd']['median']:.1f}%  "
          f"p95: {fleet_stats['thd']['p95']:.1f}%")
    print(f"    PF         — p5: {fleet_stats['pf']['p5']:.3f}  "
          f"median: {fleet_stats['pf']['median']:.3f}")
    print(f"    delta_kWh  — median: {fleet_stats['delta_kwh']['median']:.2f}  "
          f"p95: {fleet_stats['delta_kwh']['p95']:.2f}")

    # ── Score each row ─────────────────────────────────────────────────────
    print("\nScoring all rows...")
    results = []

    for _, row in df.iterrows():
        ahu_id    = row["ahu_id"]
        baseline  = ahu_baselines[ahu_id]
        has_thd   = thd_available.get(ahu_id, False)
        dq_flag   = 0

        pf_current    = row["power_factor_avg"]   if not pd.isna(row["power_factor_avg"])   else None
        unbal_current = row["current_unbalance"]  if not pd.isna(row["current_unbalance"])  else None
        power_current = row["power_total"]        if not pd.isna(row["power_total"])         else None
        delta_kwh     = row["delta_kwh"]          if not pd.isna(row["delta_kwh"])           else None
        thd_mean      = row["thd_24h_mean"]       if not pd.isna(row["thd_24h_mean"])        else None

        if not has_thd:
            dq_flag = 1

        s_energy  = score_energy_anomaly(delta_kwh, baseline, fleet_stats)
        s_pf      = score_pf_degradation(pf_current, power_current if power_current else 0.0,
                                         baseline, fleet_stats)
        s_imbal   = score_phase_imbalance(unbal_current, baseline, fleet_stats)
        s_thd     = score_thd_drift(thd_mean, baseline, fleet_stats, has_thd)
        s_overload= score_overload(power_current, baseline, fleet_stats)

        scores = {
            "energy_anomaly":  s_energy,
            "pf_degradation":  s_pf,
            "phase_imbalance": s_imbal,
            "thd_drift":       s_thd,
            "overload":        s_overload,
        }

        health_index = compute_health_index(scores)

        results.append({
            "timestamp":         row["timestamp"].isoformat(),
            "ahu_id":            ahu_id,
            "level":             LEVEL_NAME,
            "health_index":      health_index,
            "energy_anomaly":    round(s_energy,   4),
            "pf_degradation":    round(s_pf,        4),
            "phase_imbalance":   round(s_imbal,     4),
            "thd_drift":         round(s_thd,       4),
            "overload":          round(s_overload,  4),
            # Diagnostic columns (useful for debugging and dashboard)
            "power_total":       round(float(power_current), 4) if power_current is not None else None,
            "power_factor":      round(float(pf_current),    4) if pf_current    is not None else None,
            "unbalance_pct":     round(float(unbal_current), 3) if unbal_current is not None else None,
            "thd_composite":     round(float(thd_mean),      3) if thd_mean      is not None else None,
            "delta_kwh":         round(float(delta_kwh),     3) if delta_kwh     is not None else None,
            "data_quality_flag": dq_flag,
            "tier":              tier_label(health_index),
        })

    out = pd.DataFrame(results)
    out.to_csv(OUTPUT_CSV, index=False)
    print(f"\nWrote {len(out)} rows to {OUTPUT_CSV}")

    # ── Summary report ─────────────────────────────────────────────────────
    print("\n" + "═" * 70)
    print("HEALTH INDEX SUMMARY (mean / min / max across all hours)")
    print("═" * 70)
    print(f"{'AHU':<8} {'Mean':>6} {'Min':>6} {'Max':>6}  "
          f"{'Tier':>16}  {'Energy':>7} {'PF':>7} {'Imbal':>7} {'THD':>7} {'Ovld':>7}")
    print("─" * 70)

    for ahu_id, grp in out.groupby("ahu_id"):
        mean_idx = grp["health_index"].mean()
        min_idx  = grp["health_index"].min()
        max_idx  = grp["health_index"].max()
        tier     = tier_label(mean_idx)
        e = grp["energy_anomaly"].mean()
        p = grp["pf_degradation"].mean()
        i = grp["phase_imbalance"].mean()
        t = grp["thd_drift"].mean()
        o = grp["overload"].mean()
        print(f"{ahu_id:<8} {mean_idx:>6.1f} {min_idx:>6.1f} {max_idx:>6.1f}  "
              f"{tier:>16}  {e:>7.3f} {p:>7.3f} {i:>7.3f} {t:>7.3f} {o:>7.3f}")

    print("\n" + "═" * 70)
    print("FAIRNESS CHECK: score standard deviations across hours per AHU")
    print("(Higher std = index is responding to changes, not stuck)")
    print("─" * 70)
    for ahu_id, grp in out.groupby("ahu_id"):
        std_idx = grp["health_index"].std()
        print(f"  {ahu_id}: index std = {std_idx:.2f}  "
              f"(range {grp['health_index'].min():.1f} – {grp['health_index'].max():.1f})")


if __name__ == "__main__":
    main()