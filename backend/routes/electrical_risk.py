"""
electrical_risk.py
──────────────────
API routes for Electrical Risk Check - Rule-based baseline system (Stage 2B)

Endpoints:
    GET /api/electrical-risk              - Fleet-wide risk assessment
    GET /api/electrical-risk/{ahu_id}     - Single AHU detailed risk assessment
    GET /api/electrical-risk/summary      - Fleet summary with tier distribution

This module implements the complete "Electrical Risk Check" feature as described
in Stage 2B: Rule-Based Baseline System.

Usage:
    curl http://localhost:8000/api/electrical-risk?time_range=last_30d
    curl http://localhost:8000/api/electrical-risk/e0101
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from backend.core.risk_engine import (
    get_electrical_risk_check,
    get_ahu_risk_details,
)
from backend.core.influx_client import get_available_devices

router = APIRouter(prefix="/api/electrical-risk", tags=["Electrical Risk"])


@router.get("")
async def fleet_risk_assessment(
    time_range: str = Query(default="last_30d", description="Time period to analyze"),
    cluster_by_level: bool = Query(default=True, description="Group AHUs by building level")
):
    """
    Fleet-wide electrical risk assessment.
    
    Returns comprehensive risk scores for all AHUs in the fleet, including:
    - Health index (0-100)
    - Individual risk scores (energy, PF, imbalance, THD, overload)
    - Health tier classification
    - Fleet summary with top issues
    
    Parameters:
        time_range: last_24h, last_7d, last_30d, or all_time
        cluster_by_level: If true, group AHUs by building level for peer comparison
    
    Example:
        GET /api/electrical-risk?time_range=last_30d
    """
    try:
        result = await get_electrical_risk_check(
            time_range=time_range,
            cluster_by_level=cluster_by_level
        )
        
        # Check if any devices were found with data
        assessments = result.get("assessments", [])
        if not assessments:
            raise HTTPException(status_code=404, detail="No devices with electrical data found for the specified time range")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/level/{level}")
async def level_risk_assessment(
    level: str,
    time_range: str = Query(default="last_30d", description="Time period to analyze")
):
    """
    Electrical risk assessment for a specific building level.

    Returns comprehensive risk scores for all AHUs in the specified level,
    grouped and compared against peers in the same level.

    Parameters:
        level: Building level (1-11)
        time_range: last_24h, last_7d, last_30d, or all_time

    Example:
        GET /api/electrical-risk/level/5
    """
    try:
        # Get devices for this level
        from backend.models.schemas import get_devices_by_level
        
        available_devices = get_available_devices(time_range)
        level_prefix = f"e{level.zfill(2)}"
        
        # Filter devices by level prefix
        level_devices = [d for d in available_devices if d.startswith(level_prefix)]
        
        if not level_devices:
            raise HTTPException(
                status_code=404,
                detail=f"No devices found for level {level}. Available levels: 1-11"
            )
        
        # Run assessment for this level
        result = await get_electrical_risk_check(
            time_range=time_range,
            cluster_by_level=True
        )
        
        # Filter assessments to only include devices from this level
        assessments = result.get("assessments", [])
        level_assessments = [a for a in assessments if a.get("level") == f"Level {level}"]
        
        # Build level-specific summary
        tier_distribution = {}
        top_5_lowest = []
        
        for a in level_assessments:
            tier = a.get("health_tier", "Unknown")
            tier_distribution[tier] = tier_distribution.get(tier, 0) + 1
        
        # Sort by health index ascending for lowest
        sorted_by_health = sorted(level_assessments, key=lambda x: x.get("health_index", 0))
        top_5_lowest = [
            {"ahu_id": a["ahu_id"], "health_index": a["health_index"]}
            for a in sorted_by_health[:5]
        ]
        
        return {
            "level": level,
            "device_count": len(level_assessments),
            "assessments": level_assessments,
            "fleet_summary": {
                "tier_distribution": tier_distribution,
                "top_5_lowest_health_index": top_5_lowest,
                "top_5_rising_risk": [],
                "top_5_improved": [],
                "data_quality_issues_count": 0,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ahu_id}")
async def ahu_risk_details(
    ahu_id: str,
    time_range: str = Query(default="last_30d", description="Time period to analyze")
):
    """
    Detailed risk assessment for a single AHU.
    
    Returns comprehensive analysis including:
    - Health index and tier
    - All 5 risk scores with severity levels
    - Human-readable signals explaining each score
    - Data quality metrics
    
    Parameters:
        ahu_id: AHU identifier (e.g., e0101, e0505)
        time_range: last_24h, last_7d, last_30d, or all_time
    
    Example:
        GET /api/electrical-risk/e0101
    """
    try:
        result = await get_ahu_risk_details(
            ahu_id=ahu_id,
            time_range=time_range
        )
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def fleet_summary(
    time_range: str = Query(default="last_30d", description="Time period to analyze")
):
    """
    Fleet summary with tier distribution and top issues.
    
    Returns:
        - Tier counts (Healthy/Monitor/Maintenance Soon/Critical)
        - Top 5 units with lowest health index
        - Top 5 with rising risk trends
        - Top 5 that have improved most
        - Data quality issues count
    
    Parameters:
        time_range: last_24h, last_7d, last_30d, or all_time
    
    Example:
        GET /api/electrical-risk/summary
    """
    try:
        result = await get_electrical_risk_check(
            time_range=time_range,
            cluster_by_level=True
        )
        
        return result.get("fleet_summary", {
            "tier_distribution": {},
            "top_5_lowest_health_index": [],
            "top_5_rising_risk": [],
            "top_5_improved": [],
            "data_quality_issues_count": 0,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
