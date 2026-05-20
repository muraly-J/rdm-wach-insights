"""Canonical AHU feature row schema for the ML pipeline."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AHUFeatureRow(BaseModel):
    """Single row of features for one AHU at one hourly timestamp."""

    model_config = ConfigDict(strict=True)

    # ── Identity ──────────────────────────────────────────────────────────────
    ahu_id: str
    ts: datetime

    # ── Target ───────────────────────────────────────────────────────────────
    hourly_energy_kwh: float | None

    # ── Cooling work ─────────────────────────────────────────────────────────
    total_tons: float | None
    sat: float | None           # supply air temperature
    sat_minus_rat: float | None  # derived: SAT − RAT

    # ── Contextual ───────────────────────────────────────────────────────────
    rat: float | None           # return air temperature
    rah: float | None           # return air humidity
    co2: float | None           # CO₂ concentration
    wst: float | None           # water supply temperature
    wrt: float | None           # water return temperature
    wst_minus_wrt: float | None  # derived: WST − WRT
    oat: float | None           # outside air temperature
    oah: float | None           # outside air humidity
    ghi: float | None           # global horizontal irradiance

    # ── Control ──────────────────────────────────────────────────────────────
    rat_sp: float | None        # return air temp setpoint
    co2_sp: float | None        # CO₂ setpoint
    rah_sp: float | None        # return air humidity setpoint
    dsp_sp: float | None        # duct static pressure setpoint
    dsp: float | None           # duct static pressure actual
    dsp_dev: float | None       # derived: DSP − DSP_SP
    fa_dmpr: float | None       # fresh air damper position
    fa_dmpr_min: float | None   # fresh air damper minimum position
    mvlv: float | None          # main valve position
    mcvlv: float | None         # mixing/cooling valve position
    oct: bool                      # occupancy
    am: bool                       # auto/manual mode

    # ── Health ───────────────────────────────────────────────────────────────
    vsd_fb: float | None        # VSD feedback speed
    vsd_ctrl: float | None      # VSD control signal
    vsd_dev: float | None       # derived: VSD_FB − VSD_CTRL
    fltr: bool                     # filter status (dirty flag)
    sts: bool                      # run status
    dp: float | None            # differential pressure
    runtime: int                   # hours of runtime (integer-coarse)
    power_factor_avg: float | None

    # ── Temporal ─────────────────────────────────────────────────────────────
    hour_of_day: int               # 0–23
    day_of_week: int               # 0=Monday … 6=Sunday
    is_weekend: bool
    is_holiday: bool

    # ── Lags & rolling windows ────────────────────────────────────────────────
    energy_lag_1h: float | None
    energy_lag_24h: float | None
    energy_lag_168h: float | None
    energy_rolling_24h_mean: float | None
    total_tons_rolling_24h_mean: float | None
    oat_rolling_24h_mean: float | None
