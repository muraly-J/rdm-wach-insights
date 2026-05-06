"""Recompute FAIR-style scores from raw InfluxDB data and diff against stored values.

Run: cd backend && python -m scripts.research.recompute_scores
Output: data/research/2026-05-06/recompute_diffs.csv + per-AHU plots.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from backend.core import db_reader
from backend.core.healthdb import HealthDB
from backend.core.fair_health_scoring import (
    build_baselines,
    calculate_health_index,
    score_energy_anomaly,
    score_overload,
    score_phase_imbalance,
    score_power_factor,
    score_thd_drift,
)

REF_PATH = Path("data/research/2026-05-06/reference_ahus.json")
OUT_DIR = Path("data/research/2026-05-06")
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOOKBACK = "7d"


def load_reference() -> dict:
    return json.loads(REF_PATH.read_text())


def fetch_raw_for_ahu(ahu_id: str) -> pd.DataFrame:
    """
    Pull the 7d health_hourly rows from DuckDB for one AHU.
    Returns a DataFrame suitable for build_baselines() input.
    """
    db = HealthDB()
    latest_ts = db.get_latest_timestamp()
    if latest_ts is None:
        return pd.DataFrame()

    from datetime import timedelta
    start = (latest_ts - timedelta(days=7)).isoformat()

    df = db.get_time_range(
        ahu_ids=[ahu_id],
        start=start,
        end=latest_ts.isoformat(),
        limit=None,
    )
    if df.empty:
        return pd.DataFrame()

    # Rename columns to match build_baselines expectations
    # build_baselines expects: device_id, timestamp, delta_kwh, power_factor_avg,
    #   current_unbalance, composite_thd, power_total
    rename_map = {
        "ahu_id": "device_id",
        "timestamp": "timestamp",
        "raw_power_total": "power_total",
        "raw_power_factor_avg": "power_factor_avg",
        "raw_current_unbalance": "current_unbalance",
        "raw_composite_thd": "composite_thd",
    }

    # Use delta_kwh from the prediction ETL if available
    # Otherwise compute from energy_import diffs
    if "raw_hourly_delta" in df.columns:
        rename_map["raw_hourly_delta"] = "delta_kwh"
    elif "raw_energy_import" in df.columns:
        df = df.sort_values("timestamp")
        df["delta_kwh"] = df["raw_energy_import"].diff()
        rename_map["delta_kwh"] = "delta_kwh"
    else:
        df["delta_kwh"] = np.nan
        rename_map["delta_kwh"] = "delta_kwh"

    df = df.rename(columns=rename_map)
    needed = ["device_id", "timestamp", "delta_kwh", "power_factor_avg",
              "current_unbalance", "composite_thd", "power_total"]
    df = df[[c for c in needed if c in df.columns]]
    return df


def recompute_for(ahu_id: str) -> pd.DataFrame:
    """Recompute all 5 FAIR scores + health_index for each timestamp row."""
    raw = fetch_raw_for_ahu(ahu_id)
    if raw.empty:
        return pd.DataFrame()

    # Build baselines from the full 7d history
    baselines = build_baselines(raw)
    base = baselines.get(ahu_id, {})

    rows = []
    for _, r in raw.iterrows():
        # Get baseline stats for each metric
        dk = base.get("delta_kwh", {})
        pf = base.get("power_factor_avg", {})
        ub = base.get("current_unbalance", {})
        th = base.get("composite_thd_24h", {})
        pw = base.get("power_total", {})

        # Build per-row history slices (use the full 7d series for trend)
        hist_delta = raw["delta_kwh"].dropna().to_numpy() if "delta_kwh" in raw else np.array([])
        hist_pf = raw["power_factor_avg"].dropna().to_numpy() if "power_factor_avg" in raw else np.array([])
        hist_ub = raw["current_unbalance"].dropna().to_numpy() if "current_unbalance" in raw else np.array([])
        hist_thd = raw["composite_thd"].dropna().to_numpy() if "composite_thd" in raw else np.array([])
        hist_pw = raw["power_total"].dropna().to_numpy() if "power_total" in raw else np.array([])

        energy_s, _ = score_energy_anomaly(
            r.get("delta_kwh"),
            dk.get("median", np.nan),
            dk.get("rstd", np.nan),
            hist_delta,
        )
        pf_s, _ = score_power_factor(
            r.get("power_factor_avg"),
            r.get("power_total"),
            pf.get("median", np.nan),
            pf.get("rstd", np.nan),
            hist_pf,
        )
        unbal_s, _ = score_phase_imbalance(
            r.get("current_unbalance"),
            ub.get("median", np.nan),
            ub.get("rstd", np.nan),
            hist_ub,
        )
        thd_s, _ = score_thd_drift(
            r.get("composite_thd"),
            th.get("median", np.nan),
            th.get("rstd", np.nan),
            hist_thd,
        )
        ovl_s, _ = score_overload(
            r.get("power_total"),
            pw.get("median", np.nan),
            pw.get("rstd", np.nan),
            pw.get("p95", np.nan),
            hist_pw,
        )
        scores = {
            "energy_anomaly": energy_s,
            "power_factor": pf_s,
            "phase_imbalance": unbal_s,
            "thd_drift": thd_s,
            "overload": ovl_s,
        }
        idx = calculate_health_index(scores)
        rows.append({
            "timestamp": r["timestamp"],
            "ahu_id": ahu_id,
            "energy_anomaly": energy_s,
            "pf_degradation": pf_s,
            "phase_imbalance": unbal_s,
            "thd_drift": thd_s,
            "overload": ovl_s,
            "health_index_recomputed": idx,
        })

    return pd.DataFrame(rows)


def fetch_stored(ahu_id: str) -> pd.DataFrame:
    """Pull stored health_index series from healthdb for the same AHU + window."""
    db = HealthDB()
    latest_ts = db.get_latest_timestamp()
    if latest_ts is None:
        return pd.DataFrame()

    from datetime import timedelta
    start = (latest_ts - timedelta(days=7)).isoformat()

    df = db.get_time_range(
        ahu_ids=[ahu_id],
        start=start,
        end=latest_ts.isoformat(),
        metrics=["timestamp", "health_index"],
        limit=None,
    )
    if df.empty or "health_index" not in df.columns:
        return pd.DataFrame()

    return df.rename(columns={"timestamp": "timestamp", "health_index": "health_index_stored"})[["timestamp", "health_index_stored"]]


def main() -> int:
    ref = load_reference()
    all_diffs = []

    for label, info in ref.items():
        ahu = info["ahu_id"]
        recomputed = recompute_for(ahu)
        stored = fetch_stored(ahu)

        if recomputed.empty:
            print(f"[{label}] {ahu}: no raw data; skipping")
            continue

        merged = recomputed.merge(stored, on="timestamp", how="outer")
        merged["label"] = label
        merged["diff"] = merged["health_index_recomputed"] - merged["health_index_stored"]
        all_diffs.append(merged)

    if not all_diffs:
        print("No data to write.")
        return 1

    df = pd.concat(all_diffs, ignore_index=True)
    out = OUT_DIR / "recompute_diffs.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {out} ({len(df)} rows)")
    print(df.groupby("label")["diff"].describe())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())