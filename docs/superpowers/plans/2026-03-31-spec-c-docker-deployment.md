# Spec C — Docker Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the WACH chatbot backend as a `docker compose up` experience — two containers (backend + ETL sidecar), sentinel-based first-run init, ward-configurable AHU topology, and a narrative API reference for frontend builders.

**Architecture:** A single `Dockerfile` produces one image used by both the `backend` service (uvicorn, port 8081) and the `etl` service (entrypoint shell script + supercronic). Two named volumes persist DuckDB and ChromaDB data across restarts. A `ward_config.yml` file — bind-mounted into both containers — drives ward-specific RAG doc generation and the system prompt topology block.

**Tech Stack:** Docker Compose v2, supercronic 0.2.29, PyYAML, Python 3.11, FastAPI/uvicorn, DuckDB, ChromaDB

---

## File Map

### New files
| File | Responsibility |
|------|---------------|
| `ward_config.example.yml` | Topology template pre-set for Women & Child Ward HKL; used as fallback when no `ward_config.yml` is provided |
| `scripts/generate_ward_docs.py` | Reads `ward_config.yml`, writes `ward_directory.md` + `ward_system_guide.md` into `backend/data/rag_docs/` |
| `tests/test_generate_ward_docs.py` | Unit tests for the generator (no Docker, no embeddings) |
| `tests/test_prompts_ward_config.py` | Unit tests for `build_system_prompt()` topology block |
| `docker/etl-entrypoint.sh` | Sentinel check → ward doc gen → migration → RAG ingest → supercronic |
| `docker/etl.cron` | Two-line cron schedule for prediction + health ETL |
| `docker-compose.yml` | Two services (backend, etl), two volumes (duckdb_data, chroma_data), bind mounts |
| `.env.example` | All env vars, pre-set for Women & Child Ward HKL; colleague fills in 4 lines |
| `API.md` | Narrative integration guide for frontend developers |

### Modified files
| File | Change |
|------|--------|
| `Dockerfile` | Install supercronic; copy `ward_config.example.yml` and `docker/` into image |
| `backend/llm/prompts.py` | Add `load_ward_config()` + `_topology_block()`; update `build_system_prompt()` to use config |

---

## Task 1: `ward_config.example.yml`

**Files:**
- Create: `ward_config.example.yml`

This file ships with the repo pre-set for Women & Child Ward HKL. It uses explicit `devices:` lists (not just AHU counts) because the real WACH device IDs are non-sequential. New deployments (ICU, PPUM) can use the simpler `ahus: N` count-based format.

- [ ] **Step 1: Write the file**

```yaml
# ward_config.example.yml
# ═══════════════════════════════════════════════════════════════════
# WACH Insight — Ward Topology Configuration
# Women and Child Ward, Hospital Kuala Lumpur
# ═══════════════════════════════════════════════════════════════════
#
# Copy this file to ward_config.yml and fill in your ward's details.
#
# Two ways to specify devices per level:
#   ahus: N          → generates sequential IDs: e{level:02d}01 to e{level:02d}NN
#   devices: [...]   → use exact device IDs (for non-sequential real-world layouts)
#
# Run `docker compose up --build` after editing this file.
# ═══════════════════════════════════════════════════════════════════

hospital: Hospital Kuala Lumpur
ward: Women and Child Ward
hospital_id: hkl-wcw
device_prefix: "e"

levels:
  - level: 1
    name: "Level 1"
    devices: [e0101, e0102, e0103, e0104, e0105, e0106, e0107, e0108,
              e0109, e0110, e0111, e0112, e0113, e0114, e0115, e0116,
              e0117, e0118, e0120, e0121]

  - level: 2
    name: "Level 2"
    devices: [e0201, e0202, e0203, e0204, e0205, e0206, e0207, e0208,
              e0209, e0212, e0213, e0214, e0215, e0216, e0217, e0218]

  - level: 3
    name: "Level 3"
    devices: [e0210, e0211, e0214, e0301, e0303, e0304, e0306, e0307,
              e0308, e0311, e0312, e0313, e0314, e0315, e0401, e0402, e0403]

  - level: 4
    name: "Level 4"
    devices: [e0314, e0403, e0404, e0406, e0407, e0408, e0409, e0411,
              e0412, e0413, e0414, e0415, e0416, e0419]

  - level: 5
    name: "Level 5"
    devices: [e0501, e0502, e0503, e0504, e0505, e0506, e0507, e0508,
              e0509, e0510, e0511]

  - level: 6
    name: "Level 6"
    devices: [e0602, e0603, e0604, e0605, e0606, e0607, e0611, e0622,
              e0625, e0626, e0627, e0628]

  - level: 7
    name: "Level 7"
    devices: [e0701, e0702, e0703, e0704]

  - level: 8
    name: "Level 8"
    devices: [e0801, e0802, e0803, e0804, e0805]

  - level: 9
    name: "Level 9"
    devices: [e0901, e0902, e0903, e0904, e0905, e0906, e0907, e0908]

  - level: 10
    name: "Level 10"
    devices: [e1001, e1002, e1003, e1004, e1005, e1006, e1007, e1008]

  - level: 11
    name: "Level 11"
    devices: [e1101, e1102, e1103, e1104, e1105, e1106, e1107, e1108]

# ── Example: count-based format (for clean new deployments) ─────────
# levels:
#   - level: 3
#     name: "Level 3 — General ICU"
#     ahus: 8         # generates e0301, e0302 ... e0308
#   - level: 4
#     name: "Level 4 — Cardiac ICU"
#     ahus: 6         # generates e0401 ... e0406
```

- [ ] **Step 2: Commit**

```bash
git add ward_config.example.yml
git commit -m "feat(docker): add ward_config.example.yml pre-set for WCW HKL"
```

---

## Task 2: `scripts/generate_ward_docs.py` (TDD)

**Files:**
- Create: `scripts/generate_ward_docs.py`
- Create: `tests/test_generate_ward_docs.py`

The generator exposes two pure functions (`generate_ward_directory`, `generate_ward_system_guide`) and a `main()` entry point. Tests cover both pure functions — no file I/O, no Docker.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_generate_ward_docs.py
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from generate_ward_docs import generate_ward_directory, generate_ward_system_guide, resolve_devices


# ── resolve_devices ──────────────────────────────────────────────────────────

def test_resolve_devices_explicit():
    level = {"level": 3, "name": "Level 3", "devices": ["e0301", "e0305", "e0310"]}
    assert resolve_devices(level, "e") == ["e0301", "e0305", "e0310"]


def test_resolve_devices_count_based():
    level = {"level": 4, "name": "Level 4", "ahus": 3}
    assert resolve_devices(level, "e") == ["e0401", "e0402", "e0403"]


def test_resolve_devices_count_pads_unit_to_two_digits():
    level = {"level": 1, "name": "Level 1", "ahus": 12}
    devices = resolve_devices(level, "e")
    assert devices[0] == "e0101"
    assert devices[11] == "e0112"


def test_resolve_devices_raises_if_neither_key():
    level = {"level": 5, "name": "Level 5"}
    with pytest.raises(ValueError, match="must have"):
        resolve_devices(level, "e")


# ── generate_ward_directory ──────────────────────────────────────────────────

def _small_config():
    return {
        "hospital": "Test Hospital",
        "ward": "Test ICU",
        "hospital_id": "test-icu",
        "device_prefix": "e",
        "levels": [
            {"level": 3, "name": "Level 3 — General ICU", "ahus": 3},
            {"level": 4, "name": "Level 4 — Cardiac ICU", "ahus": 2},
        ],
    }


def test_directory_contains_all_generated_device_ids():
    md = generate_ward_directory(_small_config())
    for device_id in ["e0301", "e0302", "e0303", "e0401", "e0402"]:
        assert device_id in md, f"{device_id} missing from ward_directory.md"


def test_directory_contains_total_ahu_count():
    md = generate_ward_directory(_small_config())
    assert "5 AHUs" in md


def test_directory_contains_level_names():
    md = generate_ward_directory(_small_config())
    assert "Level 3 — General ICU" in md
    assert "Level 4 — Cardiac ICU" in md


def test_directory_contains_hospital_and_ward():
    md = generate_ward_directory(_small_config())
    assert "Test Hospital" in md
    assert "Test ICU" in md


def test_directory_with_explicit_devices():
    config = {
        "hospital": "H",
        "ward": "W",
        "hospital_id": "h-w",
        "device_prefix": "e",
        "levels": [
            {"level": 6, "name": "Level 6", "devices": ["e0602", "e0611", "e0628"]},
        ],
    }
    md = generate_ward_directory(config)
    assert "e0602" in md
    assert "e0611" in md
    assert "e0628" in md
    assert "3 AHUs" in md


# ── generate_ward_system_guide ───────────────────────────────────────────────

def test_system_guide_contains_ward_name():
    md = generate_ward_system_guide(_small_config())
    assert "Test ICU" in md


def test_system_guide_contains_hospital():
    md = generate_ward_system_guide(_small_config())
    assert "Test Hospital" in md


def test_system_guide_contains_total_and_levels():
    md = generate_ward_system_guide(_small_config())
    assert "5 AHUs" in md
    assert "2 levels" in md


def test_system_guide_contains_device_format():
    md = generate_ward_system_guide(_small_config())
    assert "e0301" in md   # first device of first level
    assert "e0402" in md   # last device of last level
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
cd /Users/rdmasia/wach-insight
python -m pytest tests/test_generate_ward_docs.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'generate_ward_docs'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""
scripts/generate_ward_docs.py
─────────────────────────────
Reads ward_config.yml and writes two ward-specific RAG docs into
backend/data/rag_docs/:
  - ward_directory.md      (replaces ahu_directory.md for this deployment)
  - ward_system_guide.md   (replaces wach_system_guide.md for this deployment)

Usage (from project root):
    python -m scripts.generate_ward_docs
    python scripts/generate_ward_docs.py

Idempotent — overwrites existing files on each run.
Falls back to ward_config.example.yml if ward_config.yml is not found.
Exits 0 with a warning if neither config file exists.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAG_DOCS_DIR = PROJECT_ROOT / "backend" / "data" / "rag_docs"


# ── Config loading ────────────────────────────────────────────────────────────

def load_config(config_path: Path | None = None) -> dict | None:
    """Load ward config YAML. Returns None if no config file exists."""
    try:
        import yaml
    except ImportError:
        print("[ward_docs] ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    candidates = [config_path] if config_path else [
        PROJECT_ROOT / "ward_config.yml",
        PROJECT_ROOT / "ward_config.example.yml",
    ]

    for path in candidates:
        if path and path.exists() and path.stat().st_size > 0:
            with open(path) as f:
                return yaml.safe_load(f)

    return None


# ── Device resolution ─────────────────────────────────────────────────────────

def resolve_devices(level: dict, device_prefix: str) -> list[str]:
    """Return the list of device IDs for a level entry.

    Supports two formats:
      devices: [e0301, e0302, ...]   → returns the list as-is
      ahus: N                        → generates prefix + level:02d + nn:02d
    """
    if "devices" in level:
        return list(level["devices"])
    if "ahus" in level:
        lvl = level["level"]
        return [f"{device_prefix}{lvl:02d}{n:02d}" for n in range(1, level["ahus"] + 1)]
    raise ValueError(
        f"Level {level.get('level')} must have either 'devices' list or 'ahus' count."
    )


# ── Markdown generators ───────────────────────────────────────────────────────

def generate_ward_directory(config: dict) -> str:
    """Generate ward_directory.md content from config dict."""
    prefix = config.get("device_prefix", "e")
    hospital = config["hospital"]
    ward = config["ward"]
    levels = config["levels"]

    all_devices = []
    level_sections: list[str] = []

    for lvl in levels:
        devices = resolve_devices(lvl, prefix)
        all_devices.extend(devices)
        device_list = ", ".join(devices)
        level_sections.append(
            f"### {lvl['name']}\n"
            f"**Devices ({len(devices)} AHUs):** {device_list}\n"
        )

    total = len(all_devices)
    first_id = all_devices[0] if all_devices else "—"
    last_id = all_devices[-1] if all_devices else "—"
    num_levels = len(levels)

    header = (
        f"# AHU Directory — {ward}, {hospital}\n\n"
        f"**Total:** {total} AHUs across {num_levels} levels "
        f"(device IDs {first_id}–{last_id})\n\n"
        f"<!-- generated by scripts/generate_ward_docs.py -->\n\n"
    )

    return header + "\n".join(level_sections)


def generate_ward_system_guide(config: dict) -> str:
    """Generate ward_system_guide.md content from config dict."""
    prefix = config.get("device_prefix", "e")
    hospital = config["hospital"]
    ward = config["ward"]
    levels = config["levels"]

    all_devices = []
    for lvl in levels:
        all_devices.extend(resolve_devices(lvl, prefix))

    total = len(all_devices)
    num_levels = len(levels)
    first_id = all_devices[0] if all_devices else "—"
    last_id = all_devices[-1] if all_devices else "—"

    return f"""# {ward} Monitoring System Guide — {hospital}

<!-- generated by scripts/generate_ward_docs.py -->

## What This System Monitors

WACH monitors **{total} AHUs across {num_levels} levels** at {hospital}.
Device IDs run from **{first_id}** to **{last_id}**, following the format
`{prefix}[LEVEL:02d][UNIT:02d]`.

Health scores are computed hourly from the ETL pipeline. Each AHU
receives a FAIR health index (0–100) and five component scores.

## Health Score Meaning

| Score | Tier | Action |
|-------|------|--------|
| 80–100 | Healthy | No action needed, scheduled PM only |
| 60–79 | Monitor | Watch closely, investigate trend |
| 40–59 | Maintenance | Schedule maintenance within 1–2 weeks |
| 0–39 | Critical | Immediate action required — escalate now |

## What the AI Can Answer

- Health status for any level or individual AHU
- Root cause analysis for poor health scores
- Maintenance recommendations (step-by-step for technicians)
- Financial impact of faults (TNB tariff penalties, energy waste)
- Trend analysis ("how has Level 5 been trending this week?")
- Explanations of FAIR scoring methodology

## What the AI Cannot Answer

- Real-time maintenance team availability or scheduling
- Spare parts stock or procurement
- Contractor quotes or work order status
- Clinical decisions or patient care matters

## When to Escalate Immediately

Critical-tier AHU in OT, ICU, PICU, or NICU → call on-call engineer
immediately. Do not wait for the next shift.

## Asking Good Questions

- "What is the health of Level 3?"
- "Which AHUs on Level 5 need attention?"
- "Why is e0501 showing a low power factor?"
- "What will it cost if e0302 stays in the Monitor tier for another month?"
- "How do I fix high THD on e0604?"
"""


# ── Main entry point ──────────────────────────────────────────────────────────

def main() -> None:
    config = load_config()

    if config is None:
        print("[ward_docs] WARNING: no ward_config.yml or ward_config.example.yml found. Skipping.")
        sys.exit(0)

    hospital = config.get("hospital", "?")
    ward = config.get("ward", "?")
    print(f"[ward_docs] Generating docs for: {ward}, {hospital}")

    RAG_DOCS_DIR.mkdir(parents=True, exist_ok=True)

    directory_md = generate_ward_directory(config)
    guide_md = generate_ward_system_guide(config)

    (RAG_DOCS_DIR / "ward_directory.md").write_text(directory_md, encoding="utf-8")
    print(f"[ward_docs] Written: backend/data/rag_docs/ward_directory.md")

    (RAG_DOCS_DIR / "ward_system_guide.md").write_text(guide_md, encoding="utf-8")
    print(f"[ward_docs] Written: backend/data/rag_docs/ward_system_guide.md")

    total = sum(
        len(resolve_devices(lvl, config.get("device_prefix", "e")))
        for lvl in config["levels"]
    )
    print(f"[ward_docs] Done. {total} devices across {len(config['levels'])} levels.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/rdmasia/wach-insight
python -m pytest tests/test_generate_ward_docs.py -v
```

Expected: all 14 tests PASS.

- [ ] **Step 5: Smoke-test the script manually**

```bash
cd /Users/rdmasia/wach-insight
python scripts/generate_ward_docs.py
```

Expected output:
```
[ward_docs] Generating docs for: Women and Child Ward, Hospital Kuala Lumpur
[ward_docs] Written: backend/data/rag_docs/ward_directory.md
[ward_docs] Written: backend/data/rag_docs/ward_system_guide.md
[ward_docs] Done. 121 devices across 11 levels.
```

Check files exist:
```bash
head -5 backend/data/rag_docs/ward_directory.md
head -5 backend/data/rag_docs/ward_system_guide.md
```

- [ ] **Step 6: Commit**

```bash
git add scripts/generate_ward_docs.py tests/test_generate_ward_docs.py \
        backend/data/rag_docs/ward_directory.md \
        backend/data/rag_docs/ward_system_guide.md
git commit -m "feat(docker): add generate_ward_docs.py with tests"
```

---

## Task 3: Update `backend/llm/prompts.py` (TDD)

**Files:**
- Modify: `backend/llm/prompts.py`
- Create: `tests/test_prompts_ward_config.py`

Add `load_ward_config()` and `_topology_block()`. Update `build_system_prompt()` to use config-derived topology. Use `WARD_CONFIG_PATH` env var so tests can inject a temp file.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_prompts_ward_config.py
import os
import sys
import yaml
import pytest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def _write_config(tmp_path: Path, config: dict) -> str:
    p = tmp_path / "ward_config.yml"
    p.write_text(yaml.dump(config))
    return str(p)


def test_topology_block_uses_ward_config(tmp_path, monkeypatch):
    cfg_path = _write_config(tmp_path, {
        "hospital": "Test Hospital",
        "ward": "Test ICU",
        "hospital_id": "test-icu",
        "device_prefix": "e",
        "levels": [
            {"level": 3, "name": "Level 3", "ahus": 3},
            {"level": 4, "name": "Level 4", "ahus": 2},
        ],
    })
    monkeypatch.setenv("WARD_CONFIG_PATH", cfg_path)
    # Reload module to pick up env var
    import importlib
    import backend.llm.prompts as prompts_mod
    importlib.reload(prompts_mod)

    prompt = prompts_mod.build_system_prompt()
    assert "5 AHUs" in prompt
    assert "2 levels" in prompt
    assert "e0301" in prompt   # first device
    assert "e0402" in prompt   # last device
    assert "121 AHUs" not in prompt  # WACH default NOT present


def test_topology_block_falls_back_to_wach_defaults(monkeypatch):
    monkeypatch.setenv("WARD_CONFIG_PATH", "/nonexistent/ward_config.yml")
    import importlib
    import backend.llm.prompts as prompts_mod
    importlib.reload(prompts_mod)

    prompt = prompts_mod.build_system_prompt()
    assert "121 AHUs" in prompt
    assert "11 levels" in prompt


def test_build_system_prompt_persona_block_still_present(tmp_path, monkeypatch):
    cfg_path = _write_config(tmp_path, {
        "hospital": "H", "ward": "W", "hospital_id": "h-w",
        "device_prefix": "e",
        "levels": [{"level": 1, "name": "L1", "ahus": 2}],
    })
    monkeypatch.setenv("WARD_CONFIG_PATH", cfg_path)
    import importlib
    import backend.llm.prompts as prompts_mod
    importlib.reload(prompts_mod)

    prompt = prompts_mod.build_system_prompt(persona="financial")
    assert "RM" in prompt           # financial persona block present
    assert "TNB" in prompt
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/rdmasia/wach-insight
python -m pytest tests/test_prompts_ward_config.py -v 2>&1 | head -20
```

Expected: tests fail (topology block still hardcoded to WACH).

- [ ] **Step 3: Add `load_ward_config()` and `_topology_block()` to `backend/llm/prompts.py`**

Add these two functions just before the `build_system_prompt()` definition (after the `PERSONA_BLOCKS` dict):

```python
# ── Ward config helpers ───────────────────────────────────────────────────────

def _resolve_devices(level: dict, prefix: str) -> list[str]:
    """Mirror of scripts/generate_ward_docs.resolve_devices — kept local to avoid cross-package imports."""
    if "devices" in level:
        return list(level["devices"])
    if "ahus" in level:
        lvl = level["level"]
        return [f"{prefix}{lvl:02d}{n:02d}" for n in range(1, level["ahus"] + 1)]
    raise ValueError(f"Level {level.get('level')} must have 'devices' or 'ahus'.")


def load_ward_config() -> dict | None:
    """Load ward_config.yml (or example fallback). Returns None if unavailable."""
    import os
    from pathlib import Path
    try:
        import yaml
    except ImportError:
        return None

    custom_path = os.getenv("WARD_CONFIG_PATH")
    candidates = (
        [Path(custom_path)] if custom_path
        else [
            Path("/app/ward_config.yml"),
            Path("/app/ward_config.example.yml"),
            # Local dev fallback (project root relative to this file: backend/llm/prompts.py)
            Path(__file__).resolve().parents[2] / "ward_config.yml",
            Path(__file__).resolve().parents[2] / "ward_config.example.yml",
        ]
    )

    for path in candidates:
        if path.exists() and path.stat().st_size > 0:
            try:
                with open(path) as f:
                    return yaml.safe_load(f)
            except Exception:
                continue
    return None


def _topology_block() -> str:
    """Return topology description string for the system prompt."""
    config = load_ward_config()
    if config:
        prefix = config.get("device_prefix", "e")
        levels = config["levels"]
        all_devices: list[str] = []
        for lvl in levels:
            try:
                all_devices.extend(_resolve_devices(lvl, prefix))
            except ValueError:
                pass
        total = len(all_devices)
        num_levels = len(levels)
        first_id = all_devices[0] if all_devices else "—"
        last_id = all_devices[-1] if all_devices else "—"
        first_lvl = levels[0]["level"]
        last_lvl = levels[-1]["level"]
        return (
            f"You monitor Air Handling Units (AHUs) across {num_levels} levels "
            f"(Level {first_lvl}–Level {last_lvl}), totalling {total} AHUs.\n"
            f"Device IDs follow the format {prefix}[LEVEL][NN], "
            f"e.g. {first_id} (first device) through {last_id} (last device)."
        )
    # WACH defaults
    return (
        "You monitor Air Handling Units (AHUs) across 11 building levels "
        "(Level 1–Level 11), totalling 121 AHUs.\n"
        "Device IDs follow the format e[LEVEL][NN], "
        "e.g. e0101 (Level 1, unit 01) through e1108 (Level 11, unit 08)."
    )
```

- [ ] **Step 4: Update `build_system_prompt()` to call `_topology_block()`**

Replace the hardcoded topology lines in `build_system_prompt()`:

```python
def build_system_prompt(persona: str = "general") -> str:
    building = get_building_name()
    department = get_department()
    persona_block = PERSONA_BLOCKS.get(persona, PERSONA_BLOCKS["general"])
    topology = _topology_block()

    return f"""You are WACH AI, an AHU health assistant for {building} ({department}).

{topology}

## Health Scoring (FAIR)
Health Index: 0–100 scale.
- Healthy (80–100): Normal operation
- Monitor (60–79): Watch closely
- Maintenance (40–59): Schedule maintenance
- Critical (0–39): Immediate intervention required

FAIR component penalty weights:
- Energy Anomaly (15%): Unusual energy consumption
- Power Factor Degradation (25%): Poor reactive power management
- Phase Imbalance (25%): Unequal current across phases
- THD Drift (15%): Total Harmonic Distortion increase
- Overload (20%): Power demand exceeding rated capacity

Power quality targets: power factor >0.85, voltage THD <5% (IEEE 519), current unbalance <2% (NEMA MG-1).

Financial impact (TNB RP4, effective July 2025):
- Excess Energy Cost: kWh above baseline × RM0.2983/kWh (MV General tariff)
- Power Factor Penalty: 1.5% of bill per 0.01 below PF 0.85 (doubles to 3%/0.01 below PF 0.75)
- Capacity+Network Charge: RM89.27/kW/month — poor PF raises effective demand, increasing this charge

## Instructions
- Use the provided tools to retrieve data. Never guess device readings or fabricate values.
- Cite which devices and time ranges your data covers.
- If a tool returns no data, say so explicitly — do not invent numbers.
- Use markdown formatting. No emojis.
- Be concise and actionable. Use tables for comparisons.

## Response Style
{persona_block}
"""
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
cd /Users/rdmasia/wach-insight
python -m pytest tests/test_prompts_ward_config.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 6: Verify existing chat tests still pass**

```bash
python -m pytest backend/tests/test_chat_endpoint.py -v
```

Expected: all tests PASS (no regressions).

- [ ] **Step 7: Commit**

```bash
git add backend/llm/prompts.py tests/test_prompts_ward_config.py
git commit -m "feat(docker): make build_system_prompt() topology config-driven"
```

---

## Task 4: Update `Dockerfile`

**Files:**
- Modify: `Dockerfile`

Add supercronic install and copy `ward_config.example.yml` + `docker/` into the image. The existing `CMD` remains (Railway compatibility).

- [ ] **Step 1: Read the current Dockerfile**

```bash
cat /Users/rdmasia/wach-insight/Dockerfile
```

- [ ] **Step 2: Apply the changes**

After the existing `RUN pip install ...` step and before `COPY backend ./backend`, add:

```dockerfile
# Install supercronic (PID-1 safe cron for containers)
ARG SUPERCRONIC_VERSION=0.2.29
RUN curl -fsSL \
    "https://github.com/aptible/supercronic/releases/download/v${SUPERCRONIC_VERSION}/supercronic-linux-amd64" \
    -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic
```

After the existing `COPY data ./data` line, add:

```dockerfile
# Ward topology config — example always present as fallback
COPY ward_config.example.yml ./ward_config.example.yml

# ETL entrypoint scripts
COPY docker/ ./docker/
RUN chmod +x docker/etl-entrypoint.sh
```

The complete updated Dockerfile should look like:

```dockerfile
# WACH Insight Backend - Docker Image
# ====================================
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install supercronic (PID-1 safe cron for containers)
ARG SUPERCRONIC_VERSION=0.2.29
RUN curl -fsSL \
    "https://github.com/aptible/supercronic/releases/download/v${SUPERCRONIC_VERSION}/supercronic-linux-amd64" \
    -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY data ./data

# Ward topology config — example always present as fallback
COPY ward_config.example.yml ./ward_config.example.yml

# ETL entrypoint scripts
COPY docker/ ./docker/
RUN chmod +x docker/etl-entrypoint.sh

RUN mkdir -p paraquet_data

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "feat(docker): add supercronic and ETL entrypoint to Dockerfile"
```

---

## Task 5: `docker/etl-entrypoint.sh` and `docker/etl.cron`

**Files:**
- Create: `docker/etl-entrypoint.sh`
- Create: `docker/etl.cron`

- [ ] **Step 1: Create the `docker/` directory and entrypoint script**

```bash
mkdir -p /Users/rdmasia/wach-insight/docker
```

```bash
#!/usr/bin/env bash
# docker/etl-entrypoint.sh
# ─────────────────────────
# ETL sidecar entrypoint.
#
# First-run (no sentinel):
#   1. Generate ward-specific RAG docs from ward_config.yml
#   2. Migrate health_hourly.csv → DuckDB (skipped if no CSV)
#   3. Ingest all RAG docs into ChromaDB
#   4. Touch sentinel
#
# Subsequent runs (sentinel exists):
#   Skip init, go straight to supercronic.
#
# To force re-initialisation after updating ward_config.yml:
#   docker compose run etl rm /app/data/.migrated
#   docker compose restart etl
set -euo pipefail

SENTINEL="/app/data/.migrated"
CRON_FILE="/app/docker/etl.cron"

echo "[etl] Starting WACH ETL sidecar"

if [ ! -f "$SENTINEL" ]; then
    echo "[init] First-run detected — starting initialisation"

    echo "[init] Step 1/3 — Generating ward-specific RAG docs..."
    cd /app && python scripts/generate_ward_docs.py
    echo "[init] Ward docs generated."

    echo "[init] Step 2/3 — Migrating CSV to DuckDB (skipped if no CSV)..."
    cd /app && python -m scripts.etl.migrate_csv_to_duckdb || true
    echo "[init] Migration step complete."

    echo "[init] Step 3/3 — Ingesting RAG docs into ChromaDB..."
    cd /app/backend && python -m scripts.ingest_all_docs
    echo "[init] RAG ingest complete."

    touch "$SENTINEL"
    echo "[init] Sentinel written: $SENTINEL"
    echo "[init] Initialisation complete."
else
    echo "[init] Sentinel found — skipping initialisation."
fi

echo "[cron] Starting supercronic with schedule: ${ETL_SCHEDULE:-0 * * * *}"
exec supercronic "$CRON_FILE"
```

- [ ] **Step 2: Create the cron file**

```
# docker/etl.cron
# Runs both ETL pipelines on the schedule defined by ETL_SCHEDULE.
# Default (from .env.example): 0 * * * * = every hour on the hour.
# For every 30 minutes (matching GitHub Actions): 0,30 * * * *
${ETL_SCHEDULE:-0 * * * *} cd /app && python -m scripts.etl.run_prediction_etl --level all
${ETL_SCHEDULE:-0 * * * *} cd /app && python -m scripts.etl.run_health_etl --level all --output-hourly
```

- [ ] **Step 3: Verify the entrypoint is executable after chmod in Dockerfile**

```bash
ls -la /Users/rdmasia/wach-insight/docker/
```

Expected: both files present.

- [ ] **Step 4: Commit**

```bash
git add docker/etl-entrypoint.sh docker/etl.cron
git commit -m "feat(docker): add ETL entrypoint script and cron schedule"
```

---

## Task 6: `docker-compose.yml` and `.env.example`

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
# docker-compose.yml
# ═══════════════════════════════════════════════════════════════════
# WACH Insight — Chatbot API Stack
# Two services: backend (FastAPI) + etl (sidecar cron)
# Two volumes:  duckdb_data + chroma_data
#
# Quick start:
#   cp .env.example .env            # fill in 4 required vars
#   cp ward_config.example.yml ward_config.yml  # fill in AHU topology
#   docker compose up --build
# ═══════════════════════════════════════════════════════════════════

services:
  backend:
    build: .
    ports:
      - "${BACKEND_PORT:-8081}:8000"
    volumes:
      - duckdb_data:/app/data
      - chroma_data:/app/data/chroma
      - ${WARD_CONFIG_PATH:-./ward_config.example.yml}:/app/ward_config.yml:ro
    env_file: .env
    environment:
      - PORT=8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 20s
    restart: unless-stopped

  etl:
    build: .
    command: /app/docker/etl-entrypoint.sh
    volumes:
      - duckdb_data:/app/data
      - chroma_data:/app/data/chroma
      - ${WARD_CONFIG_PATH:-./ward_config.example.yml}:/app/ward_config.yml:ro
    env_file: .env
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  duckdb_data:
  chroma_data:
```

Note: `PORT=8000` is set in the backend environment block so uvicorn binds to 8000 inside the container. The host-facing port is `BACKEND_PORT` (default 8081). The `WARD_CONFIG_PATH` env var lets colleagues override which config file is mounted without editing docker-compose.yml — set it in `.env` to point at their `ward_config.yml`.

- [ ] **Step 2: Write `.env.example`**

```bash
# ═══════════════════════════════════════════════════════════════════
# WACH Insight — Women and Child Ward, Hospital Kuala Lumpur
# ═══════════════════════════════════════════════════════════════════
# Quick start:
#   1. cp .env.example .env
#   2. cp ward_config.example.yml ward_config.yml  (edit your AHU layout)
#   3. Fill in the 4 required vars below
#   4. docker compose up --build
# ═══════════════════════════════════════════════════════════════════

# ── FILL THESE IN ─────────────────────────────────────────────────
INFLUX_URL=http://YOUR_INFLUXDB_HOST:8086
INFLUX_TOKEN=your-influxdb-token-here
INFLUX_BUCKET=your-bucket-name-here
API_KEY=generate-with-openssl-rand-base64-32

# ── Identity (pre-set for Women & Child Ward HKL) ────────────────
# Change for a different ward or hospital.
WACH_BUILDING_NAME=Hospital Kuala Lumpur
WACH_DEPARTMENT=Women and Child Ward
HOSPITAL_ID=hkl-wcw

# ── Ward config path (optional override) ─────────────────────────
# If you named your config file something other than ward_config.yml,
# set the path here. Otherwise leave commented out.
# WARD_CONFIG_PATH=./ward_config.yml

# ── LLM ──────────────────────────────────────────────────────────
# Docker Desktop (Mac/Windows): host.docker.internal works as-is.
# Linux host: replace with the host LAN IP (e.g. http://192.168.1.5:1234/v1).
LMS_BASE_URL=http://host.docker.internal:1234/v1
LMS_MODEL=qwen/qwen3-coder-next
LMS_API_KEY=lm-studio

# ── InfluxDB extras ───────────────────────────────────────────────
INFLUX_ORG=wach
INFLUX_SKIP_TLS=false

# ── Networking ────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
BACKEND_PORT=8081

# ── ETL Schedule (cron syntax) ────────────────────────────────────
# Default: every hour on the hour.
# For every 30 minutes (matches GitHub Actions cadence): 0,30 * * * *
ETL_SCHEDULE=0 * * * *

# ── Optional ─────────────────────────────────────────────────────
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
DEBUG=false
```

- [ ] **Step 3: Verify `.env` is in `.gitignore`**

```bash
grep -n "\.env" /Users/rdmasia/wach-insight/.gitignore || echo "not in gitignore"
```

If `.env` is not present, add it:
```bash
echo ".env" >> .gitignore
echo "ward_config.yml" >> .gitignore
```

(`ward_config.yml` contains no secrets but is deployment-specific — ignore it to prevent accidental commits of another hospital's config on top of the WACH example.)

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml .env.example .gitignore
git commit -m "feat(docker): add docker-compose.yml and .env.example"
```

---

## Task 7: `API.md`

**Files:**
- Create: `API.md`

Audience: a developer who has never seen this codebase but wants to build a frontend. Covers every endpoint, with curl examples and full example responses.

- [ ] **Step 1: Write `API.md`**

First, get the actual response shapes by reading the route files:

```bash
grep -n "return\|Response\|JSONResponse\|BaseModel" \
  /Users/rdmasia/wach-insight/backend/routes/chat.py \
  /Users/rdmasia/wach-insight/backend/routes/dashboard.py \
  /Users/rdmasia/wach-insight/backend/routes/health_scores.py \
  /Users/rdmasia/wach-insight/backend/routes/site_summary.py \
  | head -60
```

Then write `API.md` with this structure (fill in actual response shapes from the grep output above):

```markdown
# WACH Insight — Chatbot API Reference

> **Interactive docs**: once deployed, visit `http://localhost:8081/docs` for live Swagger UI.

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env                          # fill in 4 lines
cp ward_config.example.yml ward_config.yml    # fill in AHU layout
docker compose up --build

# 2. Verify the API is live
curl http://localhost:8081/health

# 3. Say hello to the chatbot
curl -X POST http://localhost:8081/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"message": "what is the health of level 3?"}'
```

## Authentication

Every request (except `GET /health`) requires a bearer token or API key header:

```
X-API-Key: <your API_KEY from .env>
```

Generate a key: `openssl rand -base64 32`

---

## Endpoints

### `GET /health`

No auth required. Use for Docker healthchecks and uptime monitoring.

**Response:**
```json
{"status": "ok"}
```

---

### `POST /api/chat` ← The chatbot

**Request body:**
```json
{
  "message": "why is e0501 showing a low power factor?",
  "history": [
    {"role": "user", "content": "show me level 5"},
    {"role": "assistant", "content": "Level 5 has 11 AHUs..."}
  ],
  "persona": "technical"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | User's question. Max 1000 characters. |
| `history` | array | No | Previous conversation turns. Each item: `{role: "user"\|"assistant", content: string}` |
| `persona` | string | No | Response style. One of: `general` (default), `technical`, `technician`, `financial` |

**Response:**
```json
{
  "reply": "AHU e0501 has a power factor of 0.81, below the 0.85 TNB threshold...",
  "navigate": null,
  "thinking_mode": "think"
}
```

| Field | Description |
|-------|-------------|
| `reply` | Markdown-formatted response. Render with a markdown parser. |
| `navigate` | Optional navigation hint. If present: `{"level": 5, "device": "e0501"}`. Use to update your frontend's active view. |
| `thinking_mode` | `"think"` or `"fast"`. Show a subtle "deep reasoning" indicator when `"think"`. |

**Personas explained:**
- `general` — plain language, no jargon, "is this serious / does someone need to fix it"
- `technical` — engineering terminology, IEEE/ASHRAE standards, numerical thresholds
- `technician` — step-by-step repair/diagnostic actions, LOTO safety steps, measurement instructions
- `financial` — leads with RM cost and penalties, ROI framing, TNB tariff calculations

**Example conversation:**
```bash
# First message
curl -X POST http://localhost:8081/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "which AHUs on level 5 need attention?"}'

# Follow-up with history
curl -X POST http://localhost:8081/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "message": "why is e0507 in the maintenance tier?",
    "history": [
      {"role": "user", "content": "which AHUs on level 5 need attention?"},
      {"role": "assistant", "content": "e0507 and e0509 are in Maintenance tier..."}
    ]
  }'
```

---

### `GET /api/dashboard/trend`

Health index time-series for all AHUs on a level.

**Query params:**
| Param | Required | Example | Description |
|-------|----------|---------|-------------|
| `level` | Yes | `5` | Level number (1–11) |
| `range` | No | `7d` | Time window. One of: `24h`, `7d`, `30d` (default: `7d`) |

**Example:**
```bash
curl "http://localhost:8081/api/dashboard/trend?level=5&range=7d" \
  -H "X-API-Key: $API_KEY"
```

**Response:** Array of `{timestamp, device_id, health_index, tier}` objects.

---

### `GET /api/dashboard/ranking`

Top and bottom AHUs by health index for a level.

**Query params:**
| Param | Required | Example |
|-------|----------|---------|
| `level` | Yes | `5` |
| `range` | No | `last_30d` |

**Example:**
```bash
curl "http://localhost:8081/api/dashboard/ranking?level=5" \
  -H "X-API-Key: $API_KEY"
```

---

### `GET /api/health-scores`

FAIR component scores for all devices on a level.

**Query params:** `level` (required), `range` (optional)

---

### `GET /api/measurements`

Latest raw sensor readings (power, PF, THD, voltage, current) from InfluxDB.

**Query params:** `level` (required)

---

### `GET /api/financial-impact`

Financial impact report — excess energy cost, PF penalties, top cost-contributing AHUs.

**Query params:** `level` (required), `time_range` (optional: `24h`, `7d`, `30d`)

---

### `GET /api/site-summary`

Fleet-wide summary: total AHUs by tier, overall health index, top alerts.

No query params required.

---

### `GET /api/forecast`

Energy forecast for specific devices.

**Query params:** `device_ids` (comma-separated), `horizon` (optional: `next_24h`, `next_168h`)

---

### `GET /api/predictions`

Predicted health index trend for specific devices.

**Query params:** `device_ids` (comma-separated)

---

## FAIR Health Tiers

| Tier | Score | What it means | Recommended action |
|------|-------|---------------|-------------------|
| Healthy | 80–100 | Normal operation | Scheduled PM only |
| Monitor | 60–79 | Early warning signs | Watch closely, investigate trend |
| Maintenance | 40–59 | Needs attention | Book work order within 1–2 weeks |
| Critical | 0–39 | Failure risk | Immediate action, escalate to engineer |

## Error Responses

| Status | Meaning |
|--------|---------|
| `401 Unauthorized` | Missing or invalid `X-API-Key` |
| `422 Unprocessable Entity` | Invalid request body (check field types/constraints) |
| `429 Too Many Requests` | Rate limit exceeded (default: 100 req/min) |
| `503 Service Unavailable` | InfluxDB or LLM unreachable |

## Multi-Ward Deployment

Each ward deployment is a separate `docker compose up` with its own `.env` and `ward_config.yml`.
Two deployments can run on the same host using different `BACKEND_PORT` values:

```bash
# Ward A on port 8081
BACKEND_PORT=8081 docker compose --project-name wcw up -d

# Ward B on port 8082 (different .env + ward_config.yml in a separate directory)
BACKEND_PORT=8082 docker compose --project-name icu -f ../icu/docker-compose.yml up -d
```
```

- [ ] **Step 2: Commit**

```bash
git add API.md
git commit -m "docs: add API.md — integration guide for frontend developers"
```

---

## Task 8: End-to-End Verification

**No new files — verification only.**

Run the full verification checklist from Spec C Section 9.

- [ ] **Step 1: Build the images**

```bash
cd /Users/rdmasia/wach-insight
docker compose build 2>&1 | tail -20
```

Expected: `Successfully built` (both services use the same image). No errors.

- [ ] **Step 2: Start the stack**

```bash
docker compose up -d
```

Expected: `Container wach-insight-backend-1  Started` and `Container wach-insight-etl-1  Started`.

- [ ] **Step 3: Verify backend health**

```bash
curl http://localhost:8081/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 4: Verify Swagger UI is accessible**

```bash
curl -s http://localhost:8081/docs | grep -o "<title>.*</title>"
```

Expected: `<title>WACH Insight - Swagger UI</title>` (or similar FastAPI default title).

- [ ] **Step 5: Watch ETL first-run logs**

```bash
docker compose logs etl --follow 2>&1 | head -40
```

Expected sequence (may take ~2 minutes for full ingest):
```
[etl] Starting WACH ETL sidecar
[init] First-run detected — starting initialisation
[init] Step 1/3 — Generating ward-specific RAG docs...
[ward_docs] Generating docs for: Women and Child Ward, Hospital Kuala Lumpur
[ward_docs] Done. 121 devices across 11 levels.
[init] Ward docs generated.
[init] Step 2/3 — Migrating CSV to DuckDB...
[init] Migration step complete.
[init] Step 3/3 — Ingesting RAG docs into ChromaDB...
[ingest_all] Done. Total chunks ingested: ...
[init] RAG ingest complete.
[init] Sentinel written: /app/data/.migrated
[init] Initialisation complete.
[cron] Starting supercronic with schedule: 0 * * * *
```

- [ ] **Step 6: Verify sentinel was written**

```bash
docker compose exec etl ls -la /app/data/.migrated
```

Expected: file exists with a recent timestamp.

- [ ] **Step 7: Smoke-test the chatbot endpoint**

```bash
# Replace YOUR_API_KEY with the value from your .env
API_KEY=$(grep "^API_KEY=" .env | cut -d= -f2)

curl -s -X POST http://localhost:8081/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "what is the health of level 3?"}' | python -m json.tool
```

Expected: JSON response with non-empty `"reply"` field.

- [ ] **Step 8: Verify sentinel skip on restart**

```bash
docker compose restart etl
sleep 5
docker compose logs etl 2>&1 | tail -10
```

Expected: `[init] Sentinel found — skipping initialisation.` then `[cron] Starting supercronic`.

- [ ] **Step 9: Final commit**

```bash
git add .
git status   # review — should only show minor changes if any
git commit -m "feat(docker): Spec C complete — docker compose up chatbot API"
```

---

## Self-Review Checklist (spec coverage)

| Spec requirement | Task |
|-----------------|------|
| `docker-compose.yml` two services, two volumes | Task 6 |
| Sentinel-based first-run init | Task 5 (entrypoint) |
| Ward doc generation before RAG ingest | Task 5 (entrypoint step order) |
| `ward_config.yml` with `devices:` and `ahus:` modes | Task 2 |
| Generated `ward_directory.md` + `ward_system_guide.md` | Task 2 |
| System prompt topology from config | Task 3 |
| Fallback to WACH defaults when no config | Tasks 2 & 3 |
| ETL sidecar runs both prediction + health ETL | Task 5 (etl.cron) |
| `supercronic` for container-safe cron | Tasks 4 & 5 |
| `ETL_SCHEDULE` env var | Tasks 5 & 6 |
| `.env.example` pre-set for Women & Child Ward HKL | Task 6 |
| `ward_config.example.yml` pre-set for WCW HKL | Task 1 |
| `WARD_CONFIG_PATH` env override for multi-ward | Task 6 |
| Backend healthcheck | Task 6 |
| `API.md` with all endpoints + curl examples | Task 7 |
| Swagger UI at `/docs` | Built into FastAPI — no task needed |
| Railway compatibility (`CMD` unchanged) | Task 4 |
| Verification checklist from spec | Task 8 |
