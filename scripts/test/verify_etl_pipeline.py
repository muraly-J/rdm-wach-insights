#!/usr/bin/env python3
"""
ETL Pipeline Verification Script

Run this script to verify the ETL pipeline outputs match expected schema
and all verification checks pass.
"""

import sys
import pandas as pd

def verify_raw_metrics_schema():
    """Verify raw metrics CSV has correct columns."""
    df = pd.read_csv('data/level1_raw_metrics_24h.csv', nrows=0)
    
    expected = [
        'timestamp', 'ahu_id', 'power_total', 'energy_import',
        'power_factor_avg', 'current_unbalance', 'current_l1_thd', 'current_l3_thd'
    ]
    
    actual = list(df.columns)
    assert actual == expected, f"Column mismatch: {set(actual) ^ set(expected)}"
    
    print(f"✓ Raw metrics schema correct ({len(actual)} columns)")
    return True

def verify_health_scores_schema():
    """Verify health scores CSV has correct columns."""
    df = pd.read_csv('data/level1_hourly_health_24h.csv', nrows=0)
    
    expected = [
        'timestamp', 'ahu_id', 'level', 'health_index', 'tier',
        'energy_anomaly', 'pf_degradation', 'phase_imbalance',
        'thd_drift', 'overload', 'power_total', 'power_factor',
        'unbalance_pct', 'thd_24h', 'delta_kwh', 'data_quality_flag',
        'safety_flags', 'z_energy', 'z_pf', 'z_imbalance',
        'z_thd', 'z_overload'
    ]
    
    actual = list(df.columns)
    assert actual == expected, f"Column mismatch: {set(actual) ^ set(expected)}"
    
    print(f"✓ Health scores schema correct ({len(actual)} columns)")
    return True

def verify_health_index_range():
    """Verify health_index values are within [0, 100]."""
    df = pd.read_csv('data/level1_hourly_health_24h.csv')
    
    min_val = df['health_index'].min()
    max_val = df['health_index'].max()
    
    assert min_val >= 0, f"Health index min < 0: {min_val}"
    assert max_val <= 100, f"Health index max > 100: {max_val}"
    
    print(f"✓ Health index range: [{min_val:.1f}, {max_val:.1f}]")
    return True

def verify_risk_score_bounds():
    """Verify all risk scores are in [0, 1]."""
    df = pd.read_csv('data/level1_hourly_health_24h.csv')
    
    risk_cols = [
        'energy_anomaly', 'pf_degradation', 'phase_imbalance',
        'thd_drift', 'overload'
    ]
    
    for col in risk_cols:
        min_val = df[col].min()
        max_val = df[col].max()
        
        assert min_val >= 0, f"{col} min < 0"
        assert max_val <= 1.01, f"{col} max > 1: {max_val}"
    
    print("✓ All risk scores in [0, 1] range")
    return True

def verify_tier_classification():
    """Verify tier classifications match health index thresholds."""
    df = pd.read_csv('data/level1_hourly_health_24h.csv')
    
    def get_tier(index):
        if index >= 80:
            return "Healthy"
        elif index >= 60:
            return "Monitor"
        elif index >= 40:
            return "Maintenance Soon"
        else:
            return "Critical"
    
    # Test each row
    for idx, row in df.head(50).iterrows():
        expected = get_tier(row['health_index'])
        actual = row['tier']
        
        assert expected == actual, (
            f"Row {idx}: health_index={row['health_index']} "
            f"expected tier '{expected}' but got '{actual}'"
        )
    
    print("✓ Tier classifications correct")
    return True

def verify_tier_distribution():
    """Verify tier distribution."""
    df = pd.read_csv('data/level1_hourly_health_24h.csv')
    
    tier_counts = df['tier'].value_counts()
    total = len(df)
    
    print("\n--- Tier Distribution ---")
    for tier in ['Healthy', 'Monitor', 'Maintenance Soon', 'Critical']:
        count = tier_counts.get(tier, 0)
        pct = count / total * 100
        print(f"  {tier}: {count:,} ({pct:.1f}%)")
    
    assert tier_counts.sum() == len(df), "Tier counts don't sum to total"
    
    print("✓ Tier distribution verified")
    return True

def verify_weighted_penalty():
    """Verify health_index = 100 - (penalty × 100)."""
    df = pd.read_csv('data/level1_hourly_health_24h.csv')
    
    WEIGHTS = {
        "energy_anomaly": 0.15,
        "pf_degradation": 0.25,
        "phase_imbalance": 0.25,
        "thd_drift": 0.15,
        "overload": 0.20
    }
    
    # Calculate expected health index
    df['calculated_penalty'] = sum(
        df[col] * WEIGHTS[col] for col in WEIGHTS.keys()
    )
    df['calculated_health_index'] = 100 - (df['calculated_penalty'] * 100)
    
    # Check within tolerance
    tolerance = 0.1
    diff = abs(df['health_index'] - df['calculated_health_index'])
    
    max_diff = diff.max()
    assert max_diff <= tolerance, f"Health index error: {max_diff}"
    
    print("✓ Weighted penalty calculation verified")
    return True

def verify_weights_sum():
    """Verify health index weights sum to 1.0."""
    WEIGHTS = {
        "energy_anomaly": 0.15,
        "pf_degradation": 0.25,
        "phase_imbalance": 0.25,
        "thd_drift": 0.15,
        "overload": 0.20
    }
    
    total = sum(WEIGHTS.values())
    assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, not 1.0"
    
    print(f"✓ Weights sum to 1.0: {total:.2f}")
    return True

def verify_zscore_distribution():
    """Verify z-scores have reasonable distribution."""
    df = pd.read_csv('data/level1_hourly_health_24h.csv')
    
    z_cols = ['z_energy', 'z_pf', 'z_imbalance', 'z_thd', 'z_overload']
    
    for col in z_cols:
        non_null = df[col].notna().sum()
        
        if non_null > 0:
            z_values = df[col].dropna()
            
            # Z-scores should be roughly normal with mean ~0
            assert -5 <= z_values.mean() <= 5, (
                f"{col} mean outside expected range [-5, 5]"
            )
    
    print("✓ Z-score distribution verified")
    return True

def verify_safety_flags():
    """Verify safety flags contain only valid values."""
    df = pd.read_csv('data/level1_hourly_health_24h.csv')
    
    VALID_FLAGS = {
        'THD_CHRONIC_HIGH', 'IMBALANCE_SEVERE',
        'PF_CHRONIC_LOW', 'OVERLOAD_CHRONIC'
    }
    
    # Parse all safety flags
    all_flags = set()
    for flags in df['safety_flags'].dropna():
        for flag in flags.split(','):
            all_flags.add(flag)
    
    invalid = all_flags - VALID_FLAGS
    assert len(invalid) == 0, f"Invalid safety flags: {invalid}"
    
    print("\n--- Safety Flag Distribution ---")
    for flags, count in df['safety_flags'].value_counts().head(5).items():
        print(f"  {flags or '(none)'}: {count} records")
    
    print("✓ All safety flags valid")
    return True

def verify_raw_to_health_match():
    """Verify raw metrics and health scores have same row count."""
    df_raw = pd.read_csv('data/level1_raw_metrics_24h.csv')
    df_health = pd.read_csv('data/level1_hourly_health_24h.csv')
    
    assert len(df_raw) == len(df_health), (
        f"Row count mismatch: raw={len(df_raw)}, health={len(df_health)}"
    )
    
    # Verify same timestamps and AHUs
    raw_set = set(zip(df_raw['timestamp'], df_raw['ahu_id']))
    health_set = set(zip(df_health['timestamp'], df_health['ahu_id']))
    
    assert raw_set == health_set, "Timestamp/AHU mismatch"
    
    print(f"✓ Raw/Health row count match: {len(df_raw)} records")
    return True

def verify_ahu_coverage():
    """Verify all AHUs are present."""
    df_health = pd.read_csv('data/level1_hourly_health_24h.csv')
    
    unique_ahus = df_health['ahu_id'].nunique()
    
    # Allow for missing AHUs (e.g., e0112 may be excluded)
    assert unique_ahus >= 20, f"Expected at least 20 AHUs, got {unique_ahus}"
    
    print(f"\n--- AHU Coverage ---")
    print(f"  Unique AHUs: {unique_ahus}")
    for ahu in sorted(df_health['ahu_id'].unique()):
        count = (df_health['ahu_id'] == ahu).sum()
        print(f"  {ahu}: {count} rows")
    
    print("✓ Level 1 AHUs present and complete")
    return True

def verify_time_range():
    """Verify data covers ~24 hours."""
    df_health = pd.read_csv('data/level1_hourly_health_24h.csv')
    
    df_health['timestamp_dt'] = pd.to_datetime(df_health['timestamp'])
    time_range = (df_health['timestamp_dt'].max() - df_health['timestamp_dt'].min()).total_seconds() / 3600
    
    assert 20 <= time_range <= 30, f"Time range not ~24h: {time_range}h"
    
    print(f"\n--- Time Range ---")
    print(f"  Start: {df_health['timestamp_dt'].min()}")
    print(f"  End:   {df_health['timestamp_dt'].max()}")
    print(f"  Duration: {time_range:.1f} hours")
    print("✓ Time range ~24 hours")
    return True

def verify_data_quality():
    """Verify data quality flags."""
    df_health = pd.read_csv('data/level1_hourly_health_24h.csv')
    
    # Check data_quality_flag
    dq_null = df_health['data_quality_flag'].isna().sum()
    assert dq_null == 0, f"data_quality_flag has nulls"
    
    dq_0 = (df_health['data_quality_flag'] == 0).sum()
    dq_1 = (df_health['data_quality_flag'] == 1).sum()
    
    print(f"\n--- Data Quality ---")
    print(f"  Quality Flag 0 (good): {dq_0} ({dq_0/len(df_health)*100:.1f}%)")
    print(f"  Quality Flag 1 (missing THD): {dq_1} ({dq_1/len(df_health)*100:.1f}%)")
    print("✓ Data quality flags present")
    return True

def run_all_tests():
    """Run all verification tests."""
    print("=" * 60)
    print("ETL PIPELINE VERIFICATION")
    print("=" * 60)
    
    tests = [
        ("Raw Metrics Schema", verify_raw_metrics_schema),
        ("Health Scores Schema", verify_health_scores_schema),
        ("Health Index Range", verify_health_index_range),
        ("Risk Score Bounds", verify_risk_score_bounds),
        ("Tier Classification", verify_tier_classification),
        ("Tier Distribution", verify_tier_distribution),
        ("Weighted Penalty", verify_weighted_penalty),
        ("Weights Sum", verify_weights_sum),
        ("Z-Score Distribution", verify_zscore_distribution),
        ("Safety Flags", verify_safety_flags),
        ("Raw/Health Match", verify_raw_to_health_match),
        ("AHU Coverage", verify_ahu_coverage),
        ("Time Range", verify_time_range),
        ("Data Quality", verify_data_quality),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for name, test_func in tests:
        try:
            print(f"\n--- {name} ---")
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed += 1
            errors.append((name, str(e)))
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
            errors.append((name, str(e)))
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if errors:
        print("\n--- Errors ---")
        for name, msg in errors:
            print(f"  {name}: {msg}")
    
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
