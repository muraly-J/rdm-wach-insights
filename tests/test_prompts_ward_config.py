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
