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
