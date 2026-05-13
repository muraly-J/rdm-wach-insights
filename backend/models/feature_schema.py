"""Canonical AHU feature row schema for the ML pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AHUFeatureRow(BaseModel):
    """Single row of features for one AHU at one hourly timestamp."""

    model_config = ConfigDict(strict=True)

    # ── Identity ──────────────────────────────────────────────────────────────
    ahu_id: str
    ts: datetime

    # ── Target ───────────────────────────────────────────────────────────────
    hourly_energy_kwh: Optional[float]

    # ── Cooling work ─────────────────────────────────────────────────────────
    total_tons: Optional[float]
    sat: Optional[float]           # supply air temperature
    sat_minus_rat: Optional[float]  # derived: SAT − RAT

    # ── Contextual ───────────────────────────────────────────────────────────
    rat: Optional[float]           # return air temperature
    rah: Optional[float]           # return air humidity
    co2: Optional[float]           # CO₂ concentration
    wst: Optional[float]           # water supply temperature
    wrt: Optional[float]           # water return temperature
    wst_minus_wrt: Optional[float]  # derived: WST − WRT
    oat: Optional[float]           # outside air temperature
    oah: Optional[float]           # outside air humidity
    ghi: Optional[float]           # global horizontal irradiance

    # ── Control ──────────────────────────────────────────────────────────────
    rat_sp: Optional[float]        # return air temp setpoint
    co2_sp: Optional[float]        # CO₂ setpoint
    rah_sp: Optional[float]        # return air humidity setpoint
    dsp_sp: Optional[float]        # duct static pressure setpoint
    dsp: Optional[float]           # duct static pressure actual
    dsp_dev: Optional[float]       # derived: DSP − DSP_SP
    fa_dmpr: Optional[float]       # fresh air damper position
    fa_dmpr_min: Optional[float]   # fresh air damper minimum position
    mvlv: Optional[float]          # main valve position
    mcvlv: Optional[float]         # mixing/cooling valve position
    oct: bool                      # occupancy
    am: bool                       # auto/manual mode

    # ── Health ───────────────────────────────────────────────────────────────
    vsd_fb: Optional[float]        # VSD feedback speed
    vsd_ctrl: Optional[float]      # VSD control signal
    vsd_dev: Optional[float]       # derived: VSD_FB − VSD_CTRL
    fltr: bool                     # filter status (dirty flag)
    sts: bool                      # run status
    dp: Optional[float]            # differential pressure
    runtime: int                   # hours of runtime (integer-coarse)
    power_factor_avg: Optional[float]

    # ── Temporal ─────────────────────────────────────────────────────────────
    hour_of_day: int               # 0–23
    day_of_week: int               # 0=Monday … 6=Sunday
    is_weekend: bool
    is_holiday: bool

    # ── Lags & rolling windows ────────────────────────────────────────────────
    energy_lag_1h: Optional[float]
    energy_lag_24h: Optional[float]
    energy_lag_168h: Optional[float]
    energy_rolling_24h_mean: Optional[float]
    total_tons_rolling_24h_mean: Optional[float]
    oat_rolling_24h_mean: Optional[float]
