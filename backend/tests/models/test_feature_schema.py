from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from models.feature_schema import AHUFeatureRow


def _valid_fixture() -> dict:
    """Return a minimal, fully-valid AHUFeatureRow payload."""
    return {
        "ahu_id": "e0101",
        "ts": datetime(2026, 5, 13, 14, 0, 0, tzinfo=timezone.utc),
        "hourly_energy_kwh": 12.5,
        "total_tons": 18.2,
        "sat": 14.1,
        "sat_minus_rat": -8.3,
        "rat": 22.4,
        "rah": 55.0,
        "co2": 650.0,
        "wst": 7.2,
        "wrt": 12.6,
        "wst_minus_wrt": -5.4,
        "oat": 31.2,
        "oah": 78.0,
        "ghi": 540.0,
        "rat_sp": 22.0,
        "co2_sp": 800.0,
        "rah_sp": 55.0,
        "dsp_sp": 250.0,
        "dsp": 248.0,
        "dsp_dev": -2.0,
        "fa_dmpr": 18.0,
        "fa_dmpr_min": 10.0,
        "mvlv": 62.0,
        "mcvlv": 0.0,
        "oct": True,
        "am": False,
        "vsd_fb": 78.0,
        "vsd_ctrl": 80.0,
        "vsd_dev": -2.0,
        "fltr": False,
        "sts": True,
        "dp": 120.0,
        "runtime": 8400,
        "power_factor_avg": 0.92,
        "hour_of_day": 14,
        "day_of_week": 2,
        "is_weekend": False,
        "is_holiday": False,
        "energy_lag_1h": 12.1,
        "energy_lag_24h": 11.8,
        "energy_lag_168h": 12.4,
        "energy_rolling_24h_mean": 12.0,
        "total_tons_rolling_24h_mean": 17.9,
        "oat_rolling_24h_mean": 30.5,
    }


def test_feature_row_required_columns():
    # 1. All expected field names are present on the model.
    required = {
        "ahu_id", "ts",
        # target
        "hourly_energy_kwh",
        # cooling work
        "total_tons", "sat", "sat_minus_rat",
        # contextual
        "rat", "rah", "co2", "wst", "wrt", "wst_minus_wrt",
        "oat", "oah", "ghi",
        # control
        "rat_sp", "co2_sp", "rah_sp", "dsp_sp", "dsp", "dsp_dev",
        "fa_dmpr", "fa_dmpr_min", "mvlv", "mcvlv", "oct", "am",
        # health
        "vsd_fb", "vsd_ctrl", "vsd_dev", "fltr", "sts", "dp",
        "runtime", "power_factor_avg",
        # temporal
        "hour_of_day", "day_of_week", "is_weekend", "is_holiday",
        # lags
        "energy_lag_1h", "energy_lag_24h", "energy_lag_168h",
        "energy_rolling_24h_mean", "total_tons_rolling_24h_mean",
        "oat_rolling_24h_mean",
    }
    assert required.issubset(AHUFeatureRow.model_fields.keys())

    # 2. Real validation (not model_construct) confirms types are honoured.
    row = AHUFeatureRow.model_validate(_valid_fixture())
    assert row.ahu_id == "e0101"
    assert isinstance(row.hourly_energy_kwh, float)
    assert isinstance(row.sts, bool)
    assert isinstance(row.hour_of_day, int)
    assert isinstance(row.ts, datetime)


def test_feature_row_strict_rejects_type_mismatch():
    # Pydantic v2 strict mode: int coerces to float (both are numeric),
    # but str -> float is always rejected and float -> int is rejected.
    # Use a float where runtime (int) is expected — strict mode raises.
    bad = {**_valid_fixture(), "runtime": 8400.5}  # float, not int — strict mode rejects
    with pytest.raises(ValidationError):
        AHUFeatureRow.model_validate(bad)
