#!/usr/bin/env python3
"""
generate_summary_report.py
───────────────────────────
Generate comprehensive FAIR health scoring summary report.

This script analyzes the generated health CSV files and produces:
1. Tier distribution per level
2. Top worst AHUs
3. Safety flags summary
4. Scoring metrics breakdown

Usage:
    python scripts/generate_summary_report.py [--range 24h|7d|30d]
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")


def load_data(range_name="24h"):
    """Load health data for specified time range."""
    filepath = DATA_DIR / f"all_levels_health_{range_name}.csv"
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def get_latest_data(range_name="24h"):
    """Get latest timestamp data."""
    df = load_data(range_name)
    latest_ts = df['timestamp'].max()
    return df[df['timestamp'] == latest_ts].copy()


def analyze_tier_distribution(df):
    """Analyze health tier distribution."""
    print("\n" + "="*60)
    print("TIER DISTRIBUTION")
    print("="*60)
    
    # Overall
    total = len(df)
    for tier in ["Healthy", "Monitor", "Maintenance Soon", "Critical"]:
        count = len(df[df['tier'] == tier])
        pct = 100 * count / total if total > 0 else 0
        print(f"  {tier}: {count} ({pct:.1f}%)")


def analyze_by_level(df):
    """Analyze by building level."""
    print("\n" + "="*60)
    print("BY BUILDING LEVEL")
    print("="*60)
    
    levels = sorted(df['level'].unique())
    for level in levels:
        level_data = df[df['level'] == level]
        ahus = level_data['ahu_id'].nunique()
        
        # Health stats
        hi = level_data['health_index']
        avg_hi = hi.mean()
        
        # Tier counts
        tier_counts = level_data['tier'].value_counts().to_dict()
        
        print(f"\n  {level}:")
        print(f"    AHUs: {ahus}")
        print(f"    Avg Health Index: {avg_hi:.1f}")
        print(f"    Tier Distribution:")
        for tier in ["Healthy", "Monitor", "Maintenance Soon", "Critical"]:
            count = tier_counts.get(tier, 0)
            pct = 100 * count / len(level_data) if len(level_data) > 0 else 0
            print(f"      {tier}: {count} ({pct:.1f}%)")


def analyze_top_worst(df, n=5):
    """Get top N worst AHUs."""
    print(f"\n{'='*60}")
    print(f"TOP {n} WORST AHUs (lowest health index)")
    print("="*60)
    
    worst = df.nsmallest(n, 'health_index')
    
    for _, row in worst.iterrows():
        print(f"  {row['ahu_id']} (Level {row['level']})")
        print(f"    Health Index: {row['health_index']:.1f}")
        print(f"    Tier: {row['tier']}")
        
        # Risk scores
        if 'energy_anomaly' in df.columns:
            print(f"    Risk Scores:")
            scores = [
                ('energy_anomaly', row.get('energy_anomaly')),
                ('pf_degradation', row.get('pf_degradation')),
                ('phase_imbalance', row.get('phase_imbalance')),
                ('thd_drift', row.get('thd_drift')),
                ('overload', row.get('overload')),
            ]
            for name, score in scores:
                if pd.notna(score):
                    print(f"      {name}: {score:.4f}")
        print()


def analyze_safety_flags(df):
    """Analyze safety flags distribution."""
    print("\n" + "="*60)
    print("SAFETY FLAGS SUMMARY")
    print("="*60)
    
    all_flags = df['safety_flags'].dropna()
    if len(all_flags) == 0:
        print("  No safety flags found")
        return
    
    flag_counts = {}
    for flags in all_flags:
        if pd.notna(flags) and str(flags).strip() != "":
            for flag in str(flags).split(","):
                flag_counts[flag] = flag_counts.get(flag, 0) + 1
    
    if len(flag_counts) == 0:
        print("  No safety flags found")
        return
    
    # Sort by count descending
    sorted_flags = sorted(flag_counts.items(), key=lambda x: -x[1])
    
    print(f"  Total AHUs with flags: {len(all_flags)}")
    print(f"  Flag Count:")
    
    total_ahus = df['ahu_id'].nunique()
    for flag, count in sorted_flags:
        pct = 100 * count / total_ahus
        print(f"    {flag}: {count} AHUs ({pct:.1f}%)")


def analyze_metrics(df):
    """Analyze scoring metrics breakdown."""
    print("\n" + "="*60)
    print("SCORING METRICS BREAKDOWN")
    print("="*60)
    
    # Required columns for scoring
    required_cols = [
        'energy_anomaly', 'pf_degradation', 'phase_imbalance',
        'thd_drift', 'overload'
    ]
    
    available_cols = [c for c in required_cols if c in df.columns]
    
    print(f"  Analyzing {len(available_cols)} scoring metrics:")
    
    for col in available_cols:
        values = df[col].dropna()
        if len(values) > 0:
            avg_score = values.mean()
            max_score = values.max()
            
            # Count high scores (score > 0.5 means concern)
            high_count = len(values[values > 0.5])
            high_pct = 100 * high_count / len(values)
            
            print(f"\n  {col}:")
            print(f"    Avg Score: {avg_score:.4f}")
            print(f"    Max Score: {max_score:.4f}")
            print(f"    High Scores (>0.5): {high_count} ({high_pct:.1f}%)")


def generate_report(range_name="24h", output_dir=None):
    """Generate complete health report."""
    if output_dir is None:
        output_dir = Path("docs")
    output_dir.mkdir(exist_ok=True)
    
    print("="*60)
    print("FAIR HEALTH SCORING REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Time Range: {range_name.upper()}")
    print("="*60)
    
    # Load data
    df = load_data(range_name)
    latest_df = get_latest_data(range_name)
    
    print(f"\nData Summary:")
    print(f"  Total Rows: {len(df)}")
    print(f"  Unique AHUs: {df['ahu_id'].nunique()}")
    print(f"  Levels: {sorted(df['level'].unique())}")
    
    # Time range
    ts_min = df['timestamp'].min()
    ts_max = df['timestamp'].max()
    print(f"  Time Range: {ts_min} to {ts_max}")
    
    # Generate sections
    analyze_tier_distribution(df)
    analyze_by_level(latest_df)
    analyze_top_worst(latest_df, n=10)
    analyze_safety_flags(latest_df)
    analyze_metrics(latest_df)
    
    # Summary stats
    print("\n" + "="*60)
    print("OVERALL SUMMARY")
    print("="*60)
    
    health_index = df['health_index']
    print(f"  Health Index Range: [{health_index.min():.1f}, {health_index.max():.1f}]")
    print(f"  Mean: {health_index.mean():.1f}")
    print(f"  Median: {health_index.median():.1f}")
    
    # Save to file
    report_path = output_dir / f"FAIR_HEALTH_SCORING_REPORT_{range_name}.md"
    
    # Redirect print output to file
    import sys
    original_stdout = sys.stdout
    
    with open(report_path, 'w') as f:
        sys.stdout = f
        
        print(f"# FAIR Health Scoring Report")
        print(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"**Time Range:** {range_name.upper()}")
        
        print("\n## Data Summary")
        print(f"- **Total Rows:** {len(df)}")
        print(f"- **Unique AHUs:** {df['ahu_id'].nunique()}")
        print(f"- **Levels:** {sorted(df['level'].unique())}")
        print(f"- **Time Range:** {ts_min} to {ts_max}")
        
        # Tier distribution
        print("\n## Health Tier Distribution")
        total = len(df)
        for tier in ["Healthy", "Monitor", "Maintenance Soon", "Critical"]:
            count = len(df[df['tier'] == tier])
            pct = 100 * count / total if total > 0 else 0
            print(f"- **{tier}:** {count} ({pct:.1f}%)")
        
        # Top 5 worst
        print("\n## Top 5 Worst AHUs")
        worst = df.nsmallest(5, 'health_index')
        for _, row in worst.iterrows():
            print(f"- {row['ahu_id']} (Level {row['level']}): {row['health_index']:.1f} ({row['tier']})")
        
        # Safety flags - need to count unique AHUs per flag
        print("\n## Safety Flags")
        
        # Get latest timestamp data for unique AHU counts
        latest_ts = df['timestamp'].max()
        latest_df = df[df['timestamp'] == latest_ts]
        
        if len(latest_df) > 0:
            flag_counts = {}
            for _, row in latest_df.iterrows():
                flags_str = row.get('safety_flags')
                if pd.notna(flags_str) and str(flags_str).strip() != "":
                    for flag in str(flags_str).split(","):
                        if flag.strip():
                            flag_counts[flag] = flag_counts.get(flag, 0) + 1
            
            total_ahus_latest = latest_df['ahu_id'].nunique()
            for flag, count in sorted(flag_counts.items(), key=lambda x: -x[1]):
                pct = 100 * count / total_ahus_latest if total_ahus_latest > 0 else 0
                print(f"- **{flag}:** {count} AHUs ({pct:.1f}%)")
        else:
            print("No safety flags found.")
        
        # Metrics breakdown
        print("\n## Scoring Metrics Breakdown")
        required_cols = [
            'energy_anomaly', 'pf_degradation', 'phase_imbalance',
            'thd_drift', 'overload'
        ]
        
        for col in required_cols:
            if col in df.columns:
                values = df[col].dropna()
                if len(values) > 0:
                    avg_score = values.mean()
                    max_score = values.max()
                    high_count = len(values[values > 0.5])
                    high_pct = 100 * high_count / len(values)
                    
                    print(f"\n### {col}")
                    print(f"- Avg Score: {avg_score:.4f}")
                    print(f"- Max Score: {max_score:.4f}")
                    print(f"- High Scores (>0.5): {high_count} ({high_pct:.1f}%)")
    
    sys.stdout = original_stdout
    
    print(f"\n{'='*60}")
    print(f"Report saved to: {report_path}")
    print("="*60)
    
    return report_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate FAIR health scoring report")
    parser.add_argument("--range", type=str, default="24h",
                       help="Time range: 24h, 7d, or 30d")
    parser.add_argument("--all-ranges", action="store_true",
                       help="Generate report for all time ranges")
    
    args = parser.parse_args()
    
    if args.all_ranges:
        for range_name in ["24h", "7d", "30d"]:
            print(f"\n{'='*60}")
            print(f"  Generating report for {range_name} range")
            print('='*60)
            generate_report(range_name)
    else:
        generate_report(args.range)
