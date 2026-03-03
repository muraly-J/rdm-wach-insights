#!/usr/bin/env python3
"""Test scoring functions clamp correctly."""
import sys
sys.path.insert(0, 'backend')

from core.risk_engine import (
    power_factor_risk_score,
    phase_imbalance_risk_score,
    thd_risk_score,
    clamp01
)

# Test with extreme values that would cause overflow
print('Testing scoring function clamping...')
print('=' * 60)

# Test power_factor_risk_score with extreme values
result = power_factor_risk_score(
    current_pf=0.3,  # Very low PF
    ahu_mean_pf=0.9,
    ahu_std_pf=0.01,
    fleet_median_pf=0.9,
    fleet_p5_pf=0.85,
    pf_slope_7d_normalized=10.0,  # Extreme slope
    power_ratio=2.0,
    current_power=100,
    ahu_mean_power=50
)
print(f'power_factor_risk_score (extreme): {result:.6f}')
assert 0 <= result <= 1, f'Score {result} out of [0,1] range!'

# Test phase_imbalance_risk_score
result = phase_imbalance_risk_score(
    current_unbalance=50.0,  # Extreme unbalance
    ahu_mean_unbalance=2.0,
    ahu_std_unbalance=0.1,
    fleet_median_unbalance=3.0,
    fleet_p95_unbalance=5.0,
    unbalance_slope_7d_normalized=20.0  # Extreme slope
)
print(f'phase_imbalance_risk_score (extreme): {result:.6f}')
assert 0 <= result <= 1, f'Score {result} out of [0,1] range!'

# Test thd_risk_score
result = thd_risk_score(
    composite_thd_24h_mean=97.0,  # Extreme THD
    ahu_mean_thd=15.0,
    ahu_std_thd=3.0,
    fleet_median_thd=2.5,
    fleet_p95_thd=4.0,
    thd_slope_7d_normalized=20.0  # Extreme slope
)
print(f'thd_risk_score (extreme): {result:.6f}')
assert 0 <= result <= 1, f'Score {result} out of [0,1] range!'

print('=' * 60)
print('All scoring functions correctly clamp scores to [0,1]!')
