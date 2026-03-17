"""
scripts/generate_ahu_docs.py
─────────────────────────────
One-time script: converts docs/ahu_level_mapping.json and docs/ahu_relationships.tsv
into a single readable markdown document for RAG ingestion.

Usage:
    cd backend && python -m scripts.generate_ahu_docs

Output:
    data/rag_docs/ahu_directory.md
"""

import json
import os
import sys
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # add backend/ to path
from config import get_building_name, get_department


def generate_ahu_directory(
    mapping_json: str = "../docs/ahu_level_mapping.json",
    relationships_tsv: str = "../docs/ahu_relationships.tsv",
    output_path: str = "data/rag_docs/ahu_directory.md",
) -> str:
    """Generate AHU directory markdown from source files."""
    base = Path(__file__).parent.parent  # backend/
    mapping_path = (base / mapping_json).resolve()
    tsv_path = (base / relationships_tsv).resolve()
    out_path = (base / output_path).resolve()

    # Load JSON
    with open(mapping_path, encoding="utf-8") as f:
        mapping = json.load(f)

    # Load TSV
    ahu_details: dict[str, dict] = {}
    with open(tsv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            device_id = (row.get("device_id") or "").strip()
            if device_id and device_id.startswith("e"):
                ahu_details[device_id] = {
                    "label": (row.get("AHU Label") or "").strip(),
                    "department": (row.get("Department Name") or "").strip(),
                    "area": (row.get("Area Name") or "").strip(),
                    "location": (row.get("Location") or "").strip(),
                    "type": (row.get("Type") or "").strip(),
                    "class": (row.get("Class") or "").strip(),
                }

    # Build markdown
    lines = [
        f"# AHU Directory — {get_building_name()}, {get_department()}",
        "",
        "This document lists all Air Handling Units (AHUs) across 11 building levels.",
        "Each AHU is identified by a device_id (e.g., e0101 = Level 1, Unit 01).",
        "Device IDs are used in all WACH monitoring queries and health score reports.",
        "",
        "## Building Summary",
        "",
        f"- **Total levels**: {len(mapping.get('levels', {}))}",
        f"- **Total AHUs monitored**: {len(mapping.get('device_to_level', {}))}",
        "- **Level range**: Level 1 (Ground/Emergency) to Level 11 (Paediatric Surgical)",
        "",
        "## Levels and Departments",
        "",
    ]

    levels = mapping.get("levels", {})
    level_to_devices = mapping.get("level_to_devices", {})

    for level_key in sorted(levels.keys()):
        lvl = levels[level_key]
        level_num = lvl.get("level_number", "?")
        dept = lvl.get("department_name", "")
        area = lvl.get("area_name", "")
        devices = level_to_devices.get(level_key, [])

        lines.append(f"### Level {level_num} — {dept}")
        lines.append(f"**Area**: {area}")
        lines.append(f"**AHU Count**: {len(devices)}")
        lines.append(f"**Device IDs**: {', '.join(devices)}")
        lines.append("")

        # Detail table if we have TSV data
        device_rows = [(d, ahu_details.get(d, {})) for d in devices if d in ahu_details]
        if device_rows:
            lines.append("| Device ID | AHU Label | Location | Class |")
            lines.append("|-----------|-----------|----------|-------|")
            for dev_id, det in device_rows:
                label = det.get("label", "—")
                loc = det.get("location", "—")
                cls = det.get("class", "—")
                lines.append(f"| {dev_id} | {label} | {loc} | {cls} |")
            lines.append("")

    lines += [
        "## Device ID Convention",
        "",
        "Device IDs follow the pattern `e{LLUU}` where:",
        "- `LL` = 2-digit level number (01–11)",
        "- `UU` = 2-digit unit number within that level",
        "",
        "Examples:",
        "- `e0101` = Level 1, AHU unit 01 (Emergency Department)",
        "- `e0501` = Level 5, AHU unit 01 (PICU T3 / Paediatric Intensive Care Unit)",
        "- `e1101` = Level 11, AHU unit 01 (Paediatric Surgical Ward)",
        "",
        "## How to Query by Level",
        "",
        "To see health scores for all AHUs on a level, use the level number (1–11).",
        "To ask about a specific AHU, use its device_id (e.g., 'e0501').",
        "The dashboard groups AHUs by level for fleet health monitoring.",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[generate_ahu_docs] Written {len(lines)} lines to {out_path}")
    return str(out_path)


if __name__ == "__main__":
    generate_ahu_directory()
