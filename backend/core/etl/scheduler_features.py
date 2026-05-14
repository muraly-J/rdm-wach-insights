from __future__ import annotations

"""
core/etl/scheduler_features.py
────────────────────────────────
Async feature refresh loop and CLI backfill tool for WACH Insight.

Public API
----------
    refresh_recent_features(*, hours_back, provider, weather) -> dict[str, int]
    start_feature_refresh_loop() -> None          (asyncio background task)
    backfill(start, end, ahu_ids) -> dict[str, int]  (CLI entrypoint)

Cadence rationale
-----------------
The plan originally called for APScheduler with an "HH:05" hourly schedule.
This codebase does NOT use APScheduler — ``backend/core/watchman.py`` uses a
plain asyncio loop registered in the FastAPI lifespan (see ``backend/main.py``).

We match that pattern:
- Interval-based polling every ``settings.feature_refresh_interval_seconds``
  (default 300 s / 5 min).
- Rolling window of ``hours_back=2`` hours re-processed each run.

Benefits over a fixed-clock scheduler:
1. No additional dependency (no APScheduler, no Celery).
2. Resilient: if one run fails, the next still covers the missed window because
   the 2-hour window overlaps the previous run's range.
3. Idempotent: ``build_features`` uses DuckDB ``INSERT OR IGNORE`` — re-running
   on an already-persisted (ahu_id, ts) pair is a no-op.

Error policy
------------
- Per-AHU errors (e.g. bad telemetry from one device) are caught, logged, and
  counted as 0 rows — one AHU failing does NOT stop others.
- Weather fetch errors halt the entire run.  Partial completion when weather is
  unavailable would silently persist features with NaN oat/oah/ghi, which would
  corrupt downstream models.  A logged error + skip-this-run is the safer choice.

CLI usage
---------
    python -m backend.core.etl.scheduler_features backfill \\
        --start 2025-01-01 --end 2026-05-13
    python -m backend.core.etl.scheduler_features backfill \\
        --start 2025-01-01 --end 2026-05-13 --ahu e0101 --ahu e0507
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd

from core.etl.telemetry_provider import RawTelemetryProvider
from core.external.weather_openmeteo import OpenMeteoError
from core.logger import get_logger

logger = get_logger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _all_ahu_ids() -> list[str]:
    """Return all valid AHU IDs from AHU_LEVEL_CONFIG, sorted."""
    from models.schemas import AHU_LEVEL_CONFIG  # noqa: PLC0415

    ids: list[str] = []
    for level_conf in AHU_LEVEL_CONFIG.values():
        ids.extend(level_conf["device_ids"])
    return sorted(set(ids))


def _validate_ahu_ids(ahu_ids: list[str]) -> None:
    """Raise SystemExit(1) if any ID is not in AHU_LEVEL_CONFIG."""
    from models.schemas import AHU_LEVEL_CONFIG  # noqa: PLC0415

    valid: set[str] = set()
    for level_conf in AHU_LEVEL_CONFIG.values():
        valid.update(level_conf["device_ids"])

    bad = [a for a in ahu_ids if a not in valid]
    if bad:
        print(
            f"ERROR: unknown AHU ID(s): {bad}.\n"
            "Only IDs present in AHU_LEVEL_CONFIG are accepted.",
            file=sys.stderr,
        )
        sys.exit(1)


# ── Core refresh logic ─────────────────────────────────────────────────────────


async def refresh_recent_features(
    *,
    hours_back: int = 2,
    provider: RawTelemetryProvider | None = None,
    weather: pd.DataFrame | None = None,
) -> dict[str, int]:
    """Refresh features for the trailing ``hours_back`` window for every AHU.

    Parameters
    ----------
    hours_back : int
        How far back (in hours) from *now* to recompute features.
        Default 2 h so a single failed run is automatically re-covered on the
        next poll cycle (with ``feature_refresh_interval_seconds=300``).
    provider : RawTelemetryProvider, optional
        Telemetry source.  Defaults to ``InfluxTelemetryProvider()``.
    weather : pd.DataFrame, optional
        Pre-fetched weather for the window (columns ts/oat/oah/ghi).
        When ``None``, ``weather_openmeteo.fetch_weather`` is called once for
        the entire window and reused across all AHUs.

    Returns
    -------
    dict[str, int]
        ``{ahu_id: rows_persisted}``.  AHUs that error are reported as 0.

    Raises
    ------
    OpenMeteoError
        If the weather fetch fails.  One failure halts the whole run —
        partial completion would silently persist NaN weather columns.
    """
    from config import settings  # noqa: PLC0415
    from core.etl.feature_builder import build_features  # noqa: PLC0415
    from core.etl.telemetry_provider import InfluxTelemetryProvider  # noqa: PLC0415
    from core.external.weather_openmeteo import fetch_weather  # noqa: PLC0415

    now = datetime.now(tz=timezone.utc)
    end = now.replace(minute=0, second=0, microsecond=0)  # floor to current hour
    start = end - timedelta(hours=hours_back)

    _provider = provider if provider is not None else InfluxTelemetryProvider()

    # Fetch weather once for all AHUs — halt on error
    if weather is None:
        weather = fetch_weather(
            settings.hospital_lat,
            settings.hospital_lon,
            start,
            end,
        )

    ahu_ids = _all_ahu_ids()
    results: dict[str, int] = {}

    for ahu_id in ahu_ids:
        try:
            df = build_features(
                ahu_id,
                start,
                end,
                provider=_provider,
                weather=weather,
            )
            results[ahu_id] = len(df)
        except Exception as exc:
            logger.error(
                "feature_refresh: AHU %s failed — %s",
                ahu_id,
                exc,
                exc_info=True,
            )
            results[ahu_id] = 0

    total = sum(results.values())
    successful = sum(1 for v in results.values() if v > 0)
    logger.info(
        "feature_refresh: complete — %d/%d AHUs succeeded, %d total rows",
        successful,
        len(ahu_ids),
        total,
    )
    return results


# ── Background loop ────────────────────────────────────────────────────────────


async def start_feature_refresh_loop() -> None:
    """Asyncio background loop. Run via ``asyncio.create_task()`` in FastAPI lifespan.

    Calls ``refresh_recent_features()`` every
    ``settings.feature_refresh_interval_seconds`` seconds (default 300 s).
    Exits cleanly on ``asyncio.CancelledError`` — no warning log on cancel,
    mirroring the ``start_pulse`` pattern in ``core/watchman.py``.
    """
    from config import settings  # noqa: PLC0415

    interval = settings.feature_refresh_interval_seconds
    logger.info(
        "feature_refresh: background loop started (interval=%ds, hours_back=2)",
        interval,
    )

    while True:
        try:
            await refresh_recent_features()
        except Exception as exc:
            logger.error("feature_refresh: loop iteration error — %s", exc, exc_info=True)
        await asyncio.sleep(interval)


# ── CLI backfill ───────────────────────────────────────────────────────────────


def backfill(
    start: datetime,
    end: datetime,
    ahu_ids: list[str] | None = None,
) -> dict[str, int]:
    """CLI entrypoint. Build features for [start, end] for the given AHUs.

    Parameters
    ----------
    start, end : datetime
        Inclusive start and exclusive end in UTC.
    ahu_ids : list[str], optional
        Specific AHU IDs to process.  Defaults to all IDs in AHU_LEVEL_CONFIG.

    Returns
    -------
    dict[str, int]
        ``{ahu_id: rows_persisted}``.

    Raises
    ------
    SystemExit(1)
        On invalid AHU IDs or weather fetch failure.
    """
    from config import settings  # noqa: PLC0415
    from core.etl.feature_builder import build_features  # noqa: PLC0415
    from core.etl.telemetry_provider import InfluxTelemetryProvider  # noqa: PLC0415
    from core.external.weather_openmeteo import fetch_weather  # noqa: PLC0415

    target_ids = ahu_ids if ahu_ids is not None else _all_ahu_ids()

    # Validate every requested AHU ID
    _validate_ahu_ids(target_ids)

    # Normalise timestamps to UTC
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    provider = InfluxTelemetryProvider()

    # Fetch weather once for the full range
    try:
        weather = fetch_weather(
            settings.hospital_lat,
            settings.hospital_lon,
            start,
            end,
        )
    except OpenMeteoError as exc:
        print(f"ERROR: weather fetch failed — {exc}", file=sys.stderr)
        sys.exit(1)

    results: dict[str, int] = {}
    for ahu_id in target_ids:
        try:
            df = build_features(
                ahu_id,
                start,
                end,
                provider=provider,
                weather=weather,
            )
            results[ahu_id] = len(df)
            logger.info("backfill: %s → %d rows", ahu_id, len(df))
        except Exception as exc:
            logger.error("backfill: AHU %s failed — %s", ahu_id, exc, exc_info=True)
            results[ahu_id] = 0

    total = sum(results.values())
    print(f"Backfill complete: {len(target_ids)} AHUs, {total} total rows persisted.")
    return results


# ── CLI entry point ────────────────────────────────────────────────────────────


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m backend.core.etl.scheduler_features",
        description="WACH Insight AHU feature backfill CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    bf = sub.add_parser("backfill", help="Backfill features for a date range")
    bf.add_argument(
        "--start",
        required=True,
        type=lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc),
        help="Start datetime ISO format (e.g. 2025-01-01 or 2025-01-01T00:00:00)",
    )
    bf.add_argument(
        "--end",
        required=True,
        type=lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc),
        help="End datetime ISO format (inclusive; one hour past this is used as exclusive end)",
    )
    bf.add_argument(
        "--ahu",
        dest="ahu_ids",
        action="append",
        default=None,
        metavar="AHU_ID",
        help="AHU ID to process (repeatable; default: all AHUs)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.command == "backfill":
        backfill(args.start, args.end, args.ahu_ids)


if __name__ == "__main__":
    main()
