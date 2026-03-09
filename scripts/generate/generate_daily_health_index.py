#!/usr/bin/env python3
"""
generate_daily_health_index.py
───────────────────────────────
Generate daily health index data for Level 1 AHUs and output to CSV.

This script:
1. Fetches all Level 1 AHU IDs from the system
2. For each AHU, computes hourly health indices for the past N days
3. Aggregates to daily averages (for 7d/30d ranges)
4. Outputs CSV with columns:
   - timestamp (hourly or daily)
   - ahu_id
   - health_index
   - energy_score, pf_score, imbalance_score, thd_score, overload_score

Usage:
    python3 generate_daily_health_index.py [--level 1] [--range last_24h|last_7d|last_30d]

Example:
    # Generate 24h hourly data for Level 1
    python3 generate_daily_health_index.py --level 1 --range last_24h

    # Generate 7d daily data for Level 1
    python3 generate_daily_health_index.py --level 1 --range last_7d

    # Generate 30d daily data for Level 1
    python3 generate_daily_health_index.py --level 1 --range last_30d

Output:
    ahu_health_daily_level1_24h.csv or similar
"""

import argparse
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.core.risk_engine import generate_fleet_risk_assessment
from backend.models.schemas import ALLOWED_DEVICES


def get_level1_ahu_ids():
    """Get all Level 1 AHU IDs (e01xx)."""
    level1_devices = [d for d in ALLOWED_DEVICES if d.startswith("e01")]
    return sorted(level1_devices)


def generate_daily_health_index(level=1, time_range="last_24h", output_dir=None):
    """
    Generate daily health index data for specified level and time range.

    Args:
        level: Building level number (default: 1)
        time_range: Time period - "last_24h", "last_7d", or "last_30d"
        output_dir: Directory to save CSV (default: backend/data/)

    Returns:
        Path to generated CSV file
    """
    # Get Level 1 devices
    level_prefix = f"e{str(level).zfill(2)}"
    devices = get_level1_ahu_ids()

    if not devices:
        print(f"No Level {level} devices found")
        return None

    print(f"Generating daily health index for {len(devices)} Level {level} AHUs")
    print(f"Time range: {time_range}")

    # Run fleet risk assessment
    result = generate_fleet_risk_assessment(
        time_range=time_range,
        cluster_by_level=False,  # Don't cluster for CSV output
        devices_filter=devices
    )

    assessments = result.get("assessments", [])
    print(f"Generated {len(assessments)} assessments")

    if not assessments:
        print("No assessments generated. Check the time range or data availability.")
        return None

    # Build rows with all required fields
    rows = []
    for assessment in assessments:
        ahu_id = assessment.get("ahu_id")
        timestamp_str = assessment.get("timestamp")
        health_index = round(assessment.get("health_index", 100), 1)

        # Get component scores from risk_scores
        risk_scores = assessment.get("risk_scores", {})
        energy_score = round(risk_scores.get("energy_anomaly", 0.0), 4)
        pf_score = round(risk_scores.get("power_factor", 0.0), 4)
        imbalance_score = round(risk_scores.get("phase_imbalance", 0.0), 4)
        thd_score = round(risk_scores.get("thd_drift", 0.0), 4)
        overload_score = round(risk_scores.get("overload", 0.0), 4)

        rows.append({
            "timestamp": timestamp_str,
            "ahu_id": ahu_id,
            "health_index": health_index,
            "energy_score": energy_score,
            "pf_score": pf_score,
            "imbalance_score": imbalance_score,
            "thd_score": thd_score,
            "overload_score": overload_score
        })

    # Sort by timestamp then ahu_id for consistent ordering
    rows.sort(key=lambda x: (x["timestamp"], x["ahu_id"]))

    # Determine output filename based on time range
    if "24h" in time_range:
        range_label = "24h"
        # Hourly data - keep all rows
    elif "7d" in time_range:
        range_label = "7d"
        # For 7d, we would aggregate to daily - but risk_engine already does this
    elif "30d" in time_range:
        range_label = "30d"
    else:
        range_label = "custom"

    # Create output directory if needed
    if output_dir is None:
        output_dir = Path("backend/data")
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp_now = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"ahu_health_daily_level{level}_{range_label}_{timestamp_now}.csv"

    # Write CSV
    fieldnames = [
        "timestamp", "ahu_id", "health_index",
        "energy_score", "pf_score", "imbalance_score",
        "thd_score", "overload_score"
    ]

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {output_file} with {len(rows)} rows")
    return str(output_file)


def generate_hourly_series(level=1, hours_back=24):
    """
    Generate hourly health index data for specified level and hours.

    This version fetches raw hourly data and computes scores at each hour.
    Used for the 24h time range where we want hourly granularity.

    Args:
        level: Building level number
        hours_back: How many hours to go back

    Returns:
        Path to generated CSV file
    """
    # Get Level 1 devices
    level_prefix = f"e{str(level).zfill(2)}"
    devices = [d for d in ALLOWED_DEVICES if d.startswith(level_prefix)]
    devices = sorted(devices)

    if not devices:
        print(f"No Level {level} devices found")
        return None

    print(f"Generating hourly health index for {len(devices)} Level {level} AHUs")
    print(f"Hours back: {hours_back}")

    # Get the timestamp for now
    from datetime import timezone, timedelta as td

    current_time = datetime.now()

    # Fetch data for each hour in the range
    all_rows = []

    from backend.core.influx_client import fetch_time_series

    for hours in range(hours_back, 0, -1):
        # Calculate the timestamp for this hour
        target_hour = current_time - td(hours=hours)
        # Snap to the top of the hour
        target_hour = target_hour.replace(minute=0, second=0, microsecond=0)

        # For each device, compute health index at this point in time
        for ahu_id in devices:
            try:
                # Fetch energy data to compute delta_kwh
                energy_df = fetch_time_series(
                    device_ids=[ahu_id],
                    metric="energy_import",
                    time_range="last_30d"  # Get enough history for delta calculation
                )

                if energy_df.empty:
                    continue

                # Find the row at or before target_hour
                energy_df = energy_df.sort_index()
                eligible_rows = energy_df[energy_df.index <= target_hour]

                if len(eligible_rows) < 2:
                    continue

                # Get current and previous energy values
                current_energy = float(eligible_rows.iloc[-1][ahu_id])
                prev_energy = float(eligible_rows.iloc[-2][ahu_id])

                # Delta kWh
                delta_kwh = current_energy - prev_energy
                if delta_kwh < 0:
                    continue

                # Get other metrics at this timestamp
                power_df = fetch_time_series(
                    device_ids=[ahu_id],
                    metric="power_total",
                    time_range="last_30d"
                )

                if power_df.empty:
                    continue

                power_df = power_df.sort_index()
                eligible_power = power_df[power_df.index <= target_hour]

                if len(eligible_power) < 1:
                    continue

                current_power = float(eligible_power.iloc[-1][ahu_id])

                # Get power factor
                pf_df = fetch_time_series(
                    device_ids=[ahu_id],
                    metric="power_factor_avg",
                    time_range="last_30d"
                )

                pf_value = None
                if not pf_df.empty:
                    pf_df = pf_df.sort_index()
                    eligible_pf = pf_df[pf_df.index <= target_hour]
                    if len(eligible_pf) >= 1:
                        pf_value = float(eligible_pf.iloc[-1][ahu_id])

                # Get unbalance
                unbalance_df = fetch_time_series(
                    device_ids=[ahu_id],
                    metric="current_unbalance",
                    time_range="last_30d"
                )

                unbalance_value = None
                if not unbalance_df.empty:
                    unbalance_df = unbalance_df.sort_index()
                    eligible_unbal = unbalance_df[unbalance_df.index <= target_hour]
                    if len(eligible_unbal) >= 1:
                        unbalance_value = float(eligible_unbal.iloc[-1][ahu_id])

                # Get THD
                thd_l1_df = fetch_time_series(
                    device_ids=[ahu_id],
                    metric="current_l1_thd",
                    time_range="last_30d"
                )

                thd_value = None
                if not thd_l1_df.empty:
                    thd_l1_df = thd_l1_df.sort_index()
                    eligible_thd = thd_l1_df[thd_l1_df.index <= target_hour]
                    if len(eligible_thd) >= 1:
                        thd_value = float(eligible_thd.iloc[-1][ahu_id])

                # If we have all the data, compute health index
                if delta_kwh is not None and current_power is not None:
                    # For MVP, use simplified score calculation
                    # In production, this would use the full risk_engine logic

                    # Simple health index calculation for MVP
                    base_index = 100.0
                    penalties = []

                    # Energy penalty
                    if delta_kwh > 0:
                        historical_median = energy_df[ahu_id].diff().median()
                        if historical_median and historical_median > 0:
                            deviation = (delta_kwh - historical_median) / historical_median
                            if deviation > 0:
                                penalties.append(0.15 * min(deviation, 1.0))
                            else:
                                penalties.append(0.15 * min(abs(deviation), 1.0))

                    # Power factor penalty
                    if pf_value is not None:
                        if pf_value < 0.87:
                            penalties.append(0.25 * ((0.87 - pf_value) / 0.87))

                    # Imbalance penalty
                    if unbalance_value is not None:
                        if unbalance_value > 2.0:
                            penalties.append(0.25 * min((unbalance_value - 2.0) / 3.0, 1.0))

                    # THD penalty
                    if thd_value is not None:
                        if thd_value > 3.5:
                            penalties.append(0.15 * min((thd_value - 3.5) / 1.5, 1.0))

                    # Overload penalty
                    historical_p99 = power_df[ahu_id].quantile(0.99)
                    if historical_p99 and current_power / historical_p99 > 0.85:
                        penalties.append(0.20 * min(current_power / historical_p99 - 0.85, 1.0))

                    health_index = max(0, min(100, base_index - sum(penalties) * 100))

                    all_rows.append({
                        "timestamp": target_hour.isoformat(),
                        "ahu_id": ahu_id,
                        "health_index": round(health_index, 1),
                        "energy_score": round(penalties[0] if len(penalties) > 0 and "energy" in str(penalties[0]) else 0, 4),
                        "pf_score": round(penalties[1] if len(penalties) > 1 else 0, 4),
                        "imbalance_score": round(penalties[2] if len(penalties) > 2 else 0, 4),
                        "thd_score": round(penalties[3] if len(penalties) > 3 else 0, 4),
                        "overload_score": round(penalties[4] if len(penalties) > 4 else 0, 4)
                    })

            except Exception as e:
                # Skip devices with errors
                print(f"  Error processing {ahu_id}: {e}")
                continue

    # Sort by timestamp then ahu_id
    all_rows.sort(key=lambda x: (x["timestamp"], x["ahu_id"]))

    # Output file
    output_dir = Path("backend/data")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp_now = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"ahu_health_hourly_level{level}_{timestamp_now}.csv"

    fieldnames = [
        "timestamp", "ahu_id", "health_index",
        "energy_score", "pf_score", "imbalance_score",
        "thd_score", "overload_score"
    ]

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Generated {output_file} with {len(all_rows)} rows")
    return str(output_file)


def main():
    parser = argparse.ArgumentParser(
        description="Generate daily health index data for AHUs"
    )
    parser.add_argument(
        "--level",
        type=int,
        default=1,
        help="Building level (default: 1)"
    )
    parser.add_argument(
        "--range",
        type=str,
        default="last_24h",
        choices=["last_24h", "last_7d", "last_30d"],
        help="Time range (default: last_24h)"
    )
    parser.add_argument(
        "--hourly",
        action="store_true",
        help="Generate hourly series instead of daily"
    )
    parser.add_argument(
        "--hours-back",
        type=int,
        default=24,
        help="Hours back for hourly generation (default: 24)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for CSV files"
    )

    args = parser.parse_args()

    if args.hourly:
        output_file = generate_hourly_series(
            level=args.level,
            hours_back=args.hours_back
        )
    else:
        output_file = generate_daily_health_index(
            level=args.level,
            time_range=args.range,
            output_dir=args.output_dir
        )

    if output_file:
        print(f"\nOutput: {output_file}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
