from pydantic import BaseModel, field_validator
from typing import Literal, Optional, Dict, Any, List
from enum import Enum


# ── Metric Units Reference ─────────────────────────────────────────────────────
# Energy: kWh (Kilowatt-hours), kVARh, kVAh
# Power: kW (Kilowatts), kVAR, kVA
# Current: A (Amperes)
# Voltage: V (Volts)
# Frequency: Hz (Hertz)
# THD: % (Percentage)
# Power Factor: unitless ratio (-1.0 to 1.0)
# Unbalance: % (Percentage)

ALLOWED_METRICS_WITH_UNITS = {
    # POWER (kW, kVAR, kVA)
    "power_total": ("kW", "Total active power across all phases"),
    "power_l1": ("kW", "Active power Phase L1"),
    "power_l2": ("kW", "Active power Phase L2"),
    "power_l3": ("kW", "Active power Phase L3"),
    "power_demand": ("kW", "Rolling average demand"),
    "max_power_demand": ("kW", "Peak demand recorded"),
    "apparent_power_total": ("kVA", "Total apparent power"),
    "apparent_power_l1": ("kVA", "Apparent power Phase L1"),
    "apparent_power_l2": ("kVA", "Apparent power Phase L2"),
    "apparent_power_l3": ("kVA", "Apparent power Phase L3"),
    "apparent_power_demand": ("kVA", "Apparent power demand"),
    "reactive_power_total": ("kVAR", "Total reactive power"),
    "reactive_power_l1": ("kVAR", "Reactive power Phase L1"),
    "reactive_power_l2": ("kVAR", "Reactive power Phase L2"),
    "reactive_power_l3": ("kVAR", "Reactive power Phase L3"),
    "reactive_power_demand": ("kVAR", "Reactive power demand"),
    
    # ENERGY (kWh, kVARh, kVAh)
    "energy_import": ("kWh", "Energy consumed from grid"),
    "energy_export": ("kWh", "Energy sent to grid"),
    "reactive_energy_import": ("kVARh", "Reactive energy consumed"),
    "reactive_energy_export": ("kVARh", "Reactive energy sent to grid"),
    "apparent_energy": ("kVAh", "Total apparent energy"),
    
    # CURRENT (A)
    "current_avg": ("A", "Average current across phases"),
    "current_l1": ("A", "Current Phase L1"),
    "current_l2": ("A", "Current Phase L2"),
    "current_l3": ("A", "Current Phase L3"),
    # CURRENT THD (%)
    "current_l1_thd": ("%", "Current THD Phase L1"),
    "current_l3_thd": ("%", "Current THD Phase L3"),
    
    # VOLTAGE (V)
    "volts_l_n_avg": ("V", "Phase-to-neutral voltage average"),
    "volts_l_l_avg": ("V", "Phase-to-phase voltage average"),
    "volts_l1_n": ("V", "Phase L1 to neutral voltage"),
    "volts_l2_n": ("V", "Phase L2 to neutral voltage"),
    "volts_l3_n": ("V", "Phase L3 to neutral voltage"),
    "volts_l1_l2": ("V", "Phase L1 to L2 voltage"),
    "volts_l2_l3": ("V", "Phase L2 to L3 voltage"),
    "volts_l3_l1": ("V", "Phase L3 to L1 voltage"),
    
    # THD (%)
    "volts_l1_thd": ("%", "Voltage THD Phase L1"),
    "volts_l2_thd": ("%", "Voltage THD Phase L2"),
    "volts_l3_thd": ("%", "Voltage THD Phase L3"),
    
    # POWER FACTOR (unitless, -1 to 1)
    "power_factor_avg": ("", "Power factor average (unitless ratio -1 to 1)"),
    "power_factor_l1": ("", "Power factor Phase L1 (unitless ratio -1 to 1)"),
    "power_factor_l2": ("", "Power factor Phase L2 (unitless ratio -1 to 1)"),
    "power_factor_l3": ("", "Power factor Phase L3 (unitless ratio -1 to 1)"),
    
    # FREQUENCY (Hz)
    "freq": ("Hz", "System frequency"),
    
    # UNBALANCE (%)
    "current_unbalance": ("%", "Current unbalance percentage"),
    "volts_unbalance": ("%", "Voltage unbalance percentage"),
    
    # OTHER
    "digital_input_1_and_2": ("", "Binary status inputs"),
}


# ── Allowed values ────────────────────────────────────────────────────────────

ALLOWED_METRICS = list(ALLOWED_METRICS_WITH_UNITS.keys())

ALLOWED_TIME_RANGES = {
    "last_24h": "-24h",
    "last_7d":  "-7d",
    "last_30d": "-30d",
    "all_time": "-1y",   # InfluxDB needs a concrete start; 1 year covers "all time" for MVP
}

# ── AHU Level Configuration (11 Levels based on Relationships TSV) ───────────
# WACH Ward E-Series Energy Meters (Levels 01-11)
# Each level has different number of devices due to varying building floor sizes
# Source: AHU Relational Database - Relationships.tsv

import json
from pathlib import Path


def _load_ahu_metadata() -> dict:
    """Load AHU metadata from JSON file."""
    try:
        data_file = Path(__file__).parent.parent / "data" / "ahu_metadata.json"
        if data_file.exists():
            with open(data_file) as f:
                return json.load(f)
    except Exception as e:
        print(f"[schemas] Warning: Could not load AHU metadata: {e}")
    return {}


# Load metadata once at module level
_AHU_METADATA = _load_ahu_metadata()

AHU_LEVEL_CONFIG = {
    1: {"device_ids": ['e0101', 'e0102', 'e0103', 'e0104', 'e0105', 'e0106', 'e0107', 'e0108', 'e0109', 'e0110', 'e0111', 'e0112', 'e0113', 'e0114', 'e0115', 'e0116', 'e0117', 'e0118', 'e0120', 'e0121', 'e0212']},
    2: {"device_ids": ['e0201', 'e0202', 'e0203', 'e0204', 'e0205', 'e0206', 'e0207', 'e0208', 'e0209', 'e0213', 'e0214', 'e0215', 'e0216', 'e0217', 'e0218']},
    3: {"device_ids": ['e0210', 'e0211', 'e0301', 'e0303', 'e0304', 'e0306', 'e0307', 'e0308', 'e0311', 'e0312', 'e0313', 'e0314', 'e0315', 'e0401', 'e0402', 'e0423']},
    4: {"device_ids": ['e0403', 'e0404', 'e0406', 'e0407', 'e0408', 'e0409', 'e0411', 'e0412', 'e0413', 'e0414', 'e0415', 'e0416', 'e0419']},
    5: {"device_ids": ['e0501', 'e0502', 'e0503', 'e0504', 'e0505', 'e0506', 'e0507', 'e0508', 'e0509', 'e0510', 'e0511', 'e0622']},
    6: {"device_ids": ['e0602', 'e0603', 'e0604', 'e0605', 'e0606', 'e0607', 'e0611', 'e0625', 'e0626', 'e0627', 'e0628']},
    7: {"device_ids": ['e0701', 'e0702', 'e0703', 'e0704']},
    8: {"device_ids": ['e0801', 'e0802', 'e0803', 'e0804', 'e0805']},
    9: {"device_ids": ['e0901', 'e0902', 'e0903', 'e0904', 'e0905', 'e0906', 'e0907', 'e0908']},
    10: {"device_ids": ['e1001', 'e1002', 'e1003', 'e1004', 'e1005', 'e1006', 'e1007', 'e1008']},
    11: {"device_ids": ['e1101', 'e1102', 'e1103', 'e1104', 'e1105', 'e1106', 'e1107', 'e1108']},
}

# Build set of all valid device IDs from AHU_LEVEL_CONFIG
def _build_device_set() -> set[str]:
    devices: set[str] = set()
    for level_config in AHU_LEVEL_CONFIG.values():
        devices.update(level_config["device_ids"])
    return sorted(devices)


def get_devices_by_level(level: int) -> list[str]:
    """
    Get all device IDs for a specific building level.

    Args:
        level: Building level (1-11)

    Returns:
        List of device IDs for the specified level
    """
    if level not in AHU_LEVEL_CONFIG:
        raise ValueError(f"Level {level} is invalid. Valid levels: 1-11")
    return AHU_LEVEL_CONFIG[level]["device_ids"].copy()


def get_level_device_count(level: int) -> int:
    """
    Get the number of devices for a specific level.

    Args:
        level: Building level (1-11)

    Returns:
        Number of devices for the specified level
    """
    if level not in AHU_LEVEL_CONFIG:
        raise ValueError(f"Level {level} is invalid. Valid levels: 1-11")
    return len(AHU_LEVEL_CONFIG[level]["device_ids"])


def get_all_device_counts() -> dict[int, int]:
    """
    Get device counts for all levels.

    Returns:
        Dict mapping level number to device count
    """
    return {level: len(config["device_ids"]) for level, config in AHU_LEVEL_CONFIG.items()}


ALLOWED_DEVICES: set[str] = _build_device_set()


# ── Reverse device-to-level mapping ───────────────────────────────────────────

def _build_device_to_level_map() -> dict[str, str]:
    """
    Build reverse mapping from device ID to level string.
    
    Returns:
        Dict mapping device_id -> "Level N"
    """
    mapping = {}
    for level, config in AHU_LEVEL_CONFIG.items():
        for dev_id in config["device_ids"]:
            mapping[dev_id] = f"Level {level}"
    return mapping


DEVICE_TO_LEVEL: dict[str, str] = _build_device_to_level_map()


def get_level_for_device(ahu_id: str) -> str:
    """
    Get the level string for a given device ID.
    
    Args:
        ahu_id: Device ID (e.g., 'e0101')
        
    Returns:
        Level string (e.g., 'Level 1'), or 'Unknown' if device not found
    """
    return DEVICE_TO_LEVEL.get(ahu_id, "Unknown")


# ── Query types ───────────────────────────────────────────────────────────────

class QueryType(str, Enum):
    time_series = "time_series"   # single device, metric over time  → line chart
    ranking     = "ranking"       # top-N devices by metric           → bar chart


# ── Structured query (output of LLM + validated by middleware) ────────────────

class StructuredQuery(BaseModel):
    query_type:  QueryType
    device_ids:  list[str]              # one for time_series; empty means "all" for ranking
    metric:      str
    time_range:  Literal["last_24h", "last_7d", "last_30d", "all_time"]
    top_n:       Optional[int] = None   # only for ranking queries

    @field_validator("metric")
    @classmethod
    def metric_must_be_allowed(cls, v: str) -> str:
        if v not in ALLOWED_METRICS:
            raise ValueError(f"Metric '{v}' is not in the allowed list: {ALLOWED_METRICS}")
        return v

    @field_validator("device_ids")
    @classmethod
    def devices_must_be_allowed(cls, ids: list[str]) -> list[str]:
        for d in ids:
            if d not in ALLOWED_DEVICES:
                raise ValueError(f"Device '{d}' is not a recognised WACH device.")
        return ids


# ── API request / response models ─────────────────────────────────────────────

class UserQueryRequest(BaseModel):
    user_query: str


class QueryResponse(BaseModel):
    query_type:       QueryType
    metric:           str
    time_range:       str
    structured_query: dict           # echo back for transparency / debugging
    chart_data:       dict           # Recharts-ready payload
    summary:          str
    csv_available:    bool = True


# ──────────────────────────────────────────────────────────────────────────────
# ELECTRICAL RISK CHECK SCHEMAS (Stage 2B)
# ──────────────────────────────────────────────────────────────────────────────


class RiskScore(BaseModel):
    """Single risk score with severity and signal."""
    score: float
    severity: str
    confidence: str
    signal: str


class PFRiskScore(RiskScore):
    """Power factor risk score with additional context."""
    confidence: str = "High"


class PhaseImbalanceRiskScore(RiskScore):
    """Phase imbalance risk score with root cause uncertainty flag."""
    confidence: str = "Moderate"
    root_cause_uncertainty: Optional[str] = None


class THDRiskScore(RiskScore):
    """THD drift risk score."""
    confidence: str = "High"


class OverloadRiskScore(RiskScore):
    """Overload risk score with seasonal caveat."""
    confidence: str = "Moderate"
    seasonal_caveat: Optional[str] = None


class EnergyAssessment(BaseModel):
    """Energy anomaly assessment."""
    forecast_24h_kwh: Optional[float] = None
    normal_range_kwh: Optional[List[float]] = None
    deviation_probability_pct: Optional[float] = None
    trend_7d: str = "stable"


class DataQuality(BaseModel):
    """Data quality metrics."""
    missing_data_pct: float
    days_since_last_valid_reading: int
    model_source: str
    model_confidence_flag: str


class HealthTierResponse(BaseModel):
    """Health tier classification."""
    tier: str
    description: str


# ── Individual AHU Risk Assessment ────────────────────────────────────────────

class SingleAHURiskAssessment(BaseModel):
    """
    Risk assessment for a single AHU.
    
    Example output:
    {
      "ahu_id": "wach_e0101",
      "timestamp": "2026-02-23T14:00:00+08:00",
      "health_index": 84,
      "health_tier": "Healthy",
      "energy": {...},
      "risk_scores": {...},
      "data_quality": {...}
    }
    """
    ahu_id: str
    timestamp: str
    health_index: float
    health_tier: str
    
    energy: EnergyAssessment
    risk_scores: Dict[str, Any]
    data_quality: DataQuality


class FleetRiskAssessment(BaseModel):
    """
    Fleet-wide risk assessment.
    
    Includes:
    - generated_at timestamp
    - time_range analyzed
    - total AHUs assessed
    - fleet_summary with tier distribution
    - assessments list (sorted by health_index)
    """
    generated_at: str
    time_range: str
    total_ahus: int
    fleet_summary: Dict[str, Any]
    assessments: List[SingleAHURiskAssessment]


# ── Fleet Summary (Aggregated) ───────────────────────────────────────────────

class FleetTierDistribution(BaseModel):
    """Distribution of AHUs across health tiers."""
    Healthy: int = 0
    Monitor: int = 0
    Maintenance_Soon: int = 0
    Critical: int = 0


class TopUnitsItem(BaseModel):
    """Top N units item with health index."""
    ahu_id: str
    health_index: float


class TopUnitsByRisk(BaseModel):
    """Top N units item with overload score."""
    ahu_id: str
    overload_score: float


class FleetSummary(BaseModel):
    """
    Aggregated fleet summary for the Electrical Risk Check.
    
    Returns:
        - Tier distribution (counts by tier)
        - Top 5 units by lowest health index
        - Top 5 with rising risk trends
        - Top 5 that have improved most
        - Data quality issues count
    """
    tier_distribution: FleetTierDistribution
    top_5_lowest_health_index: List[TopUnitsItem]
    top_5_rising_risk: List[TopUnitsByRisk]
    top_5_improved: List[TopUnitsItem]
    data_quality_issues_count: int


# ── API Request Models ───────────────────────────────────────────────────────

class RiskSummaryRequest(BaseModel):
    """Request parameters for fleet summary."""
    time_range: Literal["last_24h", "last_7d", "last_30d", "all_time"] = "last_30d"


# ── Utility Functions ────────────────────────────────────────────────────────

def get_metric_unit(metric: str) -> str:
    """
    Get the unit for a given metric.
    
    Args:
        metric: Metric name (e.g., "power_total", "energy_import")
        
    Returns:
        Unit string (e.g., "kW", "kWh", "A")
    """
    if metric in ALLOWED_METRICS_WITH_UNITS:
        return ALLOWED_METRICS_WITH_UNITS[metric][0]
    return ""


def get_metric_description(metric: str) -> str:
    """
    Get the description for a given metric.
    
    Args:
        metric: Metric name
        
    Returns:
        Description string
    """
    if metric in ALLOWED_METRICS_WITH_UNITS:
        return ALLOWED_METRICS_WITH_UNITS[metric][1]
    return ""


def is_valid_ahu_id(device_id: str) -> bool:
    """
    Check if a device ID is valid according to WACH Ward AHU ranges.

    Args:
        device_id: Device ID in format "eXXXX"

    Returns:
        True if valid, False otherwise
    """
    if not device_id.startswith("e"):
        return False

    try:
        level = int(device_id[1:3])
        
        if level not in AHU_LEVEL_CONFIG:
            return False
        
        # Check if device_id is in the actual device IDs list
        config = AHU_LEVEL_CONFIG[level]
        return device_id in config["device_ids"]
    except (ValueError, IndexError):
        return False


def get_level_from_ahu_id(device_id: str) -> Optional[int]:
    """
    Extract building level from AHU ID.
    
    Args:
        device_id: Device ID (e.g., "e0101", "e0508")
        
    Returns:
        Level number (1-8) or None if invalid
    """
    if not is_valid_ahu_id(device_id):
        return None
    
    try:
        return int(device_id[1:3])
    except (ValueError, IndexError):
        return None


def get_ahu_level_variance() -> dict:
    """
    Get variance information for AHU levels.

    Returns:
        Dict with level info including device counts and ID ranges
    """
    variance_info = {}
    for level, config in AHU_LEVEL_CONFIG.items():
        variance_info[f"Level {level}"] = {
            "device_count": len(config["device_ids"]),
            "id_range": f"e{level:02d}{config['start']:02d}-e{level:02d}{config['end']:02d}",
            "device_ids": config["device_ids"]
        }
    return variance_info


def get_level_ahu_info(level: int) -> dict:
    """
    Get detailed AHU information for a level from metadata.

    Args:
        level: Building level (1-11)

    Returns:
        Dict with level info including department, area, and device list
    """
    config = AHU_LEVEL_CONFIG.get(level)
    if not config:
        return {}

    result = {
        "level_number": level,
        "device_count": len(config["device_ids"]),
        "id_range": f"e{level:02d}{config['start']:02d}-e{level:02d}{config['end']:02d}",
        "device_ids": config["device_ids"].copy(),
    }

    # Add metadata if available
    level_key = f"L{level:02d}"
    if _AHU_METADATA and level_key in _AHU_METADATA.get("levels", {}):
        metadata = _AHU_METADATA["levels"][level_key]
        result.update({
            "department_name": metadata.get("department_name"),
            "area_name": metadata.get("area_name"),
        })

    return result


def get_device_level_info(device_id: str) -> Optional[dict]:
    """
    Get department and area info for a device.

    Args:
        device_id: Device ID

    Returns:
        Dict with level, department_name, area_name or None if invalid
    """
    if not is_valid_ahu_id(device_id):
        return None

    level = get_level_from_ahu_id(device_id)
    result = {"level": level, "device_id": device_id}

    # Add metadata if available
    level_key = f"L{level:02d}"
    if _AHU_METADATA and device_id in _AHU_METADATA.get("device_to_level", {}):
        info = _AHU_METADATA["device_to_level"][device_id]
        result.update({
            "department_name": info.get("department_name"),
            "area_name": info.get("area_name"),
        })
    elif _AHU_METADATA and level_key in _AHU_METADATA.get("levels", {}):
        metadata = _AHU_METADATA["levels"][level_key]
        result.update({
            "department_name": metadata.get("department_name"),
            "area_name": metadata.get("area_name"),
        })

    return result


def get_devices_by_department(department_name: str) -> list[str]:
    """
    Get all device IDs for a specific department.

    Args:
        department_name: Department name

    Returns:
        List of device IDs for the specified department
    """
    if not _AHU_METADATA:
        return []

    dept_level = _AHU_METADATA.get("department_to_level", {}).get(department_name)
    if not dept_level:
        return []

    level_num = dept_level["level_number"]
    return AHU_LEVEL_CONFIG[level_num]["device_ids"].copy()


def get_devices_by_level(level: int) -> list[str]:
    """
    Get all device IDs for a specific building level.

    Args:
        level: Building level (1-11)

    Returns:
        List of device IDs for the specified level
    """
    if level not in AHU_LEVEL_CONFIG:
        raise ValueError(f"Level {level} is invalid. Valid levels: 1-11")
    return AHU_LEVEL_CONFIG[level]["device_ids"].copy()


def get_level_device_count(level: int) -> int:
    """
    Get the number of devices for a specific level.

    Args:
        level: Building level (1-11)

    Returns:
        Number of devices for the specified level
    """
    if level not in AHU_LEVEL_CONFIG:
        raise ValueError(f"Level {level} is invalid. Valid levels: 1-11")
    return len(AHU_LEVEL_CONFIG[level]["device_ids"])


def get_all_device_counts() -> dict[int, int]:
    """
    Get device counts for all levels.

    Returns:
        Dict mapping level number to device count
    """
    return {level: len(config["device_ids"]) for level, config in AHU_LEVEL_CONFIG.items()}
