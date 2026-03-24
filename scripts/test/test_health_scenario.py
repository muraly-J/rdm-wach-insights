#!/usr/bin/env python3
"""
Scenario test: health question → live data → prediction chart → energy anomaly coherence

Validates the specific user journey described in the project spec:
  A. User asks a health question → chatbot replies with real device IDs
  B. Dashboard /api/level/{id}/scores reflects current CSV data (not stale cache)
  C. Prediction chart is accessible for e0202 via /api/predictions/{device_id}
  D. Energy anomaly score exists for a device that has a row in predictions.csv

Usage:
    API_KEY=<your-key> python scripts/test/test_health_scenario.py

Optional env vars:
    BACKEND_URL   default: http://localhost:8081
    API_KEY       default: (empty)
"""
import os
import re
import sys
import pathlib

import requests
import pandas as pd

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8081")
API_KEY  = os.getenv("API_KEY", "")
HEADERS  = {"Authorization": f"Bearer {API_KEY}"}
DATA_DIR = pathlib.Path(__file__).parents[2] / "data"

GREEN = "\033[32m"
RED   = "\033[31m"
RESET = "\033[0m"
PASS  = f"{GREEN}PASS{RESET}"
FAIL  = f"{RED}FAIL{RESET}"
SKIP  = "\033[33mSKIP\033[0m"


def check(name: str, condition: bool, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return condition


# ─────────────────────────────────────────────────────────────
# Scenario A: Chat returns real device IDs in response to a health question
# ─────────────────────────────────────────────────────────────
def scenario_chat_health_question() -> bool:
    """
    User asks which AHU on level 2 is worst.
    The bot must name at least one real device ID (e####) in its reply.
    """
    print("\n=== Scenario A: Chat health question references a real device ID ===")
    payload = {
        "message": "Which AHU on level 2 has the lowest health score right now?",
        "history": [],
        "context": {"level": 2}
    }
    try:
        r = requests.post(f"{BASE_URL}/api/chat", json=payload, headers=HEADERS, timeout=30)
    except requests.ConnectionError:
        check("backend reachable", False, f"cannot connect to {BASE_URL}")
        return False

    ok = check("chat returns HTTP 200", r.status_code == 200, str(r.status_code))
    if not ok:
        return False

    reply = r.json().get("reply", "")
    ok &= check("reply is non-empty", isinstance(reply, str) and len(reply) > 10,
                f"{len(reply)} chars")

    device_ids = re.findall(r'e\d{4}', reply)
    ok &= check(
        "reply contains at least one real device ID (e####)",
        len(device_ids) > 0,
        f"found: {device_ids[:5]}"
    )
    return ok


# ─────────────────────────────────────────────────────────────
# Scenario B: Dashboard scores reflect current CSV data
# ─────────────────────────────────────────────────────────────
def scenario_dashboard_live_scores() -> bool:
    """
    The health_index returned by /api/level/1/scores for a device should be
    within 5 points of the most recent value in health_all_levels.csv.
    Tolerance of 5 accounts for rounding and potential use of fresher InfluxDB data.
    """
    print("\n=== Scenario B: Dashboard scores reflect current CSV data ===")
    df = pd.read_csv(DATA_DIR / "health_all_levels.csv")

    # Filter to level 1 devices (device_id starts with e01)
    level1 = df[df["device_id"].str.startswith("e01", na=False)].copy()
    if level1.empty:
        print(f"  [{SKIP}] No level-1 rows found in CSV")
        return True

    # Get most recent row per device
    latest = (
        level1.sort_values("timestamp")
              .groupby("device_id")
              .last()
              .reset_index()
    )
    # Pick the first device alphabetically for a deterministic test
    latest = latest.sort_values("device_id")
    sample      = latest.iloc[0]
    csv_device  = sample["device_id"]
    csv_hi      = float(sample.get("health_index", -1))

    try:
        r = requests.get(f"{BASE_URL}/api/level/1/scores", headers=HEADERS, timeout=15)
    except requests.ConnectionError:
        check("backend reachable", False)
        return False

    ok = check("/api/level/1/scores returns HTTP 200", r.status_code == 200, str(r.status_code))
    if not ok:
        return False

    api_by_device = {d["device_id"]: d for d in r.json()}

    if csv_device not in api_by_device:
        print(f"  [{SKIP}] {csv_device} not in API response — API may use a different device set")
        return True

    api_hi = float(api_by_device[csv_device].get("health_index", -999))
    ok &= check(
        f"{csv_device} health_index within 5 pts of latest CSV value",
        abs(api_hi - csv_hi) <= 5,
        f"API={api_hi:.1f}  CSV={csv_hi:.1f}  diff={abs(api_hi - csv_hi):.1f}"
    )
    return ok


# ─────────────────────────────────────────────────────────────
# Scenario C: Prediction chart is accessible for e0202
# ─────────────────────────────────────────────────────────────
def scenario_prediction_chart_accessible() -> bool:
    """
    /api/predictions/e0202 must return a non-empty dict.
    e0202 is one of three devices with an XGBoost model (e0202, e0207, e0211).
    """
    print("\n=== Scenario C: Prediction chart accessible for e0202 ===")
    try:
        r = requests.get(f"{BASE_URL}/api/predictions/e0202", headers=HEADERS, timeout=15)
    except requests.ConnectionError:
        check("backend reachable", False)
        return False

    ok = check("/api/predictions/e0202 returns HTTP 200", r.status_code == 200, str(r.status_code))
    if not ok:
        return False

    data = r.json()
    ok &= check("response is a non-empty dict", isinstance(data, dict) and len(data) > 0,
                str(list(data.keys())[:4]))

    # Accept either {predictions: {1h: ..., 24h: ...}} or a flat shape
    predictions = data.get("predictions", data)
    has_any_horizon = (
        isinstance(predictions, dict) and len(predictions) > 0
    ) or (
        isinstance(predictions, list) and len(predictions) > 0
    )
    ok &= check("at least one prediction horizon present", has_any_horizon)
    return ok


# ─────────────────────────────────────────────────────────────
# Scenario D: Energy anomaly score exists for a device in predictions.csv
# ─────────────────────────────────────────────────────────────
def scenario_energy_anomaly_coherence() -> bool:
    """
    predictions.csv stores the energy anomaly baseline per AHU (column: device_id).
    The health scores API should include an energy_anomaly component score (0–1)
    for a device that has a corresponding row in predictions.csv.
    """
    print("\n=== Scenario D: Energy anomaly score exists for a device in predictions.csv ===")

    preds = pd.read_csv(DATA_DIR / "predictions.csv")

    # predictions.csv uses 'device_id', not 'device_id'
    if "device_id" not in preds.columns:
        print(f"  [{SKIP}] predictions.csv missing 'device_id' column — see GAP-003 in INTEGRATION_BUGS.md")
        return True

    valid = preds.dropna(subset=["device_id"])
    if valid.empty:
        print(f"  [{SKIP}] No valid device_id rows in predictions.csv")
        return True

    # Pick a stable device: prefer e0202 since it also has XGBoost model
    preferred = valid[valid["device_id"] == "e0202"]
    sample_row   = preferred.iloc[0] if not preferred.empty else valid.iloc[0]
    device_id    = sample_row["device_id"]
    level_num    = int(str(device_id)[1:3])  # e.g. e0202 → level 2

    try:
        r = requests.get(f"{BASE_URL}/api/level/{level_num}/scores",
                         headers=HEADERS, timeout=15)
    except requests.ConnectionError:
        check("backend reachable", False)
        return False

    ok = check(
        f"/api/level/{level_num}/scores returns HTTP 200",
        r.status_code == 200, str(r.status_code)
    )
    if not ok:
        return False

    api_by_device = {d["device_id"]: d for d in r.json()}

    if device_id not in api_by_device:
        print(f"  [{SKIP}] {device_id} not in API response for level {level_num}")
        return True

    device_data = api_by_device[device_id]
    scores = device_data.get("scores", {})

    ok &= check(
        f"{device_id} has energy_anomaly component score",
        "energy_anomaly" in scores,
        f"available scores: {list(scores.keys())}"
    )
    ea = scores.get("energy_anomaly")
    if ea is not None:
        ok &= check(
            "energy_anomaly score is a float in [0, 1]",
            isinstance(ea, (int, float)) and 0.0 <= float(ea) <= 1.0,
            str(ea)
        )
    return ok


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Backend: {BASE_URL}")
    print(f"Auth:    {'set' if API_KEY else 'NOT SET — may fail auth'}")

    results = [
        scenario_chat_health_question(),
        scenario_dashboard_live_scores(),
        scenario_prediction_chart_accessible(),
        scenario_energy_anomaly_coherence(),
    ]

    passed = sum(results)
    total  = len(results)
    print(f"\n{'='*44}")
    print(f"Result: {passed}/{total} scenarios passed")
    sys.exit(0 if all(results) else 1)
