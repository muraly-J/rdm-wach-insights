"""Unit tests for chat Gap 1 (time-series), Gap 2 (ranking), Gap 3 (comparison)."""
import pandas as pd
import pytest
from unittest.mock import patch


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_hourly_df(device_id: str = "e0501", level: str = "Level 5", n: int = 24) -> pd.DataFrame:
    import numpy as np
    ts = pd.date_range("2026-03-20", periods=n, freq="h", tz="UTC")
    return pd.DataFrame({
        "timestamp": ts,
        "ahu_id": device_id,
        "level": level,
        "health_index": 75.0 + np.linspace(0, -5, n),
        "energy_anomaly": 60.0 + np.linspace(0, 3, n),
        "pf_degradation": 80.0,
        "phase_imbalance": 70.0,
        "thd_drift": 65.0,
        "overload": 55.0,
        "raw_power_total": 100.0 + np.linspace(0, 10, n),
        "raw_power_factor_avg": 0.88,
        "raw_current_unbalance": 1.5,
    })


# ── Gap 1: time-series intent detection ──────────────────────────────────────

def test_ts_matches_last_n_days():
    from routes.chat import _is_time_series_query
    assert _is_time_series_query("show me e0501 last 7 days") is True

def test_ts_matches_trend():
    from routes.chat import _is_time_series_query
    assert _is_time_series_query("what is the trend for e0501 this week") is True

def test_ts_matches_history():
    from routes.chat import _is_time_series_query
    assert _is_time_series_query("e0501 power history") is True

def test_ts_requires_device_id():
    from routes.chat import _is_time_series_query
    assert _is_time_series_query("show last 7 days of power") is False

def test_ts_no_match_general_question():
    from routes.chat import _is_time_series_query
    assert _is_time_series_query("what is power factor?") is False

def test_ts_no_match_ranking():
    from routes.chat import _is_time_series_query
    assert _is_time_series_query("rank level 5 AHUs by health") is False


# ── Gap 1: param extraction ───────────────────────────────────────────────────

def test_ts_extract_params_device_from_message():
    from routes.chat import _extract_ts_params
    dev, rng = _extract_ts_params("show e0501 last 7 days", None)
    assert dev == "e0501"
    assert rng == "7d"

def test_ts_extract_params_30d():
    from routes.chat import _extract_ts_params
    dev, rng = _extract_ts_params("show e0501 past month", None)
    assert rng == "30d"

def test_ts_extract_params_24h():
    from routes.chat import _extract_ts_params
    dev, rng = _extract_ts_params("e0501 today", None)
    assert rng == "24h"

def test_ts_extract_params_device_from_context():
    from routes.chat import _extract_ts_params
    dev, rng = _extract_ts_params("show trend last 7 days", {"device": "e0301"})
    assert dev == "e0301"


# ── Gap 1: context builder output ────────────────────────────────────────────

def test_ts_summary_returns_section_header():
    from routes.chat import _get_time_series_summary_sync
    df = _make_hourly_df("e0501")
    with patch("core.csv_reader.HOURLY_CSV_PATH", "dummy.csv"), \
         patch("pandas.read_csv", return_value=df), \
         patch("core.csv_reader._filter_time_range", side_effect=lambda d, r: d):
        result = _get_time_series_summary_sync("e0501", "7d")
    assert "Time-Series Summary" in result
    assert "e0501" in result

def test_ts_summary_contains_min_max_mean():
    from routes.chat import _get_time_series_summary_sync
    df = _make_hourly_df("e0501")
    with patch("core.csv_reader.HOURLY_CSV_PATH", "dummy.csv"), \
         patch("pandas.read_csv", return_value=df), \
         patch("core.csv_reader._filter_time_range", side_effect=lambda d, r: d):
        result = _get_time_series_summary_sync("e0501", "7d")
    assert "min=" in result
    assert "max=" in result
    assert "mean=" in result

def test_ts_summary_empty_on_unknown_device():
    from routes.chat import _get_time_series_summary_sync
    df = _make_hourly_df("e0501")
    with patch("core.csv_reader.HOURLY_CSV_PATH", "dummy.csv"), \
         patch("pandas.read_csv", return_value=df), \
         patch("core.csv_reader._filter_time_range", side_effect=lambda d, r: d):
        result = _get_time_series_summary_sync("e9999", "7d")
    assert result == ""


# ── Gap 2: ranking intent detection ──────────────────────────────────────────

def test_ranking_matches_worst():
    from routes.chat import _is_ranking_query
    assert _is_ranking_query("which level 3 AHUs have the worst power factor?") is True

def test_ranking_matches_rank_level():
    from routes.chat import _is_ranking_query
    assert _is_ranking_query("rank level 5 by energy") is True

def test_ranking_matches_most():
    from routes.chat import _is_ranking_query
    assert _is_ranking_query("which unit on level 2 uses the most energy?") is True

def test_ranking_requires_level():
    from routes.chat import _is_ranking_query
    assert _is_ranking_query("rank the worst AHUs by health") is False

def test_ranking_no_match_ts():
    from routes.chat import _is_ranking_query
    assert _is_ranking_query("show e0501 last 7 days") is False


# ── Gap 2: param extraction ───────────────────────────────────────────────────

def test_ranking_extract_level_and_metric():
    from routes.chat import _extract_ranking_params
    level, col, asc = _extract_ranking_params("worst pf on level 3")
    assert level == 3
    assert col == "pf_degradation"

def test_ranking_extract_health_ascending():
    from routes.chat import _extract_ranking_params
    level, col, asc = _extract_ranking_params("worst health on level 5")
    assert col == "health_index"
    assert asc is True  # lowest health = worst → ascending sort

def test_ranking_extract_energy_descending():
    from routes.chat import _extract_ranking_params
    level, col, asc = _extract_ranking_params("most energy use on level 4")
    assert col == "energy_anomaly"
    assert asc is False  # highest energy anomaly = worst → descending


# ── Gap 2: context builder output ─────────────────────────────────────────────

def test_ranking_returns_section_header():
    from routes.chat import _get_ranking_context_sync
    df = pd.concat([
        _make_hourly_df("e0501", "Level 5"),
        _make_hourly_df("e0502", "Level 5"),
    ])
    with patch("core.csv_reader._load_csv", return_value=df):
        result = _get_ranking_context_sync(5, "health_index", True)
    assert "Ranking" in result
    assert "Level 5" in result

def test_ranking_lists_both_devices():
    from routes.chat import _get_ranking_context_sync
    df = pd.concat([
        _make_hourly_df("e0501", "Level 5"),
        _make_hourly_df("e0502", "Level 5"),
    ])
    with patch("core.csv_reader._load_csv", return_value=df):
        result = _get_ranking_context_sync(5, "health_index", True)
    assert "e0501" in result
    assert "e0502" in result

def test_ranking_empty_on_wrong_level():
    from routes.chat import _get_ranking_context_sync
    df = _make_hourly_df("e0501", "Level 5")
    with patch("core.csv_reader._load_csv", return_value=df):
        result = _get_ranking_context_sync(9, "health_index", True)
    assert result == ""


# ── Gap 3: comparison intent detection ───────────────────────────────────────

def test_compare_matches_vs():
    from routes.chat import _is_comparison_query
    assert _is_comparison_query("compare e0501 vs e0101") is True

def test_compare_matches_versus():
    from routes.chat import _is_comparison_query
    assert _is_comparison_query("e0501 versus e0201") is True

def test_compare_matches_compare_keyword():
    from routes.chat import _is_comparison_query
    assert _is_comparison_query("compare e0501 and e0502 health") is True

def test_compare_requires_two_devices():
    from routes.chat import _is_comparison_query
    assert _is_comparison_query("compare e0501") is False

def test_compare_no_match_no_compare_keyword():
    from routes.chat import _is_comparison_query
    assert _is_comparison_query("show e0501 and e0502") is False


# ── Gap 3: device extraction ──────────────────────────────────────────────────

def test_compare_extracts_two_devices():
    from routes.chat import _extract_comparison_devices
    devs = _extract_comparison_devices("compare e0501 vs e0101")
    assert "e0501" in devs
    assert "e0101" in devs
    assert len(devs) == 2

def test_compare_deduplicates():
    from routes.chat import _extract_comparison_devices
    devs = _extract_comparison_devices("compare e0501 vs e0501")
    assert devs.count("e0501") == 1

def test_compare_caps_at_four():
    from routes.chat import _extract_comparison_devices
    devs = _extract_comparison_devices("compare e0501 e0502 e0503 e0504 e0505")
    assert len(devs) <= 4


# ── Gap 3: context builder output ─────────────────────────────────────────────

def test_compare_returns_section_header():
    from routes.chat import _get_comparison_context_sync
    df = pd.concat([
        _make_hourly_df("e0501", "Level 5"),
        _make_hourly_df("e0101", "Level 1"),
    ])
    with patch("pandas.read_csv", return_value=df), \
         patch("core.csv_reader.HOURLY_CSV_PATH", "dummy.csv"):
        result = _get_comparison_context_sync(["e0501", "e0101"])
    assert "Comparison" in result
    assert "e0501" in result
    assert "e0101" in result

def test_compare_contains_table_separator():
    from routes.chat import _get_comparison_context_sync
    df = pd.concat([
        _make_hourly_df("e0501", "Level 5"),
        _make_hourly_df("e0101", "Level 1"),
    ])
    with patch("pandas.read_csv", return_value=df), \
         patch("core.csv_reader.HOURLY_CSV_PATH", "dummy.csv"):
        result = _get_comparison_context_sync(["e0501", "e0101"])
    assert "| --- |" in result

def test_compare_empty_when_only_one_device_found():
    from routes.chat import _get_comparison_context_sync
    df = _make_hourly_df("e0501", "Level 5")
    with patch("pandas.read_csv", return_value=df), \
         patch("core.csv_reader.HOURLY_CSV_PATH", "dummy.csv"):
        result = _get_comparison_context_sync(["e0501", "e9999"])
    assert result == ""
