from __future__ import annotations

"""
tests/core/external/test_weather_openmeteo.py
─────────────────────────────────────────────
Tests for the open-meteo weather adapter.

Uses respx to mock both the archive and forecast endpoints so no real HTTP
calls are made.  Each test receives a fresh DuckDB cache via tmp_path.
"""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import respx
from httpx import Response

# ── Helpers ────────────────────────────────────────────────────────────────────

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _make_hourly_response(start_iso: str, hours: int) -> dict:
    """Build a minimal open-meteo JSON payload for *hours* hourly rows."""
    from datetime import timedelta

    base = datetime.fromisoformat(start_iso)
    times = [
        (base + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(hours)
    ]
    oat = [20.0 + h * 0.1 for h in range(hours)]
    oah = [60.0 + h * 0.05 for h in range(hours)]
    ghi = [100.0 + h * 0.5 for h in range(hours)]
    return {
        "hourly": {
            "time": times,
            "temperature_2m": oat,
            "relative_humidity_2m": oah,
            "shortwave_radiation": ghi,
        }
    }


# ── Test 1: Schema + row count (archive only) ─────────────────────────────────


@respx.mock
def test_fetch_weather_returns_expected_schema(tmp_path: Path) -> None:
    """Historical range → archive API; result must have correct columns + types."""
    from core.external.weather_openmeteo import fetch_weather

    start = datetime(2025, 3, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2025, 3, 3, 23, 0, tzinfo=timezone.utc)
    expected_hours = 72  # 3 days × 24 hours

    payload = _make_hourly_response("2025-03-01T00:00", expected_hours)
    respx.get(ARCHIVE_URL).mock(return_value=Response(200, json=payload))

    df = fetch_weather(
        lat=3.139,
        lon=101.6869,
        start=start,
        end=end,
        cache_db=tmp_path / "weather.duckdb",
    )

    # Column names in exact order
    assert list(df.columns) == ["ts", "oat", "oah", "ghi"], f"columns mismatch: {list(df.columns)}"

    # Row count
    assert len(df) == expected_hours, f"expected {expected_hours} rows, got {len(df)}"

    # ts dtype — timezone-aware UTC
    assert hasattr(df["ts"].dtype, "tz"), "ts must be timezone-aware"
    assert str(df["ts"].dtype.tz) == "UTC", f"ts timezone must be UTC, got {df['ts'].dtype.tz}"

    # Numeric columns — must be exactly float64 (not Float64 nullable, float32, etc.)
    for col in ("oat", "oah", "ghi"):
        assert df[col].dtype == np.float64, f"{col} dtype is {df[col].dtype}, expected float64"

    # Monotonically increasing ts
    assert df["ts"].is_monotonic_increasing, "ts must be monotonically increasing"


# ── Test 2: Cache hit on second call ─────────────────────────────────────────


@respx.mock
def test_fetch_weather_uses_cache_on_second_call(tmp_path: Path) -> None:
    """Second call with identical args must NOT hit the API (read from cache)."""
    from core.external.weather_openmeteo import fetch_weather

    start = datetime(2025, 6, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2025, 6, 1, 5, 0, tzinfo=timezone.utc)  # 6 hours
    hours = 6

    payload = _make_hourly_response("2025-06-01T00:00", hours)
    route = respx.get(ARCHIVE_URL).mock(return_value=Response(200, json=payload))

    cache_db = tmp_path / "weather.duckdb"

    # First call — hits the API
    df1 = fetch_weather(lat=3.139, lon=101.6869, start=start, end=end, cache_db=cache_db)
    assert route.call_count == 1, "first call should hit archive API once"

    # Second call — must serve from cache
    df2 = fetch_weather(lat=3.139, lon=101.6869, start=start, end=end, cache_db=cache_db)
    assert route.call_count == 1, "second call must NOT hit archive API again"

    # Both results identical
    assert len(df1) == len(df2) == hours
    pd.testing.assert_frame_equal(df1.reset_index(drop=True), df2.reset_index(drop=True))


# ── Test 3: Boundary span (archive + forecast) ────────────────────────────────


@respx.mock
def test_fetch_weather_spans_archive_and_forecast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Range straddles today: archive called for past, forecast for future — once each."""
    from core.external import weather_openmeteo
    from core.external.weather_openmeteo import fetch_weather

    # Pin "today UTC" to 2025-09-15 so we control the boundary
    fake_today = datetime(2025, 9, 15, 0, 0, tzinfo=timezone.utc).date()
    monkeypatch.setattr(weather_openmeteo, "_today_utc", lambda: fake_today)

    # Request: 2025-09-14 00:00 → 2025-09-15 23:00 (straddles boundary)
    start = datetime(2025, 9, 14, 0, 0, tzinfo=timezone.utc)
    end = datetime(2025, 9, 15, 23, 0, tzinfo=timezone.utc)

    # 24 hours in archive part (Sep 14) + 24 hours in forecast part (Sep 15)
    archive_payload = _make_hourly_response("2025-09-14T00:00", 24)
    forecast_payload = _make_hourly_response("2025-09-15T00:00", 24)

    archive_route = respx.get(ARCHIVE_URL).mock(return_value=Response(200, json=archive_payload))
    forecast_route = respx.get(FORECAST_URL).mock(return_value=Response(200, json=forecast_payload))

    df = fetch_weather(
        lat=3.139,
        lon=101.6869,
        start=start,
        end=end,
        cache_db=tmp_path / "weather.duckdb",
    )

    assert archive_route.call_count == 1, "archive API must be called exactly once"
    assert forecast_route.call_count == 1, "forecast API must be called exactly once"
    assert len(df) == 48
    assert df["ts"].is_monotonic_increasing


# ── Test 4: Rate-limit raises OpenMeteoRateLimitError ────────────────────────


@respx.mock
def test_fetch_weather_raises_on_rate_limit(tmp_path: Path) -> None:
    """HTTP 429 from archive API must raise OpenMeteoRateLimitError."""
    from core.external.weather_openmeteo import OpenMeteoRateLimitError, fetch_weather

    respx.get(ARCHIVE_URL).mock(return_value=Response(429, text="Too Many Requests"))

    start = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2025, 1, 1, 5, 0, tzinfo=timezone.utc)

    with pytest.raises(OpenMeteoRateLimitError):
        fetch_weather(
            lat=3.139,
            lon=101.6869,
            start=start,
            end=end,
            cache_db=tmp_path / "weather.duckdb",
        )


# ── Test 5: Rounding consistency between COUNT queries and fetch_weather ───────


@respx.mock
def test_backfill_rounds_lat_lon_consistently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    _backfill must round lat/lon ONCE and use the same rounded key for both
    the COUNT-before / COUNT-after queries and the fetch_weather call.

    If the COUNT queries and fetch_weather use different keys, the reported
    new_rows count would be wrong (either 0 or a negative number).

    Regression test for fix #2: supply coordinates with sub-4dp noise
    (e.g. 3.13900001) to expose any mismatch.
    """
    import duckdb
    from core.external import weather_openmeteo
    from core.external.weather_openmeteo import _backfill, _COORD_PRECISION

    # Noisy coordinates that round to the same 4-dp values as the mock response
    noisy_lat = 3.13900001
    noisy_lon = 101.68690001

    # 4-hour window so mock payload is small
    hours = 4
    start_str = "2025-04-01"
    end_str = "2025-04-01"
    # _backfill sets end to hour=23, so expect 24 rows from the mock
    # but we only need the COUNT integrity — use 4h payload and let
    # fetch_weather filter; a full-day mock is simpler
    hours = 24
    payload = _make_hourly_response("2025-04-01T00:00", hours)
    respx.get(ARCHIVE_URL).mock(return_value=Response(200, json=payload))

    # Redirect settings so _backfill uses our noisy coords and tmp cache.
    # data_dir is a computed property so we patch _default_cache_db instead.
    monkeypatch.setattr(weather_openmeteo.settings, "hospital_lat", noisy_lat)
    monkeypatch.setattr(weather_openmeteo.settings, "hospital_lon", noisy_lon)
    cache_path = tmp_path / "weather_cache.duckdb"
    monkeypatch.setattr(weather_openmeteo, "_default_cache_db", lambda: cache_path)

    new_rows, total_rows = _backfill(start_str, end_str)

    # The number of new rows inserted must equal the total returned by fetch_weather
    # If rounding were inconsistent, new_rows would be 0 (COUNT keyed on wrong coord).
    assert total_rows == hours, f"expected {hours} total rows, got {total_rows}"
    assert new_rows == total_rows, (
        f"new_rows={new_rows} != total_rows={total_rows}; "
        "COUNT queries and fetch_weather used different lat/lon keys"
    )
