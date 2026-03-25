"""
site_summary.py
───────────────
GET /api/site/summary?range=7d

Returns a SiteSummaryData payload used by the frontend dashboard.
Computes all metrics from CSV data (fast, no InfluxDB per-device calls).
"""
import logging
from fastapi import APIRouter, HTTPException, Query

log = logging.getLogger(__name__)

router = APIRouter(tags=["Site Summary"])


def device_id_to_name(device_id: str) -> str:
    """Convert e.g. 'e0306' -> 'AHU-L3-06'."""
    try:
        level_num = int(device_id[1:3])
        unit_num = int(device_id[3:])
        return f"AHU-L{level_num}-{unit_num:02d}"
    except (ValueError, IndexError):
        return device_id.upper()


@router.get("/site/summary")
async def get_site_summary(range: str = Query(default="7d", alias="range")):
    """
    Return a site-wide summary for the dashboard.
    Uses CSV data for all health metrics (fast, no InfluxDB calls).

    Query params:
      range: "24h" | "7d" (default) | "30d"
    """
    # Rename to avoid shadowing Python's built-in range()
    time_range_param = range
    try:
        from core.csv_reader import _load_csv, _filter_time_range

        df = _load_csv(time_range=time_range_param)
        if df.empty:
            raise HTTPException(status_code=503, detail="No data available")

        df = _filter_time_range(df, time_range_param)
        df = df.sort_values("timestamp")

        # Latest snapshot per AHU (most recent row per device)
        latest = df.groupby("ahu_id").last().reset_index()

        if latest.empty:
            raise HTTPException(status_code=503, detail="No assessment data available")

        # ── Aggregate health metrics ──────────────────────────────────────────
        total_ahus = len(latest)
        avg_site_health = round(float(latest["health_index"].mean()), 1)
        alert_tiers = {"Maintenance Soon", "Critical"}
        ahus_in_alert = int(latest["tier"].isin(alert_tiers).sum())

        # ── Per-level tiles ───────────────────────────────────────────────────
        level_tiles = []
        for lvl_str, grp in latest.groupby("level"):
            try:
                lvl_num = int(str(lvl_str).replace("Level ", ""))
            except (ValueError, AttributeError):
                continue
            avg_h = round(float(grp["health_index"].mean()), 1)
            level_tiles.append({
                "level": lvl_num,
                "avgHealth": avg_h,
                "ahuCount": len(grp),
            })
        level_tiles.sort(key=lambda x: x["level"])

        # ── Spotlight AHUs ────────────────────────────────────────────────────
        def make_spotlight(row, monthly_cost: float = 0.0) -> dict:
            ahu_id = str(row["ahu_id"])
            try:
                level_num = int(str(row["level"]).replace("Level ", ""))
            except (ValueError, AttributeError):
                level_num = 0
            return {
                "id": ahu_id,
                "name": device_id_to_name(ahu_id),
                "level": level_num,
                "healthScore": round(float(row["health_index"]), 1),
                "monthlyCostMYR": round(monthly_cost, 2),
                "safetyFlags": 0,
            }

        star_row = latest.loc[latest["health_index"].idxmax()]
        critical_row = latest.loc[latest["health_index"].idxmin()]
        star_ahu = make_spotlight(star_row)
        critical_ahu = make_spotlight(critical_row)

        # ── Financial data (not computed in summary — use /financial-impact per level) ──
        grand_total = 0.0
        est_monthly_cost = 0.0

        # ── Trend deltas (split period in half) ───────────────────────────────
        mid_ts = df["timestamp"].quantile(0.5)
        df_first = df[df["timestamp"] <= mid_ts]
        df_second = df[df["timestamp"] > mid_ts]

        h1 = float(df_first["health_index"].mean()) if len(df_first) > 0 else 0.0
        h2 = float(df_second["health_index"].mean()) if len(df_second) > 0 else 0.0
        health_delta = round(h2 - h1, 1)

        energy_col = "raw_energy_import"
        if energy_col in df.columns:
            e1 = float(df_first[energy_col].mean()) if len(df_first) > 0 else 0.0
            e2 = float(df_second[energy_col].mean()) if len(df_second) > 0 else 0.0
            energy_pct = round(((e2 - e1) / e1 * 100) if e1 > 0 else 0.0, 1)
        else:
            energy_pct = 0.0

        crit1 = int(df_first["tier"].isin(alert_tiers).sum()) if len(df_first) > 0 else 0
        crit2 = int(df_second["tier"].isin(alert_tiers).sum()) if len(df_second) > 0 else 0
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
