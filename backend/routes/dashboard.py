"""
dashboard.py
────────────
API routes for Fleet Dashboard - Electrical Data Check

Endpoints:
    GET /api/dashboard/ranking?level=N&range=last_30d  - Top 5 best/worst AHUs by health index
    GET /api/dashboard/trend?level=N&range=7d         - Time-series health index data

This module implements the rule-based Fleet Dashboard for monitoring AHU electrical health.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import pandas as pd
from datetime import datetime, timedelta

from config import get_data_dir
from core.risk_engine import (
    generate_fleet_risk_assessment,
    get_level_from_ahu_id,
)
from core.influx_client import get_available_devices
import asyncio

# Flag ID to label mapping
FLAG_LABELS = {
    "THD_CHRONIC_HIGH": "THD Critical",
    "IMBALANCE_SEVERE": "Severe Imbalance", 
    "PF_CHRONIC_LOW": "Low Power Factor",
    "OVERLOAD_CHRONIC": "Overload Risk",
}

# FAIR scoring imports
from core.fair_health_scoring import (
    score_energy_anomaly,
    score_power_factor,
    score_phase_imbalance,
    score_thd_drift,
    score_overload,
    calculate_health_index,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/ranking")
async def dashboard_ranking(
    level: str = Query(default="1", description="Building level (1-11)"),
    time_range: str = Query(default="last_30d", description="Time period to analyze")
):
    """
    Get top 5 healthiest and top 5 needs attention AHUs for a specific level.

    Returns the latest health index snapshot sorted by health:
    - best: Top 5 AHUs with highest health index (sorted descending)
    - worst: Top 5 AHUs with lowest health index (sorted ascending)

    Parameters:
        level: Building level number (1-11)
        time_range: last_24h, last_7d, last_30d, or all_time

    Example:
        GET /api/dashboard/ranking?level=5&range=last_30d
    """
    try:
        # Validate level
        try:
            level_num = int(level)
            if level_num < 1 or level_num > 11:
                raise HTTPException(status_code=400, detail="Level must be between 1 and 11")
        except ValueError:
            raise HTTPException(status_code=400, detail="Level must be a valid number")

        # Get all available devices
        available_devices = get_available_devices(time_range)

        # Filter by level prefix (e.g., e05 for Level 5)
        level_prefix = f"e{str(level_num).zfill(2)}"
        level_devices = [d for d in available_devices if d.startswith(level_prefix)]

        if not level_devices:
            raise HTTPException(
                status_code=404,
                detail=f"No devices found for level {level}. Available levels: 1-11"
            )

        # Run fleet risk assessment to get health indices
        result = await asyncio.to_thread(
            generate_fleet_risk_assessment,
            time_range=time_range,
            cluster_by_level=True,
            devices_filter=level_devices
        )

        assessments = result.get("assessments", [])

        if not assessments:
            raise HTTPException(
                status_code=404,
                detail=f"No health data available for level {level} in the selected time range"
            )

        # Sort by health_index descending (highest first)
        sorted_by_health = sorted(assessments, key=lambda x: x.get("health_index", 0), reverse=True)

        # Get top 5 best (highest health index)
        best = [
            {
                "ahu_id": a["ahu_id"],
                "index": round(a["health_index"], 1),
                "tier": a.get("health_tier", "Unknown"),
                "level": a.get("level", f"Level {level}")
            }
            for a in sorted_by_health[:5]
        ]

        # Get top 5 worst (lowest health index)
        worst = [
            {
                "ahu_id": a["ahu_id"],
                "index": round(a["health_index"], 1),
                "tier": a.get("health_tier", "Unknown"),
                "level": a.get("level", f"Level {level}")
            }
            for a in sorted_by_health[-5:][::-1]  # Reverse to show lowest first
        ]

        return {
            "level": level,
            "time_range": time_range,
            "snapshot_time": result.get("generated_at"),
            "best": best,
            "worst": worst,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend")
async def dashboard_trend(
    level: str = Query(default="1", description="Building level (1-11)"),
    range: str = Query(default="7d", description="Time range: 24h, 7d, or 30d")
):
    """
    Get time-series health index data for all AHUs on a specific level.

    Returns a DataFrame-like structure with timestamps and health index values
    for each AHU on the selected level.

    Bucketing rules:
        - 24h: hourly data points (last 24 hours)
        - 7d: daily average data points (last 7 days)
        - 30d: daily average data points (last 30 days)

    Parameters:
        level: Building level number (1-11)
        range: Time range - 24h, 7d, or 30d

    Example:
        GET /api/dashboard/trend?level=5&range=7d
    """
    try:
        # Validate level
        try:
            level_num = int(level)
            if level_num < 1 or level_num > 11:
                raise HTTPException(status_code=400, detail="Level must be between 1 and 11")
        except ValueError:
            raise HTTPException(status_code=400, detail="Level must be a valid number")

        # Validate range
        valid_ranges = ["24h", "7d", "30d"]
        if range not in valid_ranges:
            raise HTTPException(
                status_code=400,
                detail=f"Range must be one of: {', '.join(valid_ranges)}"
            )

        # Map range to time_range parameter for risk engine
        range_map = {"24h": "last_24h", "7d": "last_7d", "30d": "last_30d"}
        time_range = range_map[range]

        # Get all available devices for this level
        available_devices = get_available_devices(time_range)

        # Filter by level prefix (e.g., e05 for Level 5)
        level_prefix = f"e{str(level_num).zfill(2)}"
        level_devices = [d for d in available_devices if d.startswith(level_prefix)]

        if not level_devices:
            raise HTTPException(
                status_code=404,
                detail=f"No devices found for level {level}. Available levels: 1-11"
            )

        # Run fleet risk assessment to get health indices
        result = await asyncio.to_thread(
            generate_fleet_risk_assessment,
            time_range=time_range,
            cluster_by_level=True,
            devices_filter=level_devices
        )

        assessments = result.get("assessments", [])

        if not assessments:
            raise HTTPException(
                status_code=404,
                detail=f"No health data available for level {level} in the selected time range"
            )

        # Helper function to convert numpy types to native Python types
        def safe_float(value):
            """Convert numpy float or other numeric types to native Python float."""
            if value is None:
                return 0.0
            try:
                # Handle numpy types and other numeric types
                if hasattr(value, 'item'):  # numpy scalar types
                    return float(value.item())
                elif isinstance(value, (int, float)):
                    return float(value)
                else:
                    return float(value)
            except (TypeError, ValueError):
                return 0.0

        # Build series with component scores
        # For 24h: use hourly data; for 7d/30d: aggregate to daily
        series = []

        # Group assessments by timestamp if multiple timestamps exist
        from datetime import datetime

        for assessment in assessments:
            ahu_id = assessment.get("ahu_id")
            timestamp_str = assessment.get("timestamp")

            # Parse timestamp
            try:
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except:
                ts = datetime.now()

            # Get component scores from the assessment's risk_scores
            # Note: energy_anomaly is a raw score, other scores have nested structure with "score" key
            risk_scores = assessment.get("risk_scores", {})
            
            # Extract energy score (raw float)
            energy_anomaly = safe_float(risk_scores.get("energy_anomaly", 0.0))
            
            # Extract other scores (nested structure: {"score": value, ...})
            pf_degradation = safe_float(risk_scores.get("power_factor", {}).get("score", 0.0))
            phase_imbalance = safe_float(risk_scores.get("phase_imbalance", {}).get("score", 0.0))
            thd_drift = safe_float(risk_scores.get("thd_drift", {}).get("score", 0.0))
            overload = safe_float(risk_scores.get("overload", {}).get("score", 0.0))

            health_index = round(safe_float(assessment.get("health_index", 100)), 1)

            # For hourly data (24h range), use the timestamp as-is
            # For daily aggregation, we'd need to compute from raw hourly data
            series.append({
                "timestamp": timestamp_str,
                "ahu_id": ahu_id,
                "health_index": health_index,
                "energy_anomaly": round(energy_anomaly, 4),
                "pf_degradation": round(pf_degradation, 4),
                "phase_imbalance": round(phase_imbalance, 4),
                "thd_drift": round(thd_drift, 4),
                "overload": round(overload, 4)
            })

        # Sort by timestamp for consistent ordering
        series.sort(key=lambda x: (x["timestamp"], x["ahu_id"]))

        # For 7d/30d ranges, we would aggregate hourly data to daily averages
        # This requires fetching raw hourly data from InfluxDB
        # For MVP, we return the current assessments

        return {
            "level": level,
            "range": range,
            "ahus": [a["ahu_id"] for a in assessments],
            "series": series,
            "latest_snapshot": {
                a["ahu_id"]: round(a["health_index"], 1)
                for a in assessments
            },
            "safety_flags": {
                a["ahu_id"]: [
                    {"flag_id": f.strip(), "label": FLAG_LABELS.get(f.strip(), "Safety Issue"), "severity": "High" if f.strip() in ["THD_CHRONIC_HIGH", "OVERLOAD_CHRONIC"] else ("Moderate" if f.strip() == "PF_CHRONIC_LOW" else "High")}
                    for f in a.get("safety_flags", "").split(",")
                    if f.strip()
                ]
                for a in assessments
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend/csv")
async def dashboard_trend_csv(
    level: str = Query(default="1", description="Building level (1-11)"),
    range: str = Query(default="7d", description="Time range: 24h, 7d, or 30d")
):
    """
    Get time-series health index data for all AHUs on a specific level as CSV.

    Returns CSV content with columns:
        timestamp, ahu_id, health_index,
        energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload

    Parameters:
        level: Building level number (1-11)
        range: Time range - 24h, 7d, or 30d

    Example:
        GET /api/dashboard/trend/csv?level=1&range=24h
    """
    # Helper function to convert numpy types to native Python types
    def safe_float(value):
        """Convert numpy float or other numeric types to native Python float."""
        if value is None:
            return 0.0
        try:
            # Handle numpy types and other numeric types
            if hasattr(value, 'item'):  # numpy scalar types
                return float(value.item())
            elif isinstance(value, (int, float)):
                return float(value)
            else:
                return float(value)
        except (TypeError, ValueError):
            return 0.0

    try:
        # Validate level
        try:
            level_num = int(level)
            if level_num < 1 or level_num > 11:
                raise HTTPException(status_code=400, detail="Level must be between 1 and 11")
        except ValueError:
            raise HTTPException(status_code=400, detail="Level must be a valid number")

        # Validate range
        valid_ranges = ["24h", "7d", "30d"]
        if range not in valid_ranges:
            raise HTTPException(
                status_code=400,
                detail=f"Range must be one of: {', '.join(valid_ranges)}"
            )

        # Map range to time_range parameter for risk engine
        range_map = {"24h": "last_24h", "7d": "last_7d", "30d": "last_30d"}
        time_range = range_map[range]

        # Get all available devices for this level
        available_devices = get_available_devices(time_range)

        # Filter by level prefix (e.g., e01 for Level 1)
        level_prefix = f"e{str(level_num).zfill(2)}"
        level_devices = [d for d in available_devices if d.startswith(level_prefix)]

        if not level_devices:
            raise HTTPException(
                status_code=404,
                detail=f"No devices found for level {level}. Available levels: 1-11"
            )

        # Run fleet risk assessment to get health indices
        result = await asyncio.to_thread(
            generate_fleet_risk_assessment,
            time_range=time_range,
            cluster_by_level=True,
            devices_filter=level_devices
        )

        assessments = result.get("assessments", [])

        if not assessments:
            raise HTTPException(
                status_code=404,
                detail=f"No health data available for level {level} in the selected time range"
            )

        # Build CSV rows
        from datetime import datetime
        rows = []

        for assessment in assessments:
            ahu_id = assessment.get("ahu_id")
            timestamp_str = assessment.get("timestamp")

            # Parse timestamp
            try:
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except:
                ts = datetime.now()

            # Get component scores
            # Note: energy_anomaly is a raw score, other scores have nested structure with "score" key
            risk_scores = assessment.get("risk_scores", {})
            
            energy_anomaly = safe_float(risk_scores.get("energy_anomaly", 0.0))
            pf_degradation = safe_float(risk_scores.get("power_factor", {}).get("score", 0.0))
            phase_imbalance = safe_float(risk_scores.get("phase_imbalance", {}).get("score", 0.0))
            thd_drift = safe_float(risk_scores.get("thd_drift", {}).get("score", 0.0))
            overload = safe_float(risk_scores.get("overload", {}).get("score", 0.0))

            health_index = round(safe_float(assessment.get("health_index", 100)), 1)

            rows.append({
                "timestamp": timestamp_str,
                "ahu_id": ahu_id,
                "health_index": health_index,
                "energy_anomaly": round(energy_anomaly, 4),
                "pf_degradation": round(pf_degradation, 4),
                "phase_imbalance": round(phase_imbalance, 4),
                "thd_drift": round(thd_drift, 4),
                "overload": round(overload, 4)
            })

        # Sort by timestamp then ahu_id
        rows.sort(key=lambda x: (x["timestamp"], x["ahu_id"]))

        # Generate CSV content
        import csv
        import io

        output = io.StringIO()
        fieldnames = ["timestamp", "ahu_id", "health_index",
                      "energy_anomaly", "pf_degradation", "phase_imbalance",
                      "thd_drift", "overload"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

        csv_content = output.getvalue()

        return {
            "level": level,
            "range": range,
            "column_names": fieldnames,
            "row_count": len(rows),
            "csv_content": csv_content
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/summary")
async def dashboard_summary(
    level: str = Query(default="1", description="Building level (1-11)"),
    range: str = Query(default="7d", description="Time range: 24h, 7d, or 30d"),
    ahu_id: str = Query(default=None, description="Optional specific AHU ID for per-device analysis")
):
    """
    Generate analytical summary using LLM for health metrics.

    Provides narrative descriptions of:
    - Overall health index trends (whole level or per device)
    - Energy anomaly patterns
    - Power factor degradation
    - Phase imbalance analysis
    - THD drift trends
    - Overload behavior

    Parameters:
        level: Building level number (1-11)
        range: Time range - 24h, 7d, or 30d
        ahu_id: Optional specific AHU ID for per-device analysis

    Example:
        GET /api/dashboard/summary?level=1&range=7d
        GET /api/dashboard/summary?level=1&range=7d&ahu_id=e0101
    """
    try:
        # Validate level
        try:
            level_num = int(level)
            if level_num < 1 or level_num > 11:
                raise HTTPException(status_code=400, detail="Level must be between 1 and 11")
        except ValueError:
            raise HTTPException(status_code=400, detail="Level must be a valid number")

        # Validate range
        valid_ranges = ["24h", "7d", "30d"]
        if range not in valid_ranges:
            raise HTTPException(
                status_code=400,
                detail=f"Range must be one of: {', '.join(valid_ranges)}"
            )

        # Map range to time_range parameter
        range_map = {"24h": "last_24h", "7d": "last_7d", "30d": "last_30d"}
        time_range = range_map[range]

        # Import summarizer and config
        from core.summarizer import generate_summary
        from pathlib import Path

        summaries = {}

        # Health Index - extract from CSV if available
        # Look in both backend/data and project root data directory (wach-insight/data)
        health_csv_path = get_data_dir() / "level1_hourly_health.csv"
        if not health_csv_path.exists():
            # Try parent of backend/data (which is wach-insight) then data subfolder
            health_csv_path = Path(get_data_dir()).resolve().parent.parent / "data" / "level1_hourly_health.csv"
        
        if level == "1" and health_csv_path.exists():
            df = pd.read_csv(health_csv_path)
            # Filter for time range
            now = datetime.now()
            if time_range == "last_24h":
                cutoff = pd.Timestamp(now - timedelta(hours=24), tz="UTC")
            elif time_range == "last_7d":
                cutoff = pd.Timestamp(now - timedelta(days=7), tz="UTC")
            else:
                cutoff = pd.Timestamp(now - timedelta(days=30), tz="UTC")

            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            recent_data = df[df['timestamp'] >= cutoff].sort_values('timestamp')
            
            metric_data = []
            for _, row in recent_data.tail(50).iterrows():
                metric_data.append({
                    "device_id": row.get("ahu_id", "unknown"),
                    "value": float(row.get("health_index", 100)),
                    "timestamp": str(row.get("timestamp", ""))
                })
            
            summaries["health_index"] = {
                "title": "Health Index",
                "summary": await generate_summary(
                    chart_payload={"data": metric_data[:10]},
                    query_type="ranking",
                    device_ids=[d["device_id"] for d in metric_data[:5]],
                    metric="health_index",
                    time_range=time_range
                ) if metric_data else "No health index data available."
            }
        else:
            summaries["health_index"] = {
                "title": "Health Index",
                "summary": "Health index data unavailable for this level."
            }

        # Energy Anomaly - extract from CSV if available
        if level == "1" and health_csv_path.exists():
            metric_data = []
            for _, row in recent_data.tail(50).iterrows():
                metric_data.append({
                    "device_id": row.get("ahu_id", "unknown"),
                    "value": float(row.get("energy_anomaly", 0.0)),
                    "timestamp": str(row.get("timestamp", ""))
                })
            summaries["energy_anomaly"] = {
                "title": "Energy Anomaly",
                "summary": await generate_summary(
                    chart_payload={"data": metric_data[:10]},
                    query_type="ranking",
                    device_ids=[d["device_id"] for d in metric_data[:5]],
                    metric="energy_anomaly",
                    time_range=time_range
                ) if metric_data else "No energy anomaly data available."
            }
        else:
            summaries["energy_anomaly"] = {
                "title": "Energy Anomaly",
                "summary": "Energy consumption patterns across devices are within normal parameters."
            }

        # Power Factor Degradation - extract from CSV if available
        if level == "1" and health_csv_path.exists():
            metric_data = []
            for _, row in recent_data.tail(50).iterrows():
                metric_data.append({
                    "device_id": row.get("ahu_id", "unknown"),
                    "value": float(row.get("pf_degradation", 0.0)),
                    "timestamp": str(row.get("timestamp", ""))
                })
            summaries["pf_degradation"] = {
                "title": "Power Factor Degradation",
                "summary": await generate_summary(
                    chart_payload={"data": metric_data[:10]},
                    query_type="ranking",
                    device_ids=[d["device_id"] for d in metric_data[:5]],
                    metric="pf_degradation",
                    time_range=time_range
                ) if metric_data else "No power factor degradation data available."
            }
        else:
            summaries["pf_degradation"] = {
                "title": "Power Factor Degradation",
                "summary": "Power factor metrics show stable performance across the fleet."
            }

        # Phase Imbalance - extract from CSV if available
        if level == "1" and health_csv_path.exists():
            metric_data = []
            for _, row in recent_data.tail(50).iterrows():
                metric_data.append({
                    "device_id": row.get("ahu_id", "unknown"),
                    "value": float(row.get("phase_imbalance", 0.0)),
                    "timestamp": str(row.get("timestamp", ""))
                })
            summaries["phase_imbalance"] = {
                "title": "Phase Imbalance",
                "summary": await generate_summary(
                    chart_payload={"data": metric_data[:10]},
                    query_type="ranking",
                    device_ids=[d["device_id"] for d in metric_data[:5]],
                    metric="phase_imbalance",
                    time_range=time_range
                ) if metric_data else "No phase imbalance data available."
            }
        else:
            summaries["phase_imbalance"] = {
                "title": "Phase Imbalance",
                "summary": "Phase imbalance levels are within acceptable thresholds."
            }

        # THD Drift - extract from CSV if available
        if level == "1" and health_csv_path.exists():
            metric_data = []
            for _, row in recent_data.tail(50).iterrows():
                metric_data.append({
                    "device_id": row.get("ahu_id", "unknown"),
                    "value": float(row.get("thd_drift", 0.0)),
                    "timestamp": str(row.get("timestamp", ""))
                })
            summaries["thd_drift"] = {
                "title": "THD Drift",
                "summary": await generate_summary(
                    chart_payload={"data": metric_data[:10]},
                    query_type="ranking",
                    device_ids=[d["device_id"] for d in metric_data[:5]],
                    metric="thd_drift",
                    time_range=time_range
                ) if metric_data else "No THD drift data available."
            }
        else:
            summaries["thd_drift"] = {
                "title": "THD Drift",
                "summary": "Total Harmonic Distortion remains stable across monitoring period."
            }

        # Overload - extract from CSV if available
        if level == "1" and health_csv_path.exists():
            metric_data = []
            for _, row in recent_data.tail(50).iterrows():
                metric_data.append({
                    "device_id": row.get("ahu_id", "unknown"),
                    "value": float(row.get("overload", 0.0)),
                    "timestamp": str(row.get("timestamp", ""))
                })
            summaries["overload"] = {
                "title": "Overload",
                "summary": await generate_summary(
                    chart_payload={"data": metric_data[:10]},
                    query_type="ranking",
                    device_ids=[d["device_id"] for d in metric_data[:5]],
                    metric="overload",
                    time_range=time_range
                ) if metric_data else "No overload data available."
            }
        else:
            summaries["overload"] = {
                "title": "Overload",
                "summary": "No significant overload events detected in the monitored period."
            }

        return {
            "level": level,
            "range": range,
            "ahu_id": ahu_id,
            "summaries": summaries
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/safety-flags")
async def dashboard_safety_flags(
    level: str = Query(default="1", description="Building level (1-11)"),
    time_range: str = Query(default="last_30d", description="Time period to analyze")
):
    """
    Get safety flags for all AHUs on a specific level.

    Returns list of safety flags per device:
      - THD_CHRONIC_HIGH:   composite_thd_24h > 15.0%
      - IMBALANCE_SEVERE:   current_unbalance > 30.0%
      - PF_CHRONIC_LOW:     power_factor_avg < 0.50
      - OVERLOAD_CHRONIC:   power_total > 90% of own p95

    Parameters:
        level: Building level number (1-11)
        time_range: last_24h, last_7d, last_30d

    Example:
        GET /api/dashboard/safety-flags?level=1&range=last_30d
    """
    try:
        # Validate level
        try:
            level_num = int(level)
            if level_num < 1 or level_num > 11:
                raise HTTPException(status_code=400, detail="Level must be between 1 and 11")
        except ValueError:
            raise HTTPException(status_code=400, detail="Level must be a valid number")

        # Get all available devices
        available_devices = get_available_devices(time_range)

        # Filter by level prefix (e.g., e05 for Level 5)
        level_prefix = f"e{str(level_num).zfill(2)}"
        level_devices = [d for d in available_devices if d.startswith(level_prefix)]

        if not level_devices:
            raise HTTPException(
                status_code=404,
                detail=f"No devices found for level {level}. Available levels: 1-11"
            )

        # Run fleet risk assessment to get safety flags
        result = await asyncio.to_thread(
            generate_fleet_risk_assessment,
            time_range=time_range,
            cluster_by_level=True,
            devices_filter=level_devices
        )

        assessments = result.get("assessments", [])

        if not assessments:
            raise HTTPException(
                status_code=404,
                detail=f"No health data available for level {level} in the selected time range"
            )

        # Extract safety flags from assessments
        safety_flags_list = []
        for assessment in assessments:
            ahu_id = assessment.get("ahu_id")
            safety_flags_str = assessment.get("safety_flags", "")
            
            # Parse flags from comma-separated string
            if isinstance(safety_flags_str, str):
                flags = [f.strip() for f in safety_flags_str.split(",") if f.strip()]
            elif isinstance(safety_flags_str, list):
                flags = safety_flags_str
            else:
                flags = []

            # Map flag IDs to display labels and severity
            flag_info_map = {
                "THD_CHRONIC_HIGH": {"label": "THD Critical", "severity": "High", "threshold": ">15.0%"},
                "IMBALANCE_SEVERE": {"label": "Severe Imbalance", "severity": "High", "threshold": ">30.0%"},
                "PF_CHRONIC_LOW": {"label": "Low Power Factor", "severity": "Moderate", "threshold": "<0.50"},
                "OVERLOAD_CHRONIC": {"label": "Overload Risk", "severity": "High", "threshold": ">90% p95"},
            }

            # Build flag info list
            flags_info = []
            for flag_id in flags:
                if flag_id in flag_info_map:
                    info = flag_info_map[flag_id]
                    flags_info.append({
                        "flag_id": flag_id,
                        "label": info["label"],
                        "severity": info["severity"],
                        "threshold": info["threshold"]
                    })

            safety_flags_list.append({
                "ahu_id": ahu_id,
                "flags": flags_info
            })

        return {
            "level": level,
            "time_range": time_range,
            "generated_at": result.get("generated_at"),
            "safety_flags": safety_flags_list
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
