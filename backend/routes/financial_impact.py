from __future__ import annotations
"""
financial_impact.py
───────────────────
GET  /api/financial-config         — Load saved financial parameters
POST /api/financial-config         — Save financial parameters
GET  /api/financial-impact?level=N&range=30d  — Compute cost breakdown

All calculations use DuckDB health data — no new ETL required.
"""
import json
import logging
import os

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)
router = APIRouter()

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'data', 'financial_config.json'
)

DEFAULT_CONFIG = {
    "currency":                  "RM",
    "tariff_rate":               0.365,   # RM/kWh — TNB C1 default
    "max_demand_rate":           30.30,   # RM/kVA/month — TNB C1 default
    "planned_maintenance_cost":  500.0,   # RM per visit
    "emergency_multiplier":      3.0,     # emergency = 3× planned
}


class FinancialConfig(BaseModel):
    currency:                  str   = Field(default="RM")
    tariff_rate:               float = Field(default=0.365,  gt=0)
    max_demand_rate:           float = Field(default=30.30,  gt=0)
    planned_maintenance_cost:  float = Field(default=500.0,  gt=0)
    emergency_multiplier:      float = Field(default=3.0,    gt=1)


def _load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                stored = json.load(f)
            # Merge with defaults so new fields always present
            return {**DEFAULT_CONFIG, **stored}
        except Exception:
            log.warning("Failed to load financial config from %s, using defaults", CONFIG_PATH, exc_info=True)
    return DEFAULT_CONFIG.copy()


def _save_config(cfg: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)


@router.get("/financial-config")
def get_financial_config():
    return _load_config()


@router.post("/financial-config")
def post_financial_config(config: FinancialConfig):
    cfg = config.model_dump()
    _save_config(cfg)
    return cfg


@router.get("/financial-impact")
async def get_financial_impact(
    level: int = Query(..., ge=1, le=20),
    time_range: str = Query(default="30d"),
    device_id: Optional[str] = Query(default=None),
):
    try:
        result = _compute_impact(level, time_range, device_id)
    except Exception as exc:
        log.error("financial-impact level=%s device=%s: %s", level, device_id, exc, exc_info=True)
        raise HTTPException(status_code=503, detail="Financial impact calculation failed")
    return result


# ── Calculation helpers ────────────────────────────────────────────────────────

def _compute_impact(level: int, time_range: str, device_id: Optional[str] = None) -> dict:
    from core.db_reader import get_dataframe

    cfg = _load_config()
    tariff           = cfg["tariff_rate"]
    max_demand_rate  = cfg.get("max_demand_rate", 0.0)
    planned_cost     = cfg["planned_maintenance_cost"]
    multiplier    = cfg["emergency_multiplier"]
    currency      = cfg["currency"]

    df = get_dataframe(level=level, time_range=time_range)
    if df.empty:
        return _empty_response(currency, level, time_range)
    df = df.sort_values('timestamp')

    if device_id:
        df = df[df['ahu_id'] == device_id]
        if df.empty:
            return _empty_response(currency, level, time_range)

    ahu_rows = []
    for ahu_id, grp in df.groupby('ahu_id'):
        grp = grp.sort_values('timestamp')

        # 1. Excess energy cost
        excess_cost = 0.0
        if 'raw_hourly_delta' in grp.columns and 'raw_predicted_delta' in grp.columns:
            excess_kwh = float((grp['raw_hourly_delta'].fillna(0) - grp['raw_predicted_delta'].fillna(0)).clip(lower=0).sum())
            excess_cost = round(excess_kwh * tariff, 2)

        # 2. PF penalty cost (TNB formula)
        pf_penalty = 0.0
        if 'raw_power_factor_avg' in grp.columns and 'raw_hourly_delta' in grp.columns:
            avg_pf = float(grp['raw_power_factor_avg'].dropna().mean())
            if pd.notna(avg_pf) and avg_pf < 0.85:
                steps_below    = (0.85 - avg_pf) / 0.01
                surcharge_frac = steps_below * 0.015
                surcharge_frac = min(surcharge_frac, 0.30)  # cap at 30%
                total_energy   = float(grp['raw_hourly_delta'].fillna(0).sum())
                pf_penalty     = round(total_energy * tariff * surcharge_frac, 2)

        # 3. Maintenance risk (latest health index for this AHU)
        latest_hi = float(grp['health_index'].dropna().iloc[-1]) if 'health_index' in grp.columns and not grp['health_index'].dropna().empty else 100.0
        maintenance_risk = round(planned_cost * (multiplier - 1), 2) if latest_hi < 60 else 0.0

        # 4. kVA demand charge (TNB: max_demand_rate RM/kVA/month × peak kVA in period)
        demand_charge = 0.0
        if max_demand_rate > 0 and 'raw_apparent_power_total' in grp.columns:
            peak_kva = float(grp['raw_apparent_power_total'].dropna().max() or 0.0)
            demand_charge = round(peak_kva * max_demand_rate, 2)

        total = round(excess_cost + pf_penalty + maintenance_risk + demand_charge, 2)

        ahu_rows.append({
            "ahu_id":             str(ahu_id),
            "health_index":       round(float(latest_hi), 1),
            "excess_energy_cost": float(excess_cost),
            "pf_penalty_cost":    float(pf_penalty),
            "maintenance_risk":   float(maintenance_risk),
            "demand_charge_myr":  float(demand_charge),
            "total_cost":         float(total),
        })

    ahu_rows.sort(key=lambda r: r["total_cost"], reverse=True)

    total_excess      = round(sum(r["excess_energy_cost"] for r in ahu_rows), 2)
    total_pf          = round(sum(r["pf_penalty_cost"]    for r in ahu_rows), 2)
    total_maintenance = round(sum(r["maintenance_risk"]   for r in ahu_rows), 2)
    total_demand      = round(sum(r["demand_charge_myr"]  for r in ahu_rows), 2)
    grand_total       = round(total_excess + total_pf + total_maintenance + total_demand, 2)

    return {
        "currency":           currency,
        "level":              level,
        "range":              time_range,
        "grand_total":        grand_total,
        "excess_energy_cost": total_excess,
        "pf_penalty_cost":    total_pf,
        "maintenance_risk":   total_maintenance,
        "demand_charge_myr":  total_demand,
        "top_ahus":           ahu_rows[:10],
    }


def _empty_response(currency: str, level: int = 0, time_range: str = "") -> dict:
    return {
        "currency": currency, "level": level, "range": time_range,
        "grand_total": 0, "excess_energy_cost": 0,
        "pf_penalty_cost": 0, "maintenance_risk": 0,
        "demand_charge_myr": 0,
        "top_ahus": [],
    }
