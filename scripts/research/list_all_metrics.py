"""One-off: enumerate all InfluxDB metrics from codebase definitions.

Since the remote InfluxDB may be slow/unavailable, this extracts the
authoritative metric catalog from models/schemas.py ALLOWED_METRICS_WITH_UNITS
and cross-references with influx_client.py measurement patterns.

Output: CSV to stdout and /tmp/metrics.csv
Columns: metric_name, unit, description, influx_measurement_pattern, used_by_scores

Usage:
    cd backend && python3 ../scripts/research/list_all_metrics.py
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from models.schemas import (
    AHU_LEVEL_CONFIG,
    ALLOWED_DEVICES,
    ALLOWED_METRICS,
    ALLOWED_METRICS_WITH_UNITS,
)

OUTPUT = "/tmp/metrics.csv"

# FAIR scoring components and which raw metrics they consume
FAIR_METRIC_CONSUMERS = {
    "power_total": ["energy_anomaly(overload)", "overload"],
    "energy_import": ["energy_anomaly"],
    "power_factor_avg": ["power_factor"],
    "current_unbalance": ["phase_imbalance"],
    "current_l1_thd": ["thd_drift"],
    "current_l3_thd": ["thd_drift"],
}


def main() -> int:
    print("[metrics] Building metric inventory from codebase definitions")
    print(f"[metrics] Total allowed metrics: {len(ALLOWED_METRICS)}")
    print(f"[metrics] Total allowed devices: {len(ALLOWED_DEVICES)}")
    print(f"[metrics] Total levels: {len(AHU_LEVEL_CONFIG)}")

    # Count devices per level
    for level, config in sorted(AHU_LEVEL_CONFIG.items()):
        print(f"  Level {level}: {len(config['device_ids'])} devices")

    rows = []
    for metric in sorted(ALLOWED_METRICS):
        entry = ALLOWED_METRICS_WITH_UNITS.get(metric, {})
        unit = entry.get("unit", "")
        desc = entry.get("description", "")
        pattern = f"wach_e{{XXXX}}_{metric}"
        consumers = FAIR_METRIC_CONSUMERS.get(metric, [])

        rows.append({
            "metric_name": metric,
            "unit": unit,
            "description": desc,
            "measurement_pattern": pattern,
            "fair_score_consumer": ", ".join(consumers) if consumers else "(none)",
            "in_fair_default_fetch": metric in [
                "power_total", "energy_import", "power_factor_avg",
                "current_unbalance", "current_l1_thd", "current_l3_thd",
            ],
        })

    # Write CSV
    fieldnames = ["metric_name", "unit", "description", "measurement_pattern",
                  "fair_score_consumer", "in_fair_default_fetch"]
    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Also print summary to stdout
    print(f"\n[metrics] Wrote {len(rows)} rows to {OUTPUT}")

    # Categorize by FAIR usage
    fair_default = [r for r in rows if r["in_fair_default_fetch"]]
    fair_unused = [r for r in rows if not r["in_fair_default_fetch"]]

    print(f"\n[metrics] FAIR default fetch metrics ({len(fair_default)}):")
    for r in fair_default:
        print(f"  {r['metric_name']:25s} -> {r['fair_score_consumer']}")

    print(f"\n[metrics] Not in FAIR default fetch ({len(fair_unused)}):")
    for r in fair_unused:
        print(f"  {r['metric_name']:25s} ({r['unit']})")

    print("\n[metrics] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
