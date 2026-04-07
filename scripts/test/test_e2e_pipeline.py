#!/usr/bin/env python3
"""
E2E pipeline smoke test: DuckDB → API → Dashboard → Chat

Validates the full data path without requiring InfluxDB to be live.
Uses existing DuckDB data and calls the running backend.

Usage:
    API_KEY=<your-key> python scripts/test/test_e2e_pipeline.py

Optional env vars:
    BACKEND_URL   default: http://localhost:8081
    API_KEY       default: (empty — will fail auth unless backend is in dev mode)
"""
import os
import sys
import pathlib

import requests

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8081")
API_KEY  = os.getenv("API_KEY", "")
HEADERS  = {"Authorization": f"Bearer {API_KEY}"}
DATA_DIR = pathlib.Path(__file__).parents[2] / "data"

GREEN = "\033[32m"
RED   = "\033[31m"
RESET = "\033[0m"
PASS  = f"{GREEN}PASS{RESET}"
FAIL  = f"{RED}FAIL{RESET}"


def check(name: str, condition: bool, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return condition


# ─────────────────────────────────────────────────────────────
# 1. DuckDB Integrity
# ─────────────────────────────────────────────────────────────
def test_csv_integrity() -> bool:
    print("\n=== 1. DuckDB Integrity ===")
    ok = True
    results = []

    # healthdb.duckdb: expect >100K rows in health_hourly table
    import duckdb as _duckdb
    db_path = DATA_DIR / "healthdb.duckdb"
    if db_path.exists():
        conn = _duckdb.connect(str(db_path), read_only=True)
        row_count = conn.execute("SELECT COUNT(*) FROM health_hourly").fetchone()[0]
        pred_count = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        col_names = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='health_hourly'"
        ).df()["column_name"].tolist()
        conn.close()
        results.append((row_count > 100_000, f"health_hourly has >100K rows (got {row_count})"))
        results.append((pred_count >= 100, f"predictions has >=100 rows (got {pred_count})"))
        results.append(("ahu_id" in col_names, "health_hourly has ahu_id column"))
    else:
        results.append((False, f"healthdb.duckdb not found at {db_path}"))

    for condition, detail in results:
        ok &= check(detail, condition)

    return ok


# ─────────────────────────────────────────────────────────────
# 2. Health Score API
# ─────────────────────────────────────────────────────────────
def test_health_endpoint() -> bool:
    print("\n=== 2. Health Score API (/api/level/1/scores) ===")
    try:
        r = requests.get(f"{BASE_URL}/api/level/1/scores", headers=HEADERS, timeout=15)
    except requests.ConnectionError:
        check("backend reachable", False, f"cannot connect to {BASE_URL}")
        return False

    ok = check("returns HTTP 200", r.status_code == 200, str(r.status_code))
    if not ok:
        return False

    data = r.json()
    ok &= check("response is a list", isinstance(data, list))
    ok &= check("list is non-empty", len(data) > 0, f"{len(data)} devices")

    if data:
        device = data[0]
        ok &= check("each device has health_index", "health_index" in device)
        hi = device.get("health_index", -1)
        ok &= check(
            "health_index is in 0–100",
            isinstance(hi, (int, float)) and 0 <= hi <= 100,
            str(hi)
        )
        ok &= check("each device has device_id", "device_id" in device)

    return ok


# ─────────────────────────────────────────────────────────────
# 3. Dashboard Trend API
# ─────────────────────────────────────────────────────────────
def test_dashboard_trend() -> bool:
    print("\n=== 3. Dashboard Trend API (/api/dashboard/trend) ===")
    try:
        r = requests.get(
            f"{BASE_URL}/api/dashboard/trend?level=1&range=7d",
            headers=HEADERS,
            timeout=15
        )
    except requests.ConnectionError:
        check("backend reachable", False)
        return False

    ok = check("returns HTTP 200", r.status_code == 200, str(r.status_code))
    if not ok:
        return False

    data = r.json()
    ok &= check("response has data points", isinstance(data, list) and len(data) > 0,
                f"{len(data)} points")
    return ok


# ─────────────────────────────────────────────────────────────
# 4. Predictions API
# ─────────────────────────────────────────────────────────────
def test_predictions_endpoint() -> bool:
    print("\n=== 4. Predictions API (/api/predictions/e0202) ===")
    try:
        r = requests.get(f"{BASE_URL}/api/predictions/e0202", headers=HEADERS, timeout=15)
    except requests.ConnectionError:
        check("backend reachable", False)
        return False

    ok = check("returns HTTP 200", r.status_code == 200, str(r.status_code))
    if not ok:
        return False

    data = r.json()
    ok &= check("response is a dict", isinstance(data, dict))
    # Accept either {predictions: {...}} shape or flat shape with at least one key
    ok &= check("response is non-empty", len(data) > 0, str(list(data.keys())[:4]))
    return ok


# ─────────────────────────────────────────────────────────────
# 5. Chat Endpoint with CSV Context
# ─────────────────────────────────────────────────────────────
def test_chat_with_csv_context() -> bool:
    print("\n=== 5. Chat Endpoint (POST /api/chat with level context) ===")
    payload = {
        "message": "What is the current health status of level 1?",
        "history": [],
        "context": {"level": 1}
    }
    try:
        r = requests.post(f"{BASE_URL}/api/chat", json=payload, headers=HEADERS, timeout=30)
    except requests.ConnectionError:
        check("backend reachable", False)
        return False

    ok = check("returns HTTP 200", r.status_code == 200, str(r.status_code))
    if not ok:
        return False

    body = r.json()
    ok &= check("response has reply field", "reply" in body)
    reply = body.get("reply", "")
    ok &= check("reply is a non-empty string", isinstance(reply, str) and len(reply) > 20,
                f"{len(reply)} chars")
    return ok


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Backend: {BASE_URL}")
    print(f"Auth:    {'set' if API_KEY else 'NOT SET — may fail auth'}")

    results = [
        test_csv_integrity(),
        test_health_endpoint(),
        test_dashboard_trend(),
        test_predictions_endpoint(),
        test_chat_with_csv_context(),
    ]

    passed = sum(results)
    total  = len(results)
    print(f"\n{'='*44}")
    print(f"Result: {passed}/{total} test groups passed")
    sys.exit(0 if all(results) else 1)
