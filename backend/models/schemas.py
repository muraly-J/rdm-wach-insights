from pydantic import BaseModel, field_validator
from typing import Literal, Optional
from enum import Enum


# ── Allowed values ────────────────────────────────────────────────────────────

ALLOWED_METRICS = [
    # Power
    "power_total", "power_l1", "power_l2", "power_l3",
    "power_demand", "max_power_demand",
    # Energy
    "energy_import", "energy_export",
    "reactive_energy_import", "reactive_energy_export",
    # Apparent
    "apparent_power_total", "apparent_power_l1", "apparent_power_l2", "apparent_power_l3",
    "apparent_power_demand", "apparent_energy",
    # Reactive
    "reactive_power_total", "reactive_power_l1", "reactive_power_l2", "reactive_power_l3",
    "reactive_power_demand",
    # Current
    "current_avg", "current_l1", "current_l2", "current_l3",
    "current_l1_thd", "current_l3_thd", "current_unbalance",
    # Voltage
    "volts_l_n_avg", "volts_l_l_avg",
    "volts_l1_n", "volts_l2_n", "volts_l3_n",
    "volts_l1_l2", "volts_l2_l3", "volts_l3_l1",
    "volts_l1_thd", "volts_l2_thd", "volts_l3_thd",
    "volts_unbalance",
    # Power factor & frequency
    "power_factor_avg", "power_factor_l1", "power_factor_l2", "power_factor_l3",
    "freq",
    # Other
    "digital_input_1_and_2",
]

ALLOWED_TIME_RANGES = {
    "last_24h": "-24h",
    "last_7d":  "-7d",
    "last_30d": "-30d",
    "all_time": "-1y",   # InfluxDB needs a concrete start; 1 year covers "all time" for MVP
}

# Device IDs span e0101 → e1108 in the WACH ward
# We store them as a set for O(1) validation
def _build_device_set() -> set[str]:
    devices: set[str] = set()
    for prefix in range(1, 12):          # 01 through 11
        for suffix in range(1, 99):       # 01 through 98  (generous upper bound)
            devices.add(f"e{prefix:02d}{suffix:02d}")
    return devices

ALLOWED_DEVICES: set[str] = _build_device_set()


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