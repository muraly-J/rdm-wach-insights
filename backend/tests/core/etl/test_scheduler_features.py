from __future__ import annotations

"""
tests/core/etl/test_scheduler_features.py
──────────────────────────────────────────
Unit tests for the async feature refresh loop and backfill CLI.

All tests mock external I/O (InfluxDB, open-meteo) — no live calls are made.

Patching strategy
-----------------
``scheduler_features`` uses lazy imports (inside function bodies) so that the
module itself carries no heavy dependencies at import time.  We therefore patch
at the *source* module level rather than at ``core.etl.scheduler_features.*``:

    core.etl.feature_builder.build_features     ← called by refresh/backfill
    core.external.weather_openmeteo.fetch_weather
    core.etl.telemetry_provider.InfluxTelemetryProvider
"""

import asyncio
import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from core.etl.scheduler_features import (
    _all_ahu_ids,
    _validate_ahu_ids,
    backfill,
    refresh_recent_features,
    start_feature_refresh_loop,
)


# ── Shared fixtures ────────────────────────────────────────────────────────────


def _make_fake_df(n_rows: int = 2) -> pd.DataFrame:
    """Return a minimal DataFrame with ``n_rows`` rows."""
    return pd.DataFrame({"ahu_id": ["e0101"] * n_rows, "ts": range(n_rows)})


def _make_weather() -> pd.DataFrame:
    """Minimal weather DataFrame accepted by build_features."""
    now = datetime(2026, 1, 1, 0, tzinfo=timezone.utc)
    hours = pd.date_range(start=now, periods=3, freq="h", tz="UTC")
    return pd.DataFrame({"ts": hours, "oat": [28.0] * 3, "oah": [80.0] * 3, "ghi": [0.0] * 3})


# ── Test 1: refresh_recent_features calls build_features for every AHU ────────


async def test_refresh_recent_features_calls_build_for_each_ahu():
    """build_features is called exactly once per AHU in AHU_LEVEL_CONFIG."""
    all_ids = _all_ahu_ids()
    assert len(all_ids) > 0, "AHU_LEVEL_CONFIG must contain at least one device"

    call_log: list[str] = []

    def fake_build(ahu_id, start, end, *, provider, weather, **kwargs):
        call_log.append(ahu_id)
        return _make_fake_df(1)

    fake_weather = _make_weather()

    with (
        patch("core.etl.feature_builder.build_features", side_effect=fake_build),
        patch("core.external.weather_openmeteo.fetch_weather", return_value=fake_weather),
        patch("core.etl.telemetry_provider.InfluxTelemetryProvider"),
    ):
        result = await refresh_recent_features(weather=fake_weather)

    assert len(call_log) == len(all_ids), (
        f"Expected {len(all_ids)} build_features calls, got {len(call_log)}"
    )
    assert set(call_log) == set(all_ids)
    assert len(result) == len(all_ids)


# ── Test 2: per-AHU errors are swallowed ──────────────────────────────────────


async def test_refresh_recent_features_swallows_per_ahu_errors():
    """A build_features error for one AHU is counted as 0; the loop continues for others."""
    all_ids = _all_ahu_ids()
    failing_ahu = all_ids[0]
    call_log: list[str] = []

    def fake_build(ahu_id, start, end, *, provider, weather, **kwargs):
        call_log.append(ahu_id)
        if ahu_id == failing_ahu:
            raise RuntimeError(f"Simulated failure for {ahu_id}")
        return _make_fake_df(3)

    fake_weather = _make_weather()

    with (
        patch("core.etl.feature_builder.build_features", side_effect=fake_build),
        patch("core.external.weather_openmeteo.fetch_weather", return_value=fake_weather),
        patch("core.etl.telemetry_provider.InfluxTelemetryProvider"),
    ):
        result = await refresh_recent_features(weather=fake_weather)

    # Every AHU was attempted — one failure does NOT short-circuit the others
    assert len(call_log) == len(all_ids), (
        f"Expected {len(all_ids)} calls, got {len(call_log)} — "
        "an AHU error must not stop the loop"
    )
    # The failing AHU yields 0
    assert result[failing_ahu] == 0
    # The rest yield 3
    for ahu_id in all_ids:
        if ahu_id != failing_ahu:
            assert result[ahu_id] == 3


# ── Test 3: weather errors halt the whole run ─────────────────────────────────


async def test_refresh_recent_features_halts_on_weather_error():
    """OpenMeteoError from fetch_weather propagates out — no per-AHU swallowing."""
    from core.external.weather_openmeteo import OpenMeteoError

    with (
        patch(
            "core.external.weather_openmeteo.fetch_weather",
            side_effect=OpenMeteoError(503, "Service Unavailable"),
        ),
        patch("core.etl.telemetry_provider.InfluxTelemetryProvider"),
        patch("core.etl.feature_builder.build_features") as mock_build,
    ):
        with pytest.raises(OpenMeteoError):
            await refresh_recent_features()

    # build_features must NOT have been called at all
    mock_build.assert_not_called()


# ── Test 4: start_feature_refresh_loop exits cleanly on CancelledError ────────


async def test_start_feature_refresh_loop_exits_on_cancel(caplog):
    """Cancelling the loop task raises CancelledError and emits no warning log."""
    sleep_started = asyncio.Event()

    async def mock_refresh_recent_features(**kwargs):
        return {}

    async def blocking_sleep(seconds):
        sleep_started.set()
        # Block until cancelled
        await asyncio.Event().wait()

    with (
        patch(
            "core.etl.scheduler_features.refresh_recent_features",
            side_effect=mock_refresh_recent_features,
        ),
        patch("asyncio.sleep", side_effect=blocking_sleep),
        caplog.at_level(logging.WARNING, logger="core.etl.scheduler_features"),
    ):
        task = asyncio.create_task(start_feature_refresh_loop())

        # Wait until the loop has started sleeping (i.e., first iteration done)
        try:
            await asyncio.wait_for(sleep_started.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pass  # still cancel even if event didn't fire

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    # No WARNING or higher logged on clean cancel
    warning_records = [
        r for r in caplog.records if r.levelno >= logging.WARNING
    ]
    assert warning_records == [], (
        f"Unexpected warning/error on cancel: {warning_records}"
    )


# ── Test 5: backfill validates AHU IDs ────────────────────────────────────────


def test_backfill_validates_ahu_ids():
    """Passing an unknown AHU ID causes SystemExit(1) before any build is attempted."""
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 1, 2, tzinfo=timezone.utc)

    with patch("core.etl.feature_builder.build_features") as mock_build:
        with pytest.raises(SystemExit) as exc_info:
            backfill(start, end, ahu_ids=["eXXXX"])

    assert exc_info.value.code == 1
    mock_build.assert_not_called()


def test_backfill_validates_ahu_ids_invalid_format():
    """Passing an ID with valid format but not in config also exits 1."""
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 1, 2, tzinfo=timezone.utc)

    with patch("core.etl.feature_builder.build_features") as mock_build:
        with pytest.raises(SystemExit) as exc_info:
            backfill(start, end, ahu_ids=["e9999"])  # valid format but not in config

    assert exc_info.value.code == 1
    mock_build.assert_not_called()


# ── Test 6: backfill returns correct row counts per AHU ───────────────────────


def test_backfill_returns_row_counts_per_ahu():
    """build_features returning N-row DataFrames → result dict has N for each AHU."""
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 1, 2, tzinfo=timezone.utc)
    # Use two real AHU IDs from AHU_LEVEL_CONFIG
    test_ids = ["e0101", "e0102"]
    expected_n = 5

    def fake_build(ahu_id, start, end, *, provider, weather, **kwargs):
        return _make_fake_df(expected_n)

    fake_weather = _make_weather()

    with (
        patch("core.etl.feature_builder.build_features", side_effect=fake_build),
        patch("core.external.weather_openmeteo.fetch_weather", return_value=fake_weather),
        patch("core.etl.telemetry_provider.InfluxTelemetryProvider"),
    ):
        result = backfill(start, end, ahu_ids=test_ids)

    assert result == {"e0101": expected_n, "e0102": expected_n}
