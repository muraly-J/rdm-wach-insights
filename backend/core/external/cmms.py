from __future__ import annotations

"""
core/external/cmms.py
─────────────────────
CMMS (Computerised Maintenance Management System) event ingestion.

Provides a thin facade (CMMSClient) over pluggable backends:

* CSVCMMSBackend — default; reads events from a DuckDB cache that is populated
  by importing CSV exports from the CMMS.
* APICMMSBackend — placeholder for a future HTTP-backed integration; raises
  NotImplementedError until the vendor API spec is finalised.

Public API
----------
    client = CMMSClient(cache_db=Path("data/cmms_events.duckdb"))
    events = client.events_for("e0101", since=datetime(2026, 1, 1, tzinfo=timezone.utc))

CSV import format
-----------------
Required columns: event_id, ahu_id, ts, event_type
Optional columns: notes, source  (defaults to "manual" when absent)

Timestamps:
    Parsed by pandas.  Timezone-aware values are stored as-is (converted to UTC
    internally).  Naive (timezone-unaware) timestamps are treated as UTC and a
    debug-level log message is emitted.  This matches the behaviour callers
    should expect from a facility CSV that doesn't embed TZ info.

Deduplication:
    event_id is the PRIMARY KEY in the DuckDB table.  INSERT OR IGNORE ensures
    idempotency — re-importing the same CSV never creates duplicate rows.

CLI
---
    python -m backend.core.external.cmms import data/cmms_export.csv [--db data/cmms_events.duckdb]
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import duckdb
import pandas as pd

from config import settings
from core.logger import get_logger
from models.cmms_event import VALID_EVENT_TYPES, CMMSEvent

logger = get_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

_SET_UTC = "SET TimeZone = 'UTC'"

# Inline DDL — mirrors backend/data/migrations/0001_cmms_events.duckdb.sql
_CACHE_DDL = """
CREATE TABLE IF NOT EXISTS cmms_events (
    event_id    TEXT PRIMARY KEY,
    ahu_id      TEXT NOT NULL,
    ts          TIMESTAMP NOT NULL,
    event_type  TEXT NOT NULL,
    notes       TEXT,
    source      TEXT NOT NULL DEFAULT 'manual'
);
CREATE INDEX IF NOT EXISTS idx_cmms_events_ahu_ts ON cmms_events (ahu_id, ts);
"""

# Columns required in the CSV
_REQUIRED_COLUMNS = {"event_id", "ahu_id", "ts", "event_type"}


# ── Exceptions ─────────────────────────────────────────────────────────────────


class CMMSValidationError(ValueError):
    """
    Raised when a CSV row cannot be mapped to a valid CMMSEvent.

    Attributes
    ----------
    row_index : int
        Zero-based CSV row index (excluding the header).
    bad_value : str
        The value that caused the rejection.
    message   : str
        Human-readable explanation.
    """

    def __init__(self, row_index: int, bad_value: str, message: str) -> None:
        super().__init__(message)
        self.row_index = row_index
        self.bad_value = bad_value


# ── Protocol (structural type for dependency injection) ────────────────────────


class CMMSBackend(Protocol):
    """Structural interface implemented by all CMMS backends."""

    def events_for(
        self, ahu_id: str, since: datetime | None = None
    ) -> list[CMMSEvent]: ...


# ── Helpers ────────────────────────────────────────────────────────────────────


def _default_cache_db() -> Path:
    return settings.data_dir / "cmms_events.duckdb"


def _init_cache(db_path: Path) -> None:
    """Ensure the cache table + index exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as conn:
        conn.execute(_SET_UTC)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cmms_events (
                event_id    TEXT PRIMARY KEY,
                ahu_id      TEXT NOT NULL,
                ts          TIMESTAMP NOT NULL,
                event_type  TEXT NOT NULL,
                notes       TEXT,
                source      TEXT NOT NULL DEFAULT 'manual'
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cmms_events_ahu_ts
            ON cmms_events (ahu_id, ts)
            """
        )


def _normalise_ts(ts: pd.Timestamp) -> datetime:
    """
    Convert a pandas Timestamp to a UTC-aware Python datetime.

    Naive timestamps are assumed to be UTC (documented behaviour).
    """
    if ts.tzinfo is None:
        logger.debug(
            "CMMS CSV: naive timestamp treated as UTC",
            extra={"ts": str(ts)},
        )
        return ts.to_pydatetime().replace(tzinfo=timezone.utc)
    return ts.to_pydatetime().astimezone(timezone.utc)


# ── CSV Backend ────────────────────────────────────────────────────────────────


class CSVCMMSBackend:
    """
    Reads and writes CMMS events through a DuckDB cache populated from CSV
    imports.

    Parameters
    ----------
    cache_db : Path, optional
        Path to the DuckDB cache file.  Defaults to
        ``settings.data_dir / "cmms_events.duckdb"``.
    """

    def __init__(self, cache_db: Path | None = None) -> None:
        self._db_path: Path = cache_db or _default_cache_db()
        _init_cache(self._db_path)

    # ── Public interface ───────────────────────────────────────────────────────

    def events_for(
        self, ahu_id: str, since: datetime | None = None
    ) -> list[CMMSEvent]:
        """
        Return all cached events for an AHU, optionally filtered to
        ``ts >= since``.

        Parameters
        ----------
        ahu_id : str
            AHU device identifier (e.g. ``"e0101"``).
        since  : datetime, optional
            If supplied, only events with ``ts >= since`` are returned.
            Naive datetimes are treated as UTC.

        Returns
        -------
        list[CMMSEvent]
            Events ordered by ``ts`` ascending.
        """
        if since is not None and since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)

        with duckdb.connect(str(self._db_path)) as conn:
            conn.execute(_SET_UTC)
            if since is not None:
                rows = conn.execute(
                    """
                    SELECT event_id, ahu_id, ts, event_type, notes, source
                    FROM   cmms_events
                    WHERE  ahu_id = ?
                      AND  ts >= ?
                    ORDER  BY ts
                    """,
                    [ahu_id, since],
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT event_id, ahu_id, ts, event_type, notes, source
                    FROM   cmms_events
                    WHERE  ahu_id = ?
                    ORDER  BY ts
                    """,
                    [ahu_id],
                ).fetchall()

        return [self._row_to_event(r) for r in rows]

    def import_csv(self, csv_path: Path) -> int:
        """
        Load events from a CSV file into the DuckDB cache.

        Parameters
        ----------
        csv_path : Path
            Path to the CSV file to import.

        Returns
        -------
        int
            Number of NEW rows inserted (idempotent — second call with the
            same file returns 0).

        Raises
        ------
        CMMSValidationError
            If any row contains an unrecognised ``event_type``.
        FileNotFoundError
            If ``csv_path`` does not exist.
        ValueError
            If a required column is missing from the CSV.
        """
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        df = pd.read_csv(csv_path)

        # Validate required columns
        missing_cols = _REQUIRED_COLUMNS - set(df.columns)
        if missing_cols:
            raise ValueError(
                f"CSV is missing required column(s): {sorted(missing_cols)}"
            )

        # Parse timestamps; errors='coerce' → NaT for unparseable values
        df["ts"] = pd.to_datetime(df["ts"], utc=False, errors="coerce")

        # Validate event_type values row by row
        for idx, row in df.iterrows():
            et = str(row["event_type"])
            if et not in VALID_EVENT_TYPES:
                raise CMMSValidationError(
                    row_index=int(idx),
                    bad_value=et,
                    message=(
                        f"Row {idx}: unknown event_type {et!r}. "
                        f"Valid values are: {sorted(VALID_EVENT_TYPES)}"
                    ),
                )

        # Fill optional columns
        if "notes" not in df.columns:
            df["notes"] = None
        if "source" not in df.columns:
            df["source"] = "manual"

        # Replace empty strings in notes/source with appropriate defaults
        df["notes"] = df["notes"].where(df["notes"].notna() & (df["notes"] != ""), None)
        df["source"] = df["source"].fillna("manual").replace("", "manual")

        # Normalise timestamps to UTC-aware datetimes then store as naive UTC
        # (DuckDB TIMESTAMP without timezone; we always SET TimeZone='UTC')
        normalised_ts = []
        for ts_val in df["ts"]:
            if pd.isna(ts_val):
                normalised_ts.append(None)
            else:
                normalised_ts.append(_normalise_ts(ts_val))
        df["ts"] = normalised_ts

        # Prepare insert DataFrame
        insert_df = df[["event_id", "ahu_id", "ts", "event_type", "notes", "source"]].copy()
        insert_df["event_id"] = insert_df["event_id"].astype(str)
        insert_df["ahu_id"] = insert_df["ahu_id"].astype(str)
        insert_df["event_type"] = insert_df["event_type"].astype(str)
        insert_df["source"] = insert_df["source"].astype(str)

        with duckdb.connect(str(self._db_path)) as conn:
            conn.execute(_SET_UTC)

            before = conn.execute("SELECT COUNT(*) FROM cmms_events").fetchone()[0]

            conn.execute(
                """
                INSERT OR IGNORE INTO cmms_events
                    (event_id, ahu_id, ts, event_type, notes, source)
                SELECT
                    event_id,
                    ahu_id,
                    ts::TIMESTAMP,
                    event_type,
                    notes,
                    source
                FROM insert_df
                """
            )

            after = conn.execute("SELECT COUNT(*) FROM cmms_events").fetchone()[0]

        new_rows = after - before
        logger.info(
            "CMMS CSV import complete",
            extra={
                "csv_path": str(csv_path),
                "new_rows": new_rows,
                "total_rows": after,
            },
        )
        return new_rows

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_event(row: tuple) -> CMMSEvent:
        """Convert a DuckDB result row to a CMMSEvent."""
        event_id, ahu_id, ts, event_type, notes, source = row

        # Normalise DuckDB-returned timestamp to UTC-aware datetime
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)
        else:
            # Fallback: attempt pandas coercion
            ts = _normalise_ts(pd.Timestamp(ts))

        return CMMSEvent(
            event_id=str(event_id),
            ahu_id=str(ahu_id),
            ts=ts,
            event_type=event_type,  # type: ignore[arg-type]
            notes=notes if notes is not None else None,
            source=str(source),
        )


# ── API Backend (placeholder) ──────────────────────────────────────────────────


class APICMMSBackend:
    """
    HTTP-backed CMMS adapter — not yet implemented.

    Placeholder until the vendor API specification is finalised.
    Raises NotImplementedError on every call.
    """

    def events_for(
        self, ahu_id: str, since: datetime | None = None
    ) -> list[CMMSEvent]:
        raise NotImplementedError("APICMMSBackend pending vendor API spec")


# ── Facade ─────────────────────────────────────────────────────────────────────


class CMMSClient:
    """
    Default-CSV facade.  Auto-selects the CSV backend; callers may inject
    an alternative backend for testing or future API integration.

    Parameters
    ----------
    backend  : CMMSBackend, optional
        Custom backend.  When ``None``, a ``CSVCMMSBackend`` is constructed
        using ``cache_db``.
    cache_db : Path, optional
        Passed to ``CSVCMMSBackend`` when ``backend`` is ``None``.
        Defaults to ``settings.data_dir / "cmms_events.duckdb"``.
    """

    def __init__(
        self,
        backend: CMMSBackend | None = None,
        cache_db: Path | None = None,
    ) -> None:
        self._backend: CMMSBackend = (
            backend if backend is not None else CSVCMMSBackend(cache_db)
        )

    def events_for(
        self, ahu_id: str, since: datetime | None = None
    ) -> list[CMMSEvent]:
        """
        Return events for an AHU, optionally filtered to ``ts >= since``.

        Delegates directly to the configured backend.
        """
        return self._backend.events_for(ahu_id, since=since)


# ── CLI ────────────────────────────────────────────────────────────────────────


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="CMMS event ingestion CLI",
        prog="python -m backend.core.external.cmms",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Import events from a CSV file")
    import_parser.add_argument(
        "csv_path",
        metavar="CSV_PATH",
        help="Path to the CMMS CSV export file",
    )
    import_parser.add_argument(
        "--db",
        metavar="DB_PATH",
        default=None,
        help="Path to the DuckDB cache file (default: data/cmms_events.duckdb)",
    )

    args = parser.parse_args()

    if args.command == "import":
        csv_path = Path(args.csv_path)
        db_path = Path(args.db) if args.db else None

        try:
            backend = CSVCMMSBackend(cache_db=db_path)
            new_rows = backend.import_csv(csv_path)
        except FileNotFoundError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        except (CMMSValidationError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        print(f"Imported {new_rows} new CMMS event(s) from {csv_path}.")

    return 0


if __name__ == "__main__":
    sys.exit(_main())
