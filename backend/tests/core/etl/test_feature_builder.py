from __future__ import annotations

"""
tests/core/etl/test_feature_builder.py
───────────────────────────────────────
Unit tests for the hourly AHU feature builder.

All tests use a FakeTelemetryProvider and explicit synthetic weather
DataFrames — no live InfluxDB or open-meteo calls are made.
"""

from datetime import date, datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd
import pytest
from core.etl.feature_builder import build_features
from models.feature_schema import AHUFeatureRow

# ── Constants ──────────────────────────────────────────────────────────────────

_AHU_ID = "e0101"  # valid device from AHU_LEVEL_CONFIG
_START = datetime(2026, 4, 28, 0, tzinfo=timezone.utc)
_END = datetime(2026, 4, 29, 0, tzinfo=timezone.utc)  # 24 hours, exclusive


# ── FakeTelemetryProvider ─────────────────────────────────────────────────────


def _make_telemetry(
    start: datetime,
    end: datetime,
    *,
    energy_kwh: float = 10.0,
    sat: float = 14.0,
    rat: float = 24.0,
    wst: float = 7.0,
    wrt: float = 12.0,
    dsp: float = 45.0,
    dsp_sp: float = 50.0,
    vsd_fb: float = 60.0,
    vsd_ctrl: float = 55.0,
    sts: float = 1.0,
    am: float = 0.0,
    oct_val: float = 1.0,
    fltr: float = 0.0,
    vary_energy: bool = False,
) -> pd.DataFrame:
    """Build a deterministic hourly telemetry DataFrame for [start, end)."""
    hours = pd.date_range(start=start, end=end, freq="h", tz="UTC", inclusive="left")
    n = len(hours)

    energy_vals: list[float]
    if vary_energy:
        # Predictable pattern: row index + 1 so lags are detectable
        energy_vals = [float(i + 1) for i in range(n)]
    else:
        energy_vals = [energy_kwh] * n

    return pd.DataFrame(
        {
            "ts": hours,
            "energy_import_kwh": energy_vals,
            "total_tons": [5.0] * n,
            "sat": [sat] * n,
            "rat": [rat] * n,
            "rah": [60.0] * n,
            "co2": [700.0] * n,
            "wst": [wst] * n,
            "wrt": [wrt] * n,
            "dsp": [dsp] * n,
            "dsp_sp": [dsp_sp] * n,
            "rat_sp": [23.0] * n,
            "co2_sp": [1000.0] * n,
            "rah_sp": [65.0] * n,
            "mvlv": [80.0] * n,
            "mcvlv": [75.0] * n,
            "fa_dmpr": [30.0] * n,
            "fa_dmpr_min": [10.0] * n,
            "vsd_fb": [vsd_fb] * n,
            "vsd_ctrl": [vsd_ctrl] * n,
            "dp": [200.0] * n,
            "runtime": [1.0] * n,
            "power_factor_avg": [0.95] * n,
            "sts": [sts] * n,
            "am": [am] * n,
            "oct": [oct_val] * n,
            "fltr": [fltr] * n,
        }
    )


class FakeTelemetryProvider:
    """Returns synthetic hourly telemetry; ignores ahu_id validation."""

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df.copy()

    def fetch_hourly(
        self, ahu_id: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        mask = (self._df["ts"] >= start) & (self._df["ts"] < end)
        return self._df[mask].reset_index(drop=True)


def _make_weather(start: datetime, end: datetime) -> pd.DataFrame:
    """Build a synthetic weather DataFrame aligned to [start, end)."""
    hours = pd.date_range(start=start, end=end, freq="h", tz="UTC", inclusive="left")
    n = len(hours)
    return pd.DataFrame(
        {
            "ts": hours,
            "oat": [30.0] * n,
            "oah": [70.0] * n,
            "ghi": [200.0] * n,
        }
    )


def _make_provider(start=_START, end=_END, **kwargs) -> FakeTelemetryProvider:
    df = _make_telemetry(start, end, **kwargs)
    return FakeTelemetryProvider(df)


def _make_wx(start=_START, end=_END) -> pd.DataFrame:
    return _make_weather(start, end)


# ── Test 1: schema conformance ────────────────────────────────────────────────


def test_build_features_matches_schema(tmp_path: Path) -> None:
    """Output DataFrame columns match AHUFeatureRow.model_fields.keys();
    a sample row validates via AHUFeatureRow.model_validate."""
    provider = _make_provider()
    wx = _make_wx()

    df = build_features(
        _AHU_ID,
        _START,
        _END,
        provider=provider,
        cache_db=tmp_path / "feat.duckdb",
        weather=wx,
    )

    assert not df.empty, "DataFrame must not be empty"

    expected_fields = set(AHUFeatureRow.model_fields.keys())
    actual_cols = set(df.columns)
    missing = expected_fields - actual_cols
    extra = actual_cols - expected_fields
    assert not missing, f"DataFrame missing columns: {missing}"
    assert not extra, f"DataFrame has unexpected columns: {extra}"

    # Validate a sample row
    sample = df.iloc[0].to_dict()
    AHUFeatureRow.model_validate(sample)


# ── Test 2: derived columns correct ──────────────────────────────────────────


def test_build_features_derived_columns_correct(tmp_path: Path) -> None:
    """sat_minus_rat, wst_minus_wrt, dsp_dev, vsd_dev computed correctly."""
    provider = _make_provider(
        sat=14.0,
        rat=24.0,
        wst=7.0,
        wrt=12.0,
        dsp=45.0,
        dsp_sp=50.0,
        vsd_fb=60.0,
        vsd_ctrl=55.0,
    )
    wx = _make_wx()

    df = build_features(
        _AHU_ID,
        _START,
        _END,
        provider=provider,
        cache_db=tmp_path / "feat.duckdb",
        weather=wx,
    )

    assert not df.empty
    row = df.iloc[0]
    assert row["sat_minus_rat"] == pytest.approx(14.0 - 24.0)
    assert row["wst_minus_wrt"] == pytest.approx(7.0 - 12.0)
    assert row["dsp_dev"] == pytest.approx(45.0 - 50.0)
    assert row["vsd_dev"] == pytest.approx(60.0 - 55.0)


# ── Test 3: lag features correct ─────────────────────────────────────────────


def test_build_features_lags_correct(tmp_path: Path) -> None:
    """energy_lag_1h[t] == hourly_energy_kwh[t-1] for 1h, 24h, 168h."""
    # Use 200 hours so we can check all lags
    long_start = datetime(2026, 1, 1, 0, tzinfo=timezone.utc)
    long_end = datetime(2026, 1, 9, 8, tzinfo=timezone.utc)  # 200 hours
    provider = FakeTelemetryProvider(
        _make_telemetry(long_start, long_end, vary_energy=True)
    )
    wx = _make_weather(long_start, long_end)

    df = build_features(
        _AHU_ID,
        long_start,
        long_end,
        provider=provider,
        cache_db=tmp_path / "feat.duckdb",
        weather=wx,
        am_policy="keep_with_flag",  # keep all rows
    )

    df = df.reset_index(drop=True)
    energy = df["hourly_energy_kwh"].to_numpy()
    lag1 = df["energy_lag_1h"].to_numpy()
    lag24 = df["energy_lag_24h"].to_numpy()
    lag168 = df["energy_lag_168h"].to_numpy()

    # Check lag at index 1 (1h lag should equal index 0)
    assert lag1[1] == pytest.approx(energy[0])
    # Check lag at index 24 (24h lag should equal index 0)
    assert lag24[24] == pytest.approx(energy[0])
    # Check lag at index 168
    assert lag168[168] == pytest.approx(energy[0])


# ── Test 4: weather joined correctly ─────────────────────────────────────────


def test_build_features_weather_joined(tmp_path: Path) -> None:
    """Provide synthetic weather; assert oat, oah, ghi populated for matching ts."""
    provider = _make_provider()
    wx = pd.DataFrame(
        {
            "ts": pd.date_range(start=_START, end=_END, freq="h", tz="UTC", inclusive="left"),
            "oat": [33.5] * 24,
            "oah": [80.0] * 24,
            "ghi": [500.0] * 24,
        }
    )

    df = build_features(
        _AHU_ID,
        _START,
        _END,
        provider=provider,
        cache_db=tmp_path / "feat.duckdb",
        weather=wx,
    )

    assert not df.empty
    assert df["oat"].notna().all(), "oat must not be NaN after weather join"
    assert abs(df["oat"] - 33.5).max() < 1e-6, f"oat should be 33.5, got {df['oat'].tolist()}"
    assert abs(df["oah"] - 80.0).max() < 1e-6, "oah should be 80.0"
    assert abs(df["ghi"] - 500.0).max() < 1e-6, "ghi should be 500.0"


# ── Test 5: drop_for_training removes sts==0 and am==1 rows ──────────────────


def test_build_features_drops_sts_zero_and_am_one_under_drop_policy(
    tmp_path: Path,
) -> None:
    """Under drop_for_training, rows with sts==0 or am==1 are absent."""
    hours = pd.date_range(start=_START, end=_END, freq="h", tz="UTC", inclusive="left")
    n = len(hours)  # 24

    # Build custom telemetry: first 6 hours sts=0, next 6 am=1, rest ok
    sts_col = [0.0] * 6 + [1.0] * (n - 6)
    am_col = [0.0] * 6 + [1.0] * 6 + [0.0] * (n - 12)
    base = _make_telemetry(_START, _END)
    base["sts"] = sts_col
    base["am"] = am_col
    provider = FakeTelemetryProvider(base)
    wx = _make_wx()

    df = build_features(
        _AHU_ID,
        _START,
        _END,
        provider=provider,
        cache_db=tmp_path / "feat.duckdb",
        weather=wx,
        am_policy="drop_for_training",
    )

    # After drop: sts==0 rows (first 6) removed; am==1 rows (hours 6-11) removed
    # Remaining: hours 12-23 = 12 rows
    assert len(df) == 12, f"expected 12 rows, got {len(df)}"
    assert (df["sts"] == True).all(), "all remaining rows must have sts=True"  # noqa: E712
    assert (df["am"] == False).all(), "all remaining rows must have am=False"  # noqa: E712


# ── Test 6: keep_with_flag keeps all rows ────────────────────────────────────


def test_build_features_keeps_all_under_keep_with_flag_policy(
    tmp_path: Path,
) -> None:
    """Under keep_with_flag, all rows are preserved regardless of sts/am."""
    hours = pd.date_range(start=_START, end=_END, freq="h", tz="UTC", inclusive="left")
    n = len(hours)
    sts_col = [0.0] * 6 + [1.0] * (n - 6)
    am_col = [0.0] * 6 + [1.0] * 6 + [0.0] * (n - 12)
    base = _make_telemetry(_START, _END)
    base["sts"] = sts_col
    base["am"] = am_col
    provider = FakeTelemetryProvider(base)
    wx = _make_wx()

    df = build_features(
        _AHU_ID,
        _START,
        _END,
        provider=provider,
        cache_db=tmp_path / "feat.duckdb",
        weather=wx,
        am_policy="keep_with_flag",
    )

    assert len(df) == n, f"expected {n} rows (all kept), got {len(df)}"


# ── Test 7: persist idempotently ─────────────────────────────────────────────


def test_build_features_persists_idempotently(tmp_path: Path) -> None:
    """Calling build_features twice inserts 0 new rows on the second call."""
    provider = _make_provider()
    wx = _make_wx()
    db = tmp_path / "feat.duckdb"

    df1 = build_features(
        _AHU_ID,
        _START,
        _END,
        provider=provider,
        cache_db=db,
        weather=wx,
    )
    count_after_first = len(df1)

    # Count rows in DuckDB
    with duckdb.connect(str(db)) as conn:
        before_second = conn.execute(
            "SELECT COUNT(*) FROM ahu_features WHERE ahu_id = ?", [_AHU_ID]
        ).fetchone()[0]

    # Second call — same provider, same range
    provider2 = _make_provider()
    df2 = build_features(
        _AHU_ID,
        _START,
        _END,
        provider=provider2,
        cache_db=db,
        weather=wx,
    )

    with duckdb.connect(str(db)) as conn:
        after_second = conn.execute(
            "SELECT COUNT(*) FROM ahu_features WHERE ahu_id = ?", [_AHU_ID]
        ).fetchone()[0]

    assert before_second == after_second, (
        f"second call inserted new rows: {before_second} → {after_second}"
    )
    assert len(df2) == count_after_first


# ── Test 8: invalid ahu_id raises ValueError ──────────────────────────────────


def test_build_features_invalid_ahu_id_raises(tmp_path: Path) -> None:
    """Non-matching AHU ID format raises ValueError before any data fetch."""
    provider = _make_provider()
    wx = _make_wx()

    with pytest.raises(ValueError, match="Invalid AHU ID"):
        build_features(
            "bad_id",
            _START,
            _END,
            provider=provider,
            cache_db=tmp_path / "feat.duckdb",
            weather=wx,
        )


def test_build_features_unknown_ahu_id_raises(tmp_path: Path) -> None:
    """Known format but unknown device ID raises ValueError."""
    provider = _make_provider()
    wx = _make_wx()

    with pytest.raises(ValueError, match="not in AHU_LEVEL_CONFIG"):
        build_features(
            "e9999",
            _START,
            _END,
            provider=provider,
            cache_db=tmp_path / "feat.duckdb",
            weather=wx,
        )


# ── Test 9: holiday flag correct ──────────────────────────────────────────────


def test_build_features_holiday_flag_correct(tmp_path: Path) -> None:
    """holidays_fn returning True for 2026-05-01 sets is_holiday correctly."""
    # 2026-05-01 is Labour Day — use a span that includes May 1
    start = datetime(2026, 4, 30, 0, tzinfo=timezone.utc)
    end = datetime(2026, 5, 2, 0, tzinfo=timezone.utc)  # 48 hours

    provider = FakeTelemetryProvider(_make_telemetry(start, end))
    wx = _make_weather(start, end)

    def _my_holidays(d: date) -> bool:
        return d == date(2026, 5, 1)

    df = build_features(
        _AHU_ID,
        start,
        end,
        provider=provider,
        cache_db=tmp_path / "feat.duckdb",
        weather=wx,
        holidays_fn=_my_holidays,
        am_policy="keep_with_flag",
    )

    df = df.reset_index(drop=True)

    # Convert ts to date for comparison
    df["_date"] = pd.to_datetime(df["ts"]).dt.date

    holiday_rows = df[df["_date"] == date(2026, 5, 1)]
    non_holiday_rows = df[df["_date"] != date(2026, 5, 1)]

    assert not holiday_rows.empty, "No rows found for 2026-05-01"
    assert holiday_rows["is_holiday"].all(), "All May-1 rows must be is_holiday=True"
    assert not non_holiday_rows["is_holiday"].any(), "Non-May-1 rows must be is_holiday=False"
