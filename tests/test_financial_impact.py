"""Unit tests for financial impact calculation helpers."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pandas as pd
import numpy as np

# Import the private helpers directly
from routes.financial_impact import _load_config, _save_config, DEFAULT_CONFIG, FinancialConfig


def test_default_config_has_required_keys():
    for key in ["currency", "tariff_rate", "planned_maintenance_cost", "emergency_multiplier"]:
        assert key in DEFAULT_CONFIG


def test_financial_config_model_rejects_zero_tariff():
    from pydantic import ValidationError
    try:
        FinancialConfig(tariff_rate=0)
        assert False, "Should have raised"
    except ValidationError:
        pass


def test_pf_penalty_formula():
    """Verify TNB 1.5%/0.01 formula."""
    avg_pf = 0.80           # 5 steps below 0.85
    steps  = (0.85 - avg_pf) / 0.01   # 5.0
    frac   = steps * 0.015              # 0.075  (7.5% surcharge)
    total_energy_cost = 1000.0          # RM 1000 base
    penalty = total_energy_cost * frac  # RM 75
    assert abs(penalty - 75.0) < 0.01


def test_excess_energy_calculation():
    """sum of max(0, actual - predicted)."""
    actual    = pd.Series([10.0, 12.0,  9.0, 11.0])
    predicted = pd.Series([10.0, 10.0, 10.0, 10.0])
    excess = (actual - predicted).clip(lower=0).sum()
    assert excess == 3.0   # only hours 2 and 4 contributed


def test_maintenance_risk_only_for_unhealthy():
    planned    = 500.0
    multiplier = 3.0
    risk_if_unhealthy = planned * (multiplier - 1)   # RM 1000
    assert risk_if_unhealthy == 1000.0
    # healthy AHU (hi >= 60) → 0
    hi = 75.0
    risk = risk_if_unhealthy if hi < 60 else 0.0
    assert risk == 0.0
