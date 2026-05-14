from __future__ import annotations

"""
core/etl/telemetry_provider.py
───────────────────────────────
Protocol definition for raw telemetry access, plus the InfluxDB-backed
concrete implementation.

Public API
----------
    RawTelemetryProvider  — structural Protocol; inject for testing
    InfluxTelemetryProvider — production InfluxDB-backed implementation

Protocol contract
-----------------
``fetch_hourly`` returns a DataFrame with one row per hour in [start, end)
and the following columns:

    ts                — datetime64[ns, UTC] (timezone-aware)
    energy_import_kwh — DELTA in kWh for the hour (NOT a cumulative reading)
                        Computed as last_value(t) − last_value(t-1) from the
                        raw cumulative meter.  Zero on gaps.
    total_tons        — float   mean over the hour (RT)
    sat               — float   mean supply air temperature (°C)
    rat               — float   mean return air temperature (°C)
    rah               — float   mean return air humidity (%)
    co2               — float   mean CO₂ concentration (ppm)
    wst               — float   mean water supply temperature (°C)
    wrt               — float   mean water return temperature (°C)
    dsp               — float   mean duct static pressure (Pa)
    dsp_sp            — float   mean DSP setpoint (Pa)
    rat_sp            — float   mean RAT setpoint (°C)
    co2_sp            — float   mean CO₂ setpoint (ppm)
    rah_sp            — float   mean RAH setpoint (%)
    mvlv              — float   mean main valve position (%)
    mcvlv             — float   mean mixing/cooling valve position (%)
    fa_dmpr           — float   mean fresh-air damper position (%)
    fa_dmpr_min       — float   mean fresh-air damper minimum (%)
    vsd_fb            — float   mean VSD feedback speed (Hz or %)
    vsd_ctrl          — float   mean VSD control signal (Hz or %)
    dp                — float   mean differential pressure (Pa)
    runtime           — float   count of 5-min intervals unit was running (→ int)
    power_factor_avg  — float   mean power factor (unitless)
    sts               — float   max over hour (1.0 = ran at any point)
    am                — float   max over hour (1.0 = manual mode at any point)
    oct               — float   max over hour (1.0 = occupied at any point)
    fltr              — float   max over hour (1.0 = dirty at any point)

Missing signals MUST be present as columns containing NaN — they must NOT be
absent from the returned DataFrame.
"""

from datetime import datetime
from typing import Protocol

import pandas as pd

from core.logger import get_logger

logger = get_logger(__name__)

# ── Columns the Protocol guarantees ───────────────────────────────────────────

TELEMETRY_COLUMNS: tuple[str, ...] = (
    "ts",
    "energy_import_kwh",
    "total_tons",
    "sat",
    "rat",
    "rah",
    "co2",
    "wst",
    "wrt",
    "dsp",
    "dsp_sp",
    "rat_sp",
    "co2_sp",
    "rah_sp",
    "mvlv",
    "mcvlv",
    "fa_dmpr",
    "fa_dmpr_min",
    "vsd_fb",
    "vsd_ctrl",
    "dp",
    "runtime",
    "power_factor_avg",
    "sts",
    "am",
    "oct",
    "fltr",
)

# Signals fetched as instantaneous mean
_MEAN_SIGNALS = [
    "total_tons",
    "sat",
    "rat",
    "rah",
    "co2",
    "wst",
    "wrt",
    "dsp",
    "dsp_sp",
    "rat_sp",
    "co2_sp",
    "rah_sp",
    "mvlv",
    "mcvlv",
    "fa_dmpr",
    "fa_dmpr_min",
    "vsd_fb",
    "vsd_ctrl",
    "dp",
    "power_factor_avg",
]

# Discrete signals: max over the hour (any active interval → 1)
_MAX_SIGNALS = ["sts", "am", "oct", "fltr"]

# Cumulative energy meter signal (fetched raw then diff'd)
_ENERGY_METRIC = "energy_import"

# Runtime: count of non-zero 5-min power readings (approximation)
_RUNTIME_METRIC = "power_total"


# ── Protocol ──────────────────────────────────────────────────────────────────


class RawTelemetryProvider(Protocol):
    """Returns hourly-aggregated telemetry for one AHU over [start, end).

    The returned DataFrame has exactly the columns listed in TELEMETRY_COLUMNS.
    All columns must be present; missing signals are represented as NaN.

    ``energy_import_kwh`` is the HOURLY DELTA in kWh (not a cumulative meter
    reading). The implementor is responsible for differencing the raw cumulative
    meter to produce the per-hour energy consumed.
    """

    def fetch_hourly(
        self, ahu_id: str, start: datetime, end: datetime
    ) -> pd.DataFrame: ...


# ── InfluxDB-backed implementation ────────────────────────────────────────────


class InfluxTelemetryProvider:
    """Wraps backend/core/influx_client to fetch hourly-aggregated telemetry.

    TODO: This stub is wired to the real influx_client.fetch_time_series_window
          but has NOT been validated against live InfluxDB data.  Before
          production use, verify:
          1. Measurement naming convention matches what InfluxDB contains.
          2. Energy diff produces sensible hourly kWh (check for meter resets).
          3. Unit scaling is correct for all signals.
          Recommended: add an integration test that connects to the staging
          InfluxDB and spot-checks one AHU for a known time window.

    Aggregation strategy
    --------------------
    - Cumulative energy meter (energy_import): fetched at native resolution,
      resampled to last-value-per-hour, then diff()'d to get hourly delta.
    - Instantaneous signals (sat, rat, mvlv, etc.): mean over each hour.
    - Discrete signals (sts, am, oct, fltr): max over each hour (1 if the
      signal was 1 for any 5-min interval during the hour).
    - runtime: count of 5-min intervals where power_total > 0 (proxy).
    """

    def fetch_hourly(
        self, ahu_id: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """Fetch hourly telemetry for *ahu_id* over [start, end)."""
        # Import here so feature_builder.py has zero InfluxDB imports
        from core.influx_client import fetch_time_series_window  # noqa: PLC0415

        # Build an empty skeleton indexed on the requested hours
        hour_index = pd.date_range(start=start, end=end, freq="h", tz="UTC", inclusive="left")
        result = pd.DataFrame({"ts": hour_index})
        for col in TELEMETRY_COLUMNS:
            if col != "ts":
                result[col] = float("nan")

        # ── Instantaneous signals (mean) ───────────────────────────────────────
        metric_col_map: list[tuple[str, str]] = [
            ("total_tons", "total_tons"),
            ("sat", "sat"),
            ("rat", "rat"),
            ("rah", "rah"),
            ("co2", "co2"),
            ("wst", "wst"),
            ("wrt", "wrt"),
            ("dsp", "dsp"),
            ("dsp_sp", "dsp_sp"),
            ("rat_sp", "rat_sp"),
            ("co2_sp", "co2_sp"),
            ("rah_sp", "rah_sp"),
            ("mvlv", "mvlv"),
            ("mcvlv", "mcvlv"),
            ("fa_dmpr", "fa_dmpr"),
            ("fa_dmpr_min", "fa_dmpr_min"),
            ("vsd_fb", "vsd_fb"),
            ("vsd_ctrl", "vsd_ctrl"),
            ("dp", "dp"),
            ("power_factor_avg", "power_factor_avg"),
        ]

        for influx_metric, col_name in metric_col_map:
            try:
                raw = fetch_time_series_window([ahu_id], influx_metric, start, end)
                if ahu_id in raw.columns:
                    # raw is indexed by ts; resample to 1h mean
                    series = raw[ahu_id].resample("1h").mean()
                    series.index = series.index.tz_localize("UTC") if series.index.tz is None else series.index.tz_convert("UTC")
                    result = result.set_index("ts")
                    result[col_name] = series.reindex(result.index)
                    result = result.reset_index()
            except Exception as exc:
                logger.warning(
                    "InfluxTelemetryProvider: failed to fetch %s for %s: %s",
                    influx_metric,
                    ahu_id,
                    exc,
                )

        # ── Discrete signals (max) ─────────────────────────────────────────────
        discrete_map: list[tuple[str, str]] = [
            ("sts", "sts"),
            ("am", "am"),
            ("oct", "oct"),
            ("fltr", "fltr"),
        ]

        for influx_metric, col_name in discrete_map:
            try:
                raw = fetch_time_series_window([ahu_id], influx_metric, start, end)
                if ahu_id in raw.columns:
                    series = raw[ahu_id].resample("1h").max()
                    series.index = series.index.tz_localize("UTC") if series.index.tz is None else series.index.tz_convert("UTC")
                    result = result.set_index("ts")
                    result[col_name] = series.reindex(result.index)
                    result = result.reset_index()
            except Exception as exc:
                logger.warning(
                    "InfluxTelemetryProvider: failed to fetch discrete %s for %s: %s",
                    influx_metric,
                    ahu_id,
                    exc,
                )

        # ── Energy (cumulative → hourly delta) ────────────────────────────────
        try:
            raw = fetch_time_series_window([ahu_id], _ENERGY_METRIC, start, end)
            if ahu_id in raw.columns:
                # Last value per hour, then diff for hourly delta
                series = raw[ahu_id].resample("1h").last()
                series.index = series.index.tz_localize("UTC") if series.index.tz is None else series.index.tz_convert("UTC")
                delta = series.diff()
                # First row is NaN after diff — use 0 as convention
                delta.iloc[0] = 0.0
                # Clamp negative values (meter reset) to 0
                delta = delta.clip(lower=0.0)
                result = result.set_index("ts")
                result["energy_import_kwh"] = delta.reindex(result.index)
                result = result.reset_index()
        except Exception as exc:
            logger.warning(
                "InfluxTelemetryProvider: failed to fetch energy_import for %s: %s",
                ahu_id,
                exc,
            )

        # ── Runtime (proxy: count 5-min power_total > 0) ──────────────────────
        try:
            raw = fetch_time_series_window([ahu_id], _RUNTIME_METRIC, start, end)
            if ahu_id in raw.columns:
                series = (raw[ahu_id] > 0).resample("1h").sum().astype(float)
                series.index = series.index.tz_localize("UTC") if series.index.tz is None else series.index.tz_convert("UTC")
                result = result.set_index("ts")
                result["runtime"] = series.reindex(result.index)
                result = result.reset_index()
        except Exception as exc:
            logger.warning(
                "InfluxTelemetryProvider: failed to fetch runtime proxy for %s: %s",
                ahu_id,
                exc,
            )

        return result[list(TELEMETRY_COLUMNS)].reset_index(drop=True)
