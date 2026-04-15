import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_registry_is_dict_of_dicts():
    """Each metric entry should be a dict with unit, description, aliases."""
    from models.schemas import ALLOWED_METRICS_WITH_UNITS
    for key, entry in ALLOWED_METRICS_WITH_UNITS.items():
        assert isinstance(entry, dict), f"{key}: expected dict, got {type(entry)}"
        assert "unit" in entry, f"{key}: missing 'unit'"
        assert "description" in entry, f"{key}: missing 'description'"
        assert "aliases" in entry, f"{key}: missing 'aliases'"
        assert isinstance(entry["aliases"], list), f"{key}: aliases should be a list"


def test_allowed_metrics_list_matches_keys():
    """ALLOWED_METRICS should be the list of keys from the registry."""
    from models.schemas import ALLOWED_METRICS, ALLOWED_METRICS_WITH_UNITS
    assert set(ALLOWED_METRICS) == set(ALLOWED_METRICS_WITH_UNITS.keys())


def test_get_metric_unit():
    """get_metric_unit reads from new dict structure."""
    from models.schemas import get_metric_unit
    assert get_metric_unit("power_total") == "kW"
    assert get_metric_unit("energy_import") == "kWh"
    assert get_metric_unit("nonexistent") == ""


def test_get_metric_description():
    """get_metric_description reads from new dict structure."""
    from models.schemas import get_metric_description
    assert "active power" in get_metric_description("power_total").lower()
    assert get_metric_description("nonexistent") == ""


def test_resolve_metric_exact_key():
    """Exact metric key name matches."""
    from models.schemas import resolve_metric
    assert resolve_metric("show power_total for e0101") == "power_total"


def test_resolve_metric_alias():
    """Natural language alias matches."""
    from models.schemas import resolve_metric
    assert resolve_metric("show energy consumption for level 3") == "energy_import"


def test_resolve_metric_multi_word_priority():
    """Multi-word alias 'apparent power' matches before single-word 'power'."""
    from models.schemas import resolve_metric
    assert resolve_metric("apparent power for e0101") == "apparent_power_total"


def test_resolve_metric_no_match():
    """Returns None when no metric matches."""
    from models.schemas import resolve_metric
    assert resolve_metric("what is the weather") is None


@pytest.mark.parametrize("text,expected", [
    ("show phase imbalance for e0101", "current_unbalance"),
    ("voltage unbalance level 3", "volts_unbalance"),
    ("thd l3 for e0101", "current_l3_thd"),
    ("energy usage level 5", "energy_import"),
    ("voltage readings e0201", "volts_l_n_avg"),
    ("show reactive power", "reactive_power_total"),
    ("power factor for e0101", "power_factor_avg"),
    ("current for level 1", "current_avg"),
])
def test_resolve_metric_aliases(text, expected):
    """All aliases from the old metric_map should resolve correctly."""
    from models.schemas import resolve_metric
    assert resolve_metric(text) == expected
