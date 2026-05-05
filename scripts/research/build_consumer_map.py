"""Build a consumer map: which code files consume which metrics.

Scans the codebase for references to each metric name and outputs
a CSV mapping metric -> consuming files/modules.

Output: /tmp/metric_consumers.csv
Columns: metric_name, consumer_file, consumer_type, context

Usage:
    cd backend && python3 ../scripts/research/build_consumer_map.py
"""

from __future__ import annotations

import csv
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from models.schemas import ALLOWED_METRICS

OUTPUT = "/tmp/metric_consumers.csv"

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..")

# File patterns to skip
SKIP_DIRS = {"__pycache__", ".git", "venv", ".pytest_cache"}
SKIP_FILES = {"__init__.py"}


def find_py_files(root_dir):
    """Recursively find all .py files."""
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip certain directories
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if fname.endswith(".py") and fname not in SKIP_FILES:
                py_files.append(os.path.join(dirpath, fname))
    return py_files


def scan_for_metric(py_files, metric_name):
    """Find which files reference a given metric name."""
    consumers = []
    pattern = re.compile(r'\b' + re.escape(metric_name) + r'\b')
    
    for fpath in py_files:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    # Determine relative path
                    rel_path = fpath
                    for base in [BACKEND_DIR, SCRIPTS_DIR]:
                        if fpath.startswith(base):
                            rel_path = os.path.relpath(fpath, os.path.dirname(base))
                            break
                    
                    # Classify consumer type
                    line_lower = line.lower().strip()
                    if "import" in line_lower or "from " in line_lower:
                        consumer_type = "import"
                    elif "def " in line_lower or "class " in line_lower:
                        consumer_type = "definition"
                    elif "#" in line and line.strip().startswith("#"):
                        consumer_type = "comment"
                    elif "fetch" in line_lower or "query" in line_lower:
                        consumer_type = "data_fetch"
                    elif "score" in line_lower or "health" in line_lower:
                        consumer_type = "scoring"
                    elif "route" in line_lower or "api" in line_lower or "@" in line:
                        consumer_type = "api"
                    else:
                        consumer_type = "usage"
                    
                    consumers.append({
                        "metric_name": metric_name,
                        "consumer_file": rel_path,
                        "line_number": i,
                        "consumer_type": consumer_type,
                        "context": line.strip()[:120],
                    })
        except (OSError, UnicodeDecodeError):
            continue
    
    return consumers


def main() -> int:
    print("[consumer_map] Scanning codebase for metric references...")
    
    # Find all Python files
    py_files = find_py_files(BACKEND_DIR) + find_py_files(SCRIPTS_DIR)
    print(f"[consumer_map] Found {len(py_files)} Python files to scan")
    
    all_consumers = []
    for metric in sorted(ALLOWED_METRICS):
        print(f"  Scanning for: {metric}")
        consumers = scan_for_metric(py_files, metric)
        all_consumers.extend(consumers)
    
    # Write CSV
    fieldnames = ["metric_name", "consumer_file", "line_number", "consumer_type", "context"]
    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_consumers)
    
    # Print summary
    print(f"\n[consumer_map] Wrote {len(all_consumers)} rows to {OUTPUT}")
    
    # Per-metric summary
    metric_counts = {}
    for c in all_consumers:
        metric_counts[c["metric_name"]] = metric_counts.get(c["metric_name"], 0) + 1
    
    print("\n[consumer_map] References per metric:")
    for metric in sorted(ALLOWED_METRICS):
        count = metric_counts.get(metric, 0)
        if count > 0:
            print(f"  {metric:25s}: {count} references")
    
    # Unique files consuming FAIR default metrics
    fair_defaults = {"power_total", "energy_import", "power_factor_avg",
                     "current_unbalance", "current_l1_thd", "current_l3_thd"}
    fair_files = set()
    for c in all_consumers:
        if c["metric_name"] in fair_defaults:
            fair_files.add(c["consumer_file"])
    
    print(f"\n[consumer_map] Files consuming FAIR default metrics ({len(fair_files)}):")
    for f in sorted(fair_files):
        print(f"  {f}")
    
    print("\n[consumer_map] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())