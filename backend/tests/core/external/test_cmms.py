from __future__ import annotations

"""
tests/core/external/test_cmms.py
─────────────────────────────────
Unit tests for the CMMS event ingestion module.

Each test receives a fresh DuckDB cache via ``tmp_path`` — no real data/
directory is touched.
"""

import csv
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.external.cmms import APICMMSBackend, CMMSClient, CMMSValidationError, CSVCMMSBackend
from models.cmms_event import CMMSEvent


# ── Helpers ────────────────────────────────────────────────────────────────────


def _write_csv(path: Path, rows: list[dict]) -> Path:
    """Write a list of dicts to a CSV at *path* and return the path."""
    if not rows:
        raise ValueError("rows must not be empty")
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _make_rows(ahu_id: str = "e0101", count: int = 3, offset: int = 0) -> list[dict]:
    """Build *count* minimal valid CSV rows for *ahu_id*."""
    return [
        {
            "event_id": f"evt-{ahu_id}-{offset + i:04d}",
            "ahu_id": ahu_id,
            "ts": f"2026-01-{offset + i + 1:02d}T10:00:00",
            "event_type": "filter_change",
            "notes": f"note {i}",
            "source": "manual",
        }
        for i in range(count)
    ]


# ── Test 1: import inserts events ──────────────────────────────────────────────


def test_csv_import_inserts_events(tmp_path: Path) -> None:
    """
    Point at a tmp CSV with 3 events; import_csv returns 3 and
    events_for returns matching CMMSEvent instances.
    """
    csv_path = _write_csv(tmp_path / "events.csv", _make_rows("e0101", 3))
    backend = CSVCMMSBackend(cache_db=tmp_path / "cmms.duckdb")

    count = backend.import_csv(csv_path)

    assert count == 3, f"expected 3 new rows, got {count}"

    events = backend.events_for("e0101")
    assert len(events) == 3

    # Verify they are CMMSEvent instances with correct fields
    for event in events:
        assert isinstance(event, CMMSEvent)
        assert event.ahu_id == "e0101"
        assert event.event_type == "filter_change"
        assert event.source == "manual"

    # Timestamps are UTC-aware
    for event in events:
        assert event.ts.tzinfo is not None


# ── Test 2: import is idempotent ───────────────────────────────────────────────


def test_csv_import_is_idempotent(tmp_path: Path) -> None:
    """
    Calling import_csv twice on the same file returns 0 on the second call.
    """
    csv_path = _write_csv(tmp_path / "events.csv", _make_rows("e0202", 3))
    backend = CSVCMMSBackend(cache_db=tmp_path / "cmms.duckdb")

    first = backend.import_csv(csv_path)
    second = backend.import_csv(csv_path)

    assert first == 3, f"expected 3 new rows on first import, got {first}"
    assert second == 0, f"expected 0 new rows on second import, got {second}"

    # Total in cache still 3
    assert len(backend.events_for("e0202")) == 3


# ── Test 3: events_for filters by ahu_id ──────────────────────────────────────


def test_events_for_filters_by_ahu_id(tmp_path: Path) -> None:
    """
    CSV with events for 2 AHUs; querying each returns only matching events.
    """
    rows = _make_rows("e0101", 2) + _make_rows("e0202", 3, offset=10)
    csv_path = _write_csv(tmp_path / "events.csv", rows)

    backend = CSVCMMSBackend(cache_db=tmp_path / "cmms.duckdb")
    backend.import_csv(csv_path)

    events_0101 = backend.events_for("e0101")
    events_0202 = backend.events_for("e0202")

    assert len(events_0101) == 2
    assert all(e.ahu_id == "e0101" for e in events_0101)

    assert len(events_0202) == 3
    assert all(e.ahu_id == "e0202" for e in events_0202)


# ── Test 4: events_for filters by since ───────────────────────────────────────


def test_events_for_filters_by_since(tmp_path: Path) -> None:
    """
    Query with since= cutoff; only events with ts >= since are returned.
    """
    rows = [
        {
            "event_id": "evt-early",
            "ahu_id": "e0303",
            "ts": "2026-01-01T08:00:00",
            "event_type": "coil_clean",
            "notes": "",
            "source": "manual",
        },
        {
            "event_id": "evt-mid",
            "ahu_id": "e0303",
            "ts": "2026-03-15T12:00:00",
            "event_type": "planned_pm",
            "notes": "",
            "source": "manual",
        },
        {
            "event_id": "evt-late",
            "ahu_id": "e0303",
            "ts": "2026-06-01T00:00:00",
            "event_type": "belt_replace",
            "notes": "",
            "source": "manual",
        },
    ]
    csv_path = _write_csv(tmp_path / "events.csv", rows)

    backend = CSVCMMSBackend(cache_db=tmp_path / "cmms.duckdb")
    backend.import_csv(csv_path)

    cutoff = datetime(2026, 3, 1, tzinfo=timezone.utc)
    filtered = backend.events_for("e0303", since=cutoff)

    assert len(filtered) == 2, f"expected 2 events after cutoff, got {len(filtered)}"
    event_ids = {e.event_id for e in filtered}
    assert "evt-mid" in event_ids
    assert "evt-late" in event_ids
    assert "evt-early" not in event_ids


# ── Test 5: import rejects unknown event_type ─────────────────────────────────


def test_csv_import_rejects_unknown_event_type(tmp_path: Path) -> None:
    """
    A CSV containing event_type='lol' raises CMMSValidationError with a
    clear message that includes the bad value.
    """
    rows = [
        {
            "event_id": "evt-bad-001",
            "ahu_id": "e0101",
            "ts": "2026-01-01T09:00:00",
            "event_type": "lol",
            "notes": "",
            "source": "manual",
        }
    ]
    csv_path = _write_csv(tmp_path / "bad.csv", rows)
    backend = CSVCMMSBackend(cache_db=tmp_path / "cmms.duckdb")

    with pytest.raises(CMMSValidationError) as exc_info:
        backend.import_csv(csv_path)

    error_msg = str(exc_info.value)
    assert "lol" in error_msg, f"expected bad value 'lol' in error message: {error_msg}"
    assert exc_info.value.bad_value == "lol"


# ── Test 6: APICMMSBackend raises NotImplementedError ─────────────────────────


def test_api_backend_raises_not_implemented() -> None:
    """APICMMSBackend.events_for always raises NotImplementedError."""
    api_backend = APICMMSBackend()

    with pytest.raises(NotImplementedError):
        api_backend.events_for("e0101")


# ── Test 7: CMMSClient defaults to CSV backend ────────────────────────────────


def test_cmms_client_defaults_to_csv(tmp_path: Path) -> None:
    """
    CMMSClient(cache_db=...) with no backend kwarg uses CSVCMMSBackend.
    events_for returns an empty list (no data imported yet) — proves the
    CSV backend was used (no NotImplementedError).
    """
    client = CMMSClient(cache_db=tmp_path / "client.duckdb")

    # No events yet — should return empty list, not raise
    events = client.events_for("e0101")
    assert events == []

    # Internally, the backend should be a CSVCMMSBackend instance
    assert isinstance(client._backend, CSVCMMSBackend)


# ── Test 8: import handles missing optional columns gracefully ─────────────────


def test_csv_import_optional_columns_default(tmp_path: Path) -> None:
    """
    CSVs without 'notes' or 'source' columns should still import cleanly,
    defaulting notes to None and source to 'manual'.
    """
    rows = [
        {
            "event_id": "evt-minimal-001",
            "ahu_id": "e0505",
            "ts": "2026-02-14T14:00:00",
            "event_type": "other",
        }
    ]
    csv_path = _write_csv(tmp_path / "minimal.csv", rows)
    backend = CSVCMMSBackend(cache_db=tmp_path / "cmms.duckdb")

    count = backend.import_csv(csv_path)
    assert count == 1

    events = backend.events_for("e0505")
    assert len(events) == 1
    assert events[0].notes is None
    assert events[0].source == "manual"


# ── Test 9: import with timezone-aware timestamps ─────────────────────────────


def test_csv_import_timezone_aware_timestamps(tmp_path: Path) -> None:
    """
    Timezone-aware ISO 8601 timestamps (with +HH:MM offset) are parsed and
    returned as UTC-aware datetimes.
    """
    rows = [
        {
            "event_id": "evt-tz-001",
            "ahu_id": "e0606",
            "ts": "2026-04-01T08:00:00+08:00",  # MYT = UTC+8 → 00:00 UTC
            "event_type": "corrective_failure",
            "notes": "TZ-aware test",
            "source": "cmms_api",
        }
    ]
    csv_path = _write_csv(tmp_path / "tz.csv", rows)
    backend = CSVCMMSBackend(cache_db=tmp_path / "cmms.duckdb")
    backend.import_csv(csv_path)

    events = backend.events_for("e0606")
    assert len(events) == 1

    ts = events[0].ts
    assert ts.tzinfo is not None
    # UTC+8 08:00 → UTC 00:00
    assert ts.hour == 0
    assert ts.day == 1
    assert ts.month == 4


# ── Test 10: import rejects unparseable timestamp ─────────────────────────────


def test_csv_import_rejects_unparseable_timestamp(tmp_path: Path) -> None:
    """
    A CSV row with an unparseable timestamp value raises CMMSValidationError.
    The error message must include the offending raw value and the row_index
    must be 0 (zero-based, excluding the header).
    """
    csv = tmp_path / "bad_ts.csv"
    csv.write_text(
        "event_id,ahu_id,ts,event_type\n"
        "evt-1,e0101,not-a-real-timestamp,filter_change\n"
    )
    backend = CSVCMMSBackend(cache_db=tmp_path / "cache.duckdb")
    with pytest.raises(CMMSValidationError) as exc_info:
        backend.import_csv(csv)
    assert "not-a-real-timestamp" in str(exc_info.value)
    assert exc_info.value.row_index == 0
