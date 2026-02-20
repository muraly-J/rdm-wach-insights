"""
Test script for Stage 2 — Middleware & Safety Layer
Run from the backend/ directory: python3 middleware_test.py
"""

import sys
import os
# Add the project root to sys.path so 'models' can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(__file__))

from backend.middleware.validator import validate_raw_dict
from backend.middleware.query_logger import init_db, log_query, get_rejected_queries

print("\n" + "="*55)
print(" WACH INSIGHT - MIDDLEWARE TEST ".center(55, "="))
print("="*55)

# ── Initialise the SQLite DB ───────────────────────────────────────────────────
print("\n[Setup] Initialising query log database...")
init_db()
print("✅ DB initialised (backend/data/query_logs.db created)")


# ── Test 1: Valid time-series query ───────────────────────────────────────────
print("\n[Test 1] Valid time-series query...")
query, result = validate_raw_dict({
    "query_type": "time_series",
    "device_ids": ["e0101"],
    "metric": "power_total",
    "time_range": "last_7d",
})
assert result.is_valid, f"Expected valid, got: {result.errors}"
print("✅ Accepted — valid time-series query passes through")

log_query(session_id="test-session", user_query="show e0101 power for last 7 days",
          structured_query=query.model_dump(), execution_status="success")


# ── Test 2: Invalid metric ─────────────────────────────────────────────────────
print("\n[Test 2] Query with unsupported metric...")
query2, result2 = validate_raw_dict({
    "query_type": "time_series",
    "device_ids": ["e0101"],
    "metric": "temperature",       # ← not in whitelist
    "time_range": "last_24h",
})
assert not result2.is_valid, "Expected invalid"
print(f"✅ Rejected — {result2.user_message}")

log_query(session_id="test-session", user_query="show e0101 temperature",
          structured_query=None, execution_status="validation_error",
          error_detail=result2.user_message)


# ── Test 3: Unknown device ID ──────────────────────────────────────────────────
print("\n[Test 3] Query with unknown device ID...")
query3, result3 = validate_raw_dict({
    "query_type": "time_series",
    "device_ids": ["e9999"],       # ← not in WACH ward
    "metric": "power_total",
    "time_range": "last_24h",
})
assert not result3.is_valid, "Expected invalid"
print(f"✅ Rejected — {result3.user_message}")

log_query(session_id="test-session", user_query="show e9999 power",
          structured_query=None, execution_status="validation_error",
          error_detail=result3.user_message)


# ── Test 4: Invalid time range ─────────────────────────────────────────────────
print("\n[Test 4] Query with unsupported time range...")
query4, result4 = validate_raw_dict({
    "query_type": "time_series",
    "device_ids": ["e0206"],
    "metric": "energy_import",
    "time_range": "last_6_months",  # ← not supported
})
assert not result4.is_valid, "Expected invalid"
print(f"✅ Rejected — {result4.user_message}")


# ── Test 5: Valid ranking query ────────────────────────────────────────────────
print("\n[Test 5] Valid ranking query...")
query5, result5 = validate_raw_dict({
    "query_type": "ranking",
    "device_ids": [],
    "metric": "power_total",
    "time_range": "last_30d",
    "top_n": 10,
})
assert result5.is_valid, f"Expected valid, got: {result5.errors}"
print("✅ Accepted — valid ranking query passes through")
if result5.warnings:
    print(f"   ⚠️  Warnings: {result5.warnings}")

log_query(session_id="test-session", user_query="rank top 10 devices by power this month",
          structured_query=query5.model_dump(), execution_status="success")


# ── Test 6: Malformed dict (simulates bad LLM output) ─────────────────────────
print("\n[Test 6] Malformed LLM output (missing required fields)...")
query6, result6 = validate_raw_dict({
    "query_type": "ranking",
    # missing: device_ids, metric, time_range
})
assert not result6.is_valid, "Expected invalid"
print(f"✅ Rejected — parse error caught cleanly")

log_query(session_id="test-session", user_query="rank devices",
          structured_query=None, execution_status="parse_error",
          error_detail=result6.user_message)


# ── Check rejected query log ───────────────────────────────────────────────────
print("\n[Summary] Rejected queries in log:")
rejected = get_rejected_queries()
for row in rejected:
    print(f"   • [{row['execution_status']}] \"{row['user_query']}\" — {row['error_detail'][:60] if row['error_detail'] else 'n/a'}")

print("\n" + "="*55)
print(" ALL MIDDLEWARE TESTS PASSED ".center(55, "="))
print("="*55 + "\n")