from __future__ import annotations

"""
models/schemas.py
─────────────────
Pydantic models and allowlist constants for the WACH Insight API.

Exposes:
  StructuredQuery — the parsed representation of a user's NL query
  ALLOWED_METRICS, ALLOWED_DEVICES, ALLOWED_TIME_RANGES — InfluxDB allowlists
  QueryType — enum of supported query categories
  ChatHistoryItem — a single turn in the conversation history
"""

import json
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, field_validator

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
    "power_total": {
        "unit": "kW",
        "description": "Total active power across all phases",
        "aliases": ["power", "total power", "active power"],
    },
    "power_l1": {"unit": "kW", "description": "Active power Phase L1", "aliases": []},
    "power_l2": {"unit": "kW", "description": "Active power Phase L2", "aliases": []},
    "power_l3": {"unit": "kW", "description": "Active power Phase L3", "aliases": []},
    "power_demand": {"unit": "kW", "description": "Rolling average demand", "aliases": []},
    "max_power_demand": {"unit": "kW", "description": "Peak demand recorded", "aliases": ["peak demand"]},
    "apparent_power_total": {"unit": "kVA", "description": "Total apparent power", "aliases": ["apparent power"]},
    "apparent_power_l1": {"unit": "kVA", "description": "Apparent power Phase L1", "aliases": []},
    "apparent_power_l2": {"unit": "kVA", "description": "Apparent power Phase L2", "aliases": []},
    "apparent_power_l3": {"unit": "kVA", "description": "Apparent power Phase L3", "aliases": []},
    "apparent_power_demand": {"unit": "kVA", "description": "Apparent power demand", "aliases": []},
    "reactive_power_total": {"unit": "kVAR", "description": "Total reactive power", "aliases": ["reactive power"]},
    "reactive_power_l1": {"unit": "kVAR", "description": "Reactive power Phase L1", "aliases": []},
    "reactive_power_l2": {"unit": "kVAR", "description": "Reactive power Phase L2", "aliases": []},
    "reactive_power_l3": {"unit": "kVAR", "description": "Reactive power Phase L3", "aliases": []},
    "reactive_power_demand": {"unit": "kVAR", "description": "Reactive power demand", "aliases": []},
    # ENERGY (kWh, kVARh, kVAh)
    "energy_import": {"unit": "kWh", "description": "Energy consumed from grid", "aliases": ["energy", "energy consumption", "energy usage", "energy import"]},
    "energy_export": {"unit": "kWh", "description": "Energy sent to grid", "aliases": []},
    "reactive_energy_import": {"unit": "kVARh", "description": "Reactive energy consumed", "aliases": []},
    "reactive_energy_export": {"unit": "kVARh", "description": "Reactive energy sent to grid", "aliases": []},
    "apparent_energy": {"unit": "kVAh", "description": "Total apparent energy", "aliases": []},
    # CURRENT (A)
    "current_avg": {"unit": "A", "description": "Average current across phases", "aliases": ["current"]},
    "current_l1": {"unit": "A", "description": "Current Phase L1", "aliases": []},
    "current_l2": {"unit": "A", "description": "Current Phase L2", "aliases": []},
    "current_l3": {"unit": "A", "description": "Current Phase L3", "aliases": []},
    # CURRENT THD (%)
    "current_l1_thd": {"unit": "%", "description": "Current THD Phase L1", "aliases": ["thd", "thd l1"]},
    "current_l3_thd": {"unit": "%", "description": "Current THD Phase L3", "aliases": ["thd l3"]},
    # VOLTAGE (V)
    "volts_l_n_avg": {"unit": "V", "description": "Phase-to-neutral voltage average", "aliases": ["voltage", "voltage readings"]},
    "volts_l_l_avg": {"unit": "V", "description": "Phase-to-phase voltage average", "aliases": []},
    "volts_l1_n": {"unit": "V", "description": "Phase L1 to neutral voltage", "aliases": []},
    "volts_l2_n": {"unit": "V", "description": "Phase L2 to neutral voltage", "aliases": []},
    "volts_l3_n": {"unit": "V", "description": "Phase L3 to neutral voltage", "aliases": []},
    "volts_l1_l2": {"unit": "V", "description": "Phase L1 to L2 voltage", "aliases": []},
    "volts_l2_l3": {"unit": "V", "description": "Phase L2 to L3 voltage", "aliases": []},
    "volts_l3_l1": {"unit": "V", "description": "Phase L3 to L1 voltage", "aliases": []},
    # THD (%)
    "volts_l1_thd": {"unit": "%", "description": "Voltage THD Phase L1", "aliases": []},
    "volts_l2_thd": {"unit": "%", "description": "Voltage THD Phase L2", "aliases": []},
    "volts_l3_thd": {"unit": "%", "description": "Voltage THD Phase L3", "aliases": []},
    # POWER FACTOR (unitless)
    "power_factor_avg": {"unit": "", "description": "Power factor average (unitless ratio -1 to 1)", "aliases": ["power factor"]},
    "power_factor_l1": {"unit": "", "description": "Power factor Phase L1 (unitless ratio -1 to 1)", "aliases": []},
    "power_factor_l2": {"unit": "", "description": "Power factor Phase L2 (unitless ratio -1 to 1)", "aliases": []},
    "power_factor_l3": {"unit": "", "description": "Power factor Phase L3 (unitless ratio -1 to 1)", "aliases": []},
    # FREQUENCY (Hz)
    "freq": {"unit": "Hz", "description": "System frequency", "aliases": ["frequency"]},
    # UNBALANCE (%)
    "current_unbalance": {"unit": "%", "description": "Current unbalance percentage", "aliases": ["unbalance", "phase imbalance", "phase unbalance", "current imbalance"]},
    "volts_unbalance": {"unit": "%", "description": "Voltage unbalance percentage", "aliases": ["voltage unbalance", "voltage imbalance"]},
    # OTHER
    "digital_input_1_and_2": {"unit": "", "description": "Binary status inputs", "aliases": []},
}


# ── Allowed values ────────────────────────────────────────────────────────────

ALLOWED_METRICS = list(ALLOWED_METRICS_WITH_UNITS.keys())

# ── Metric alias resolver ────────────────────────────────────────────────────

def _build_alias_lookup() -> dict[str, str]:
    """
    Build reverse lookup: alias string -> metric key.
    Sorted longest-first so multi-word aliases match before single-word.
    """
    lookup: dict[str, str] = {}
    # First pass: add all metric key names themselves
    for key in ALLOWED_METRICS_WITH_UNITS:
        lookup[key] = key
    # Second pass: add aliases (longer aliases inserted first for priority)
    pairs: list[tuple[str, str]] = []
    for key, entry in ALLOWED_METRICS_WITH_UNITS.items():
        for alias in entry["aliases"]:
            pairs.append((alias.lower(), key))
    # Sort by alias length descending — longest match wins
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    for alias, key in pairs:
        if alias not in lookup:  # don't override metric key names
            lookup[alias] = key
    return lookup


_ALIAS_LOOKUP: dict[str, str] = _build_alias_lookup()
# Sorted by length descending for substring matching
_ALIAS_KEYS_BY_LENGTH: list[str] = sorted(_ALIAS_LOOKUP.keys(), key=len, reverse=True)


def resolve_metric(text: str) -> str | None:
    """
    Resolve a natural-language query text to a metric key.

    Matching strategy:
      1. Exact metric key match (e.g., "power_total" in text)
      2. Longest alias substring match (multi-word before single-word)

    Returns the metric key string, or None if no match.
    """
    text_lower = text.lower()
    for alias in _ALIAS_KEYS_BY_LENGTH:
        if alias in text_lower:
            return _ALIAS_LOOKUP[alias]
    return None

ALLOWED_TIME_RANGES = {
    "last_24h": "-24h",
    "last_7d":  "-7d",
    "last_30d": "-30d",
    "all_time": "-1y",   # InfluxDB needs a concrete start; 1 year covers "all time" for MVP
    "last_30d_hourly": "-30d",  # Used by history_generator.py for hourly historical data
}

# ── AHU Level Configuration (11 Levels based on Relationships TSV) ───────────
# WACH Ward E-Series Energy Meters (Levels 01-11)
# Each level has different number of devices due to varying building floor sizes
# Source: AHU Relational Database - Relationships.tsv


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
    time_series  = "time_series"   # single device, metric over time  → line chart
    ranking      = "ranking"       # top-N devices by metric           → bar chart
    prediction   = "prediction"    # forecast query → redirect to prediction panel
    health_index = "health_index"  # health score query → redirect to health index chart


# ── Structured query (output of LLM + validated by middleware) ────────────────

class StructuredQuery(BaseModel):
    query_type:  QueryType
    device_ids:  list[str]              # one for time_series; empty means "all" for ranking
    metric:      str
    time_range:  Literal["last_24h", "last_7d", "last_30d", "all_time"]
    top_n:       int | None = None   # only for ranking queries

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
    root_cause_uncertainty: str | None = None


class THDRiskScore(RiskScore):
    """THD drift risk score."""
    confidence: str = "High"


class OverloadRiskScore(RiskScore):
    """Overload risk score with seasonal caveat."""
    confidence: str = "Moderate"
    seasonal_caveat: str | None = None


class EnergyAssessment(BaseModel):
    """Energy anomaly assessment."""
    forecast_24h_kwh: float | None = None
    normal_range_kwh: list[float] | None = None
    deviation_probability_pct: float | None = None
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
      "device_id": "wach_e0101",
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
    risk_scores: dict[str, Any]
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
    fleet_summary: dict[str, Any]
    assessments: list[SingleAHURiskAssessment]


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
    top_5_lowest_health_index: list[TopUnitsItem]
    top_5_rising_risk: list[TopUnitsByRisk]
    top_5_improved: list[TopUnitsItem]
    data_quality_issues_count: int


# ── API Request Models ───────────────────────────────────────────────────────

class RiskSummaryRequest(BaseModel):
    """Request parameters for fleet summary."""
    time_range: Literal["last_24h", "last_7d", "last_30d", "all_time"] = "last_30d"


class ChatHistoryItem(BaseModel):
    """A single message in the chat conversation history."""
    role: Literal["user", "model"]
    content: str


class AIChatRequest(BaseModel):
    """Request body for POST /api/chat"""
    message: str
    history: list[ChatHistoryItem] = []
    context: dict | None = None


# ── Utility Functions ────────────────────────────────────────────────────────

def get_metric_unit(metric: str) -> str:
    """
    Get the unit for a given metric.

    Args:
        metric: Metric name (e.g., "power_total", "energy_import")

    Returns:
        Unit string (e.g., "kW", "kWh", "A")
    """
    entry = ALLOWED_METRICS_WITH_UNITS.get(metric)
    if entry is None:
        return ""
    return entry["unit"]


def get_metric_description(metric: str) -> str:
    """
    Get the description for a given metric.

    Args:
        metric: Metric name

    Returns:
        Description string
    """
    entry = ALLOWED_METRICS_WITH_UNITS.get(metric)
    if entry is None:
        return ""
    return entry["description"]


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


def get_level_from_ahu_id(device_id: str) -> int | None:
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


def get_device_level_info(device_id: str) -> dict | None:
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


# ── Work Order models ─────────────────────────────────────────────────────────


class WorkOrderCreate(BaseModel):
    ahu_id: str
    level: int
    title: str
    description: str | None = None
    severity: str  # "critical" | "warning" | "info"
    trigger_source: str = "chat"  # "watchman" | "chat" | "manual"
    fair_snapshot: dict | None = None  # {F, A, I, R, composite}


class WorkOrder(BaseModel):
    id: int
    ahu_id: str
    level: int
    title: str
    description: str | None
    severity: str
    status: str
    created_by: str
    created_at: str
    updated_at: str
    resolved_at: str | None
    trigger_source: str
    fair_snapshot: dict | None
    notified_via: str
    approved_by: str | None


class WorkOrderUpdate(BaseModel):
    status: str
    notes: str | None = None
    approved_by: str | None = None


# ── Agent memory model ────────────────────────────────────────────────────────


class AgentMemoryEntry(BaseModel):
    key: str
    value: dict
    expires_at: str | None = None  # ISO datetime string


# ── Watchman alert model ──────────────────────────────────────────────────────


class WatchmanAlert(BaseModel):
    ahu_id: str
    level: int
    fair_score: float
    severity: str  # "critical" | "warning"
    fair_breakdown: dict  # {F, A, I, R}
