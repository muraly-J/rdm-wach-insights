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

Vercel Compatibility:
- In Vercel's read-only environment, logging is disabled gracefully
- Uses /tmp directory for writable storage when needed
"""

import sqlite3
import json
import os
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path


# Detect Vercel environment (read-only filesystem)
IN_VERCEL = os.getenv("VERCEL") == "1"

# Determine DB path based on environment
if IN_VERCEL:
    # In Vercel, use /tmp which is writable
    _DB_DIR = Path("/tmp/query_logger")
else:
    # In local/dev, use backend/data
    _DB_DIR = Path(__file__).parent.parent / "data"

_DB_PATH = _DB_DIR / "query_logs.db"


def _get_conn() -> Optional[sqlite3.Connection]:
    """Get database connection, returns None if not writable."""
    try:
        _DB_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        # In Vercel, this may fail on initial deploy before /tmp is ready
        print(f"[query_logger] Warning: Could not connect to database: {e}")
        return None


def init_db() -> bool:
    """
    Create the query_logs table if it doesn't exist.
    Returns True on success, False if database is not writable (Vercel).
    """
    try:
        conn = _get_conn()
        if conn is None:
            return False
        with conn:
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
        return True
    except Exception as e:
        print(f"[query_logger] Warning: Could not initialize database: {e}")
        return False


def log_query(
    *,
    session_id:       str,
    user_query:       str,
    structured_query: Optional[dict],
    execution_status: str,
    error_detail:     Optional[str] = None,
) -> Optional[int]:
    """
    Insert one log row. Returns the new row id.
    
    In Vercel (read-only), this function silently fails and returns None.
    
    execution_status should be one of:
      'success' | 'validation_error' | 'parse_error' | 'influx_error'
    """
    # Don't log in Vercel if database is not writable
    if IN_VERCEL:
        return None
    
    metric = structured_query.get("metric") if structured_query else None
    query_type = structured_query.get("query_type") if structured_query else None

    try:
        conn = _get_conn()
        if conn is None:
            return None
        with conn:
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
    except Exception as e:
        print(f"[query_logger] Warning: Could not log query: {e}")
        return None


def get_recent_logs(limit: int = 50) -> list[dict]:
    """Return the most recent log rows as dicts (for a future admin panel)."""
    try:
        conn = _get_conn()
        if conn is None:
            return []
        with conn:
            rows = conn.execute(
                "SELECT * FROM query_logs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"[query_logger] Warning: Could not fetch logs: {e}")
        return []


def get_rejected_queries(limit: int = 100) -> list[dict]:
    """
    Return queries that were rejected by validation or parse errors.
    Useful for iterative prompt improvement as recommended in PRD commentary.
    """
    try:
        conn = _get_conn()
        if conn is None:
            return []
        with conn:
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
    except Exception as e:
        print(f"[query_logger] Warning: Could not fetch rejected queries: {e}")
        return []
