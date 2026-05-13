import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from models.feature_schema import AHUFeatureRow


def test_feature_row_required_columns():
    row = AHUFeatureRow.model_construct()
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
