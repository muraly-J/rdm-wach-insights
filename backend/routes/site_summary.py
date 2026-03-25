"""
site_summary.py
───────────────
GET /api/site/summary?range=7d

Returns a SiteSummaryData payload used by the frontend dashboard hero panel.
Aggregates fleet-wide health, financial impact, level tiles, and trend deltas
from real CSV data — no mock data.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

log = logging.getLogger(__name__)

router = APIRouter(tags=["Site Summary"])

RANGE_MAP = {
    "24h": "last_24h",
    "7d": "last_7d",
    "30d": "last_30d",
}


def device_id_to_name(device_id: str) -> str:
    """Convert e.g. 'e0306' -> 'AHU-L3-06'."""
    level_num = int(device_id[1:3])
    unit_num = int(device_id[3:])
    return f"AHU-L{level_num}-{unit_num:02d}"


def _build_spotlight(assessment: dict, cost_lookup: dict) -> dict:
    """Build starAHU / criticalAHU spotlight dict from an assessment."""
    from models.schemas import get_level_from_ahu_id

    device_id = assessment["device_id"]
    level = get_level_from_ahu_id(device_id) or 0
    return {
        "id": device_id,
        "name": device_id_to_name(device_id),
        "level": level,
        "healthScore": round(float(assessment["health_index"]), 1),
        "monthlyCostMYR": round(cost_lookup.get(device_id, 0.0), 2),
        "safetyFlags": len(assessment.get("safety_flags", [])),
    }


@router.get("/site/summary")
async def get_site_summary(range: str = Query(default="7d", alias="range")):
    """
    Return a site-wide summary for the dashboard hero panel.

    Query params:
      range: "24h" | "7d" (default) | "30d"
    """
    # Avoid shadowing Python's built-in range() — rename param for use below
    time_range_param = range
    try:
        internal_range = RANGE_MAP.get(time_range_param, "last_7d")

        # ── Step 1: Fleet health assessment ──────────────────────────────────
        from core.risk_engine import generate_fleet_risk_assessment
        from models.schemas import get_level_from_ahu_id, ALLOWED_DEVICES

        fleet = generate_fleet_risk_assessment(
            time_range=internal_range,
            cluster_by_level=True,
            devices_filter=list(ALLOWED_DEVICES),
        )
        assessments = fleet.get("assessments", [])

        if not assessments:
            raise HTTPException(status_code=503, detail="No assessment data available")

        # ── Step 2: Aggregate health metrics ─────────────────────────────────
        total_ahus = len(assessments)
        avg_site_health = round(
            sum(a["health_index"] for a in assessments) / total_ahus, 1
        )
        ahus_in_alert = sum(
            1 for a in assessments if len(a.get("safety_flags", [])) > 0
        )

        # ── Step 3: Per-level summary ─────────────────────────────────────────
        level_tiles = []
        for level_num in range(1, 12):
            level_assessments = [
                a for a in assessments
                if get_level_from_ahu_id(a["device_id"]) == level_num
            ]
            if not level_assessments:
                continue
            avg_h = round(
                sum(a["health_index"] for a in level_assessments) / len(level_assessments),
                1,
            )
            level_tiles.append({
                "level": level_num,
                "avgHealth": avg_h,
                "ahuCount": len(level_assessments),
            })

        # ── Step 4: Financial data ────────────────────────────────────────────
        from routes.financial_impact import _compute_impact

        grand_total = 0.0
        all_top_ahus: list = []

        for level_num in range(1, 12):
            try:
                impact = _compute_impact(level=level_num, time_range=time_range_param)
                grand_total += impact.get("grand_total", 0.0)
                all_top_ahus.extend(impact.get("top_ahus", []))
            except Exception as exc:
                log.debug("Skipping level %d financial data: %s", level_num, exc)

        est_monthly_cost = round(grand_total, 2)

        # Build device_id -> total_cost lookup from financial top_ahus
        cost_lookup: dict = {
            row["device_id"]: row.get("total_cost", 0.0)
            for row in all_top_ahus
        }

        # ── Step 5 & 6: Star + critical AHU spotlights ───────────────────────
        star_assessment = max(assessments, key=lambda a: a["health_index"])
        critical_assessment = min(assessments, key=lambda a: a["health_index"])

        star_ahu = _build_spotlight(star_assessment, cost_lookup)
        critical_ahu = _build_spotlight(critical_assessment, cost_lookup)

        # ── Step 7: Trend deltas ──────────────────────────────────────────────
        from core.csv_reader import _load_csv, _filter_time_range

        df_full = _load_csv(time_range=time_range_param)
        trend_deltas = []

        if not df_full.empty:
            df_full = _filter_time_range(df_full, time_range_param)
            df_full = df_full.sort_values("timestamp")

            mid_ts = df_full["timestamp"].quantile(0.5)
            df_first = df_full[df_full["timestamp"] <= mid_ts]
            df_second = df_full[df_full["timestamp"] > mid_ts]

            # Health delta
            h1 = float(df_first["health_index"].mean()) if len(df_first) > 0 else 0.0
            h2 = float(df_second["health_index"].mean()) if len(df_second) > 0 else 0.0
            health_delta = round(h2 - h1, 1)

            # Energy delta (percentage change of raw_energy_import mean)
            energy_col = "raw_energy_import"
            if energy_col in df_full.columns:
                e1 = float(df_first[energy_col].mean()) if len(df_first) > 0 else 0.0
                e2 = float(df_second[energy_col].mean()) if len(df_second) > 0 else 0.0
                energy_pct = round(((e2 - e1) / e1 * 100) if e1 > 0 else 0.0, 1)
            else:
                energy_pct = 0.0

            # Alerts delta (critical-tier count change between halves)
            crit1 = int((df_first["health_index"] < 40).sum()) if len(df_first) > 0 else 0
            crit2 = int((df_second["health_index"] < 40).sum()) if len(df_second) > 0 else 0
            alerts_delta = crit2 - crit1

            trend_deltas = [
                {
                    "label": "Energy",
                    "value": energy_pct,
                    "unit": "%",
                    "direction": "down" if energy_pct <= 0 else "up",
                },
                {
                    "label": "Health",
                    "value": health_delta,
                    "unit": "pts",
                    "direction": "up" if health_delta >= 0 else "down",
                },
                {
                    "label": "Cost",
                    "value": round(grand_total * (energy_pct / 100), 2) if energy_pct != 0 else 0.0,
                    "unit": "MYR",
                    "direction": "down" if energy_pct <= 0 else "up",
                },
                {
                    "label": "Alerts",
                    "value": float(alerts_delta),
                    "unit": "",
                    "direction": "down" if alerts_delta <= 0 else "up",
                },
            ]
        else:
            log.warning("site/summary: CSV data empty, trend deltas will be zeros")
            trend_deltas = [
                {"label": "Energy", "value": 0.0, "unit": "%", "direction": "down"},
                {"label": "Health", "value": 0.0, "unit": "pts", "direction": "up"},
                {"label": "Cost", "value": 0.0, "unit": "MYR", "direction": "down"},
                {"label": "Alerts", "value": 0.0, "unit": "", "direction": "down"},
            ]

        # ── Assemble final response ───────────────────────────────────────────
        return {
            "totalAHUs": total_ahus,
            "avgSiteHealth": avg_site_health,
            "ahusInAlert": ahus_in_alert,
            "estMonthlyCostMYR": est_monthly_cost,
            "starAHU": star_ahu,
            "criticalAHU": critical_ahu,
            "levelTiles": level_tiles,
            "trendDeltas": trend_deltas,
        }

    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Unexpected error in /api/site/summary: %s", exc)
        raise HTTPException(status_code=500, detail="Site summary computation failed")
