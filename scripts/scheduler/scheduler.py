#!/usr/bin/env python3
"""
scheduler.py — Automated ETL Pipeline Scheduler

Runs both ETL pipelines every 30 minutes:
1. Prediction ETL (upserts predictions to healthdb.duckdb)
2. Health Scoring ETL (uses predictions for scoring)

Usage:
    python scripts/scheduler.py [--interval 30] [--dry-run]

Options:
    --interval MINUTES   Run interval (default: 30)
    --dry-run           Show what would run without executing

Logs:
    logs/prediction_etl.log - Prediction ETL output
    logs/health_etl.log     - Health scoring ETL output
    logs/scheduler.log      - Scheduler activity log

Installation (macOS):
    1. Copy to: ~/Library/LaunchAgents/com.wach.insight.scheduler.plist
    2. Load with: launchctl load ~/Library/LaunchAgents/com.wach.insight.scheduler.plist
    3. Or run manually: python scripts/scheduler.py

Author: WACH Insight Team
"""

import time
import subprocess
import sys
from datetime import datetime, timedelta
import os
import argparse

# Configuration
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
DEFAULT_INTERVAL_MINUTES = 30

# Ensure logs directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

# Log file paths
PREDICTION_LOG = os.path.join(LOGS_DIR, "prediction_etl.log")
HEALTH_LOG = os.path.join(LOGS_DIR, "health_etl.log")
SCHEDULER_LOG = os.path.join(LOGS_DIR, "scheduler.log")


def log_scheduler(message: str):
    """Log a message to scheduler log file."""
    timestamp = datetime.now().isoformat()
    log_line = f"[{timestamp}] {message}\n"
    
    # Write to scheduler log
    with open(SCHEDULER_LOG, "a") as f:
        f.write(log_line)
    
    # Also print to console
    print(log_line.strip())


def run_etl(script_name: str, log_file: str, extra_args: list = None) -> tuple:
    """
    Run an ETL script and return (success, output).
    
    Args:
        script_name: Name of the ETL script (e.g., "run_prediction_etl.py")
        log_file: Path to log file for output
        extra_args: Additional command-line arguments
    
    Returns:
        Tuple of (success: bool, output: str)
    """
    script_path = os.path.join(PROJECT_ROOT, "scripts", "etl", script_name)
    
    # Build command
    cmd = [
        sys.executable,
        script_path,
        "--level", "all"
    ]
    
    if extra_args:
        cmd.extend(extra_args)
    
    try:
        # Run script and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        output = result.stdout + result.stderr
        
        # Write to log file
        with open(log_file, "a") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"\n{'='*70}\n")
            f.write(f"RUN: {timestamp}\n")
            f.write(f"COMMAND: {' '.join(cmd)}\n")
            f.write(f"{'='*70}\n")
            if result.stdout:
                f.write("STDOUT:\n" + result.stdout + "\n")
            if result.stderr:
                f.write("STDERR:\n" + result.stderr + "\n")
            if result.returncode == 0:
                f.write(f"STATUS: SUCCESS\n")
            else:
                f.write(f"STATUS: FAILED (exit code {result.returncode})\n")
        
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        # Write timeout to log
        with open(log_file, "a") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"\n{'='*70}\n")
            f.write(f"RUN: {timestamp}\n")
            f.write(f"COMMAND: {' '.join(cmd)}\n")
            f.write(f"{'='*70}\n")
            f.write("STATUS: TIMEOUT (exceeded 300 seconds)\n")
        
        return False, "ERROR: Command timed out after 300 seconds"
    except Exception as e:
        # Write error to log
        with open(log_file, "a") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"\n{'='*70}\n")
            f.write(f"RUN: {timestamp}\n")
            f.write(f"COMMAND: {' '.join(cmd)}\n")
            f.write(f"{'='*70}\n")
            f.write(f"STATUS: EXCEPTION\n")
            f.write(f"ERROR: {str(e)}\n")
        
        return False, f"ERROR: {str(e)}"


def run_prediction_etl(dry_run: bool = False) -> tuple:
    """Run the prediction ETL pipeline."""
    if dry_run:
        log_scheduler("[DRY-RUN] Would run: run_prediction_etl.py")
        return True, "Dry run - no execution"
    
    log_scheduler("Starting Prediction ETL...")
    success, output = run_etl(
        "run_prediction_etl.py",
        PREDICTION_LOG,
        extra_args=["--level", "all"]
    )
    
    if success:
        log_scheduler("Prediction ETL completed successfully")
    else:
        log_scheduler(f"Prediction ETL failed: {output[:200]}")
    
    return success, output


def run_health_etl(dry_run: bool = False) -> tuple:
    """Run the health scoring ETL pipeline."""
    if dry_run:
        log_scheduler("[DRY-RUN] Would run: run_health_etl.py")
        return True, "Dry run - no execution"
    
    log_scheduler("Starting Health Scoring ETL...")
    success, output = run_etl(
        "run_health_etl.py",
        HEALTH_LOG,
        extra_args=["--level", "all"]
    )
    
    if success:
        log_scheduler("Health Scoring ETL completed successfully")
    else:
        log_scheduler(f"Health Scoring ETL failed: {output[:200]}")
    
    return success, output


def main():
    """Main scheduler loop."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Automated ETL Pipeline Scheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/scheduler.py                    # Run every 30 minutes
  python scripts/scheduler.py --interval 60     # Run every hour
  python scripts/scheduler.py --dry-run         # Show what would run
        """
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_MINUTES,
        help=f"Run interval in minutes (default: {DEFAULT_INTERVAL_MINUTES})"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would run without executing"
    )
    
    parser.add_argument(
        "--one-shot",
        action="store_true",
        help="Run once and exit (for testing)"
    )
    
    args = parser.parse_args()
    
    # Validate interval
    if args.interval < 5:
        print(f"ERROR: Interval must be at least 5 minutes, got {args.interval}")
        sys.exit(1)
    
    # Start scheduler
    log_scheduler("=" * 70)
    log_scheduler("WACH Insight ETL Scheduler Started")
    log_scheduler("=" * 70)
    log_scheduler(f"  Interval: Every {args.interval} minutes")
    log_scheduler(f"  Prediction ETL Log: {PREDICTION_LOG}")
    log_scheduler(f"  Health Scoring Log: {HEALTH_LOG}")
    log_scheduler(f"  Dry Run Mode: {args.dry_run}")
    log_scheduler("")
    
    # Log startup info
    if args.dry_run:
        log_scheduler("[DRY-RUN] Prediction ETL would run:")
        log_scheduler("  - Fetch hourly energy data for all AHUs")
        log_scheduler("  - Compute predictions using 3-slot average")
        log_scheduler("  - Upsert to DuckDB predictions table")
        log_scheduler("")
        log_scheduler("[DRY-RUN] Health Scoring ETL would run:")
        log_scheduler("  - Resume from latest DuckDB timestamp")
        log_scheduler("  - Fetch new metrics from InfluxDB")
        log_scheduler("  - Compute FAIR health scores for all AHUs")
        log_scheduler("  - Upsert to DuckDB health_hourly table")
    else:
        log_scheduler(f"Scheduler PID: {os.getpid()}")
        log_scheduler("")
    
    # Main loop
    iteration = 0
    while True:
        iteration += 1
        
        if args.dry_run and iteration > 1:
            break
            
        start_time = datetime.now()
        
        log_scheduler("-" * 70)
        log_scheduler(f"Iteration {iteration} - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        log_scheduler("-" * 70)
        
        # Run Prediction ETL
        if iteration == 1 or not args.dry_run:
            log_scheduler("")
            success, output = run_prediction_etl(dry_run=args.dry_run)
            
            if not success:
                log_scheduler(f"  ⚠️  Prediction ETL had issues (see {PREDICTION_LOG})")
        
        # Run Health Scoring ETL
        if iteration == 1 or not args.dry_run:
            log_scheduler("")
            success, output = run_health_etl(dry_run=args.dry_run)
            
            if not success:
                log_scheduler(f"  ⚠️  Health Scoring ETL had issues (see {HEALTH_LOG})")
        
        # Calculate wait time
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Only log timing after first real run
        if iteration > 1 or not args.dry_run:
            wait_time = max(0, args.interval * 60 - elapsed)
            
            log_scheduler("")
            log_scheduler(f"  Iteration completed in {elapsed:.1f} seconds")
            log_scheduler(f"  Next run in {wait_time:.0f} seconds ({wait_time/60:.1f} minutes)")
        
        # Exit after one iteration if --one-shot
        if args.one_shot:
            log_scheduler("")
            log_scheduler("One-shot mode: Exiting")
            break
        
        # Exit if dry-run
        if args.dry_run:
            log_scheduler("")
            log_scheduler("Dry run: Exiting")
            break
        
        # Sleep until next run
        time.sleep(wait_time)


if __name__ == "__main__":
    main()
