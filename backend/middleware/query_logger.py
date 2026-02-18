"""
middleware/query_logger.py
──────────────────────────
Logs every query attempt (including rejected ones) to a local SQLite database.

Table: query_logs
  id               INTEGER  PRIMARY KEY AUTOINCREMENT
  session_id       TEXT     — browser session identifier (passed from frontend)
  timestamp        TEXT     — ISO-8601 UTC
  user_query       TEXT     — raw natural language input
  structured_query TEXT     — JSON string of parsed query (null if parse failed)
  execution_status TEXT     — 'success' | 'validation_error' | 'parse_error' | 'influx_error'
  error_detail     TEXT     — error message if not success (null otherwise)
  metric           TEXT     — extracted metric (null if parse failed)
  query_type       TEXT     — 'time_series' | 'ranking' (null if parse failed)

The PRD commentary explicitly calls out logging rejected queries for iterative
improvement — this table makes that easy to query later.
"""

import sqlite3
import json
import os
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path


# DB lives at backend/data/query_logs.db — created automatically on first run
_DB_DIR  = Path(__file__).parent.parent / "data"
_DB_PATH = _DB_DIR / "query_logs.db"


def _get_conn() -> sqlite3.Connection:
    _DB_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the query_logs table if it doesn't exist. Call once at app startup."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id       TEXT,
                timestamp        TEXT NOT NULL,
                user_query       TEXT NOT NULL,
                structured_query TEXT,
                execution_status TEXT NOT NULL,
                error_detail     TEXT,
                metric           TEXT,
                query_type       TEXT
            )
        """)
        conn.commit()


def log_query(
    *,
    session_id:       str,
    user_query:       str,
    structured_query: Optional[dict],
    execution_status: str,
    error_detail:     Optional[str] = None,
) -> int:
    """
    Insert one log row. Returns the new row id.

    execution_status should be one of:
      'success' | 'validation_error' | 'parse_error' | 'influx_error'
    """
    metric     = structured_query.get("metric")     if structured_query else None
    query_type = structured_query.get("query_type") if structured_query else None

    with _get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO query_logs
                (session_id, timestamp, user_query, structured_query,
                 execution_status, error_detail, metric, query_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                datetime.now(timezone.utc).isoformat(),
                user_query,
                json.dumps(structured_query) if structured_query else None,
                execution_status,
                error_detail,
                metric,
                query_type,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_recent_logs(limit: int = 50) -> list[dict]:
    """Return the most recent log rows as dicts (for a future admin panel)."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM query_logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_rejected_queries(limit: int = 100) -> list[dict]:
    """
    Return queries that were rejected by validation or parse errors.
    Useful for iterative prompt improvement as recommended in PRD commentary.
    """
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM query_logs
            WHERE execution_status IN ('validation_error', 'parse_error')
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]