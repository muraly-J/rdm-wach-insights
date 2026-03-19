# ETL Pipeline Automation Architecture

**Date:** March 6, 2026  
**Version:** 1.0

---

## Overview

Both ETL pipelines run automatically every 30 minutes using a Python-based scheduler that maintains a continuous loop.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    SCHEDULER (scheduler.py)                 │
│  Runs continuously, wakes up every 30 minutes               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    PREDICTION ETL                           │
│  1. Fetch hourly energy data from InfluxDB                 │
│  2. Compute predictions: ŷ(t) = avg(yesterday, last_week, │
│     two_weeks)                                              │
│  3. Compute delta_kwh = E(t) - ŷ(t)                        │
│  4. Write to: data/predictions.csv                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    HEALTH SCORING ETL                       │
│  1. Fetch latest metrics from InfluxDB                     │
│  2. Load predictions.csv (from Prediction ETL)             │
│  3. Compute FAIR health scores using prediction deltas     │
│  4. Write to: data/health_all_levels.csv                   │
└─────────────────────────────────────────────────────────────┘
```

---

## The Scheduler (`scripts/scheduler.py`)

### How It Works

```python
def main():
    """Main scheduler loop."""
    iteration = 0
    
    while True:  # Run forever
        start_time = datetime.now()
        iteration += 1
        
        log_scheduler(f"Iteration {iteration} started")
        
        # 1. Run Prediction ETL
        log_scheduler("Starting Prediction ETL...")
        success, output = run_etl("run_prediction_etl.py", ...)
        
        # 2. Run Health Scoring ETL
        log_scheduler("Starting Health Scoring ETL...")
        success, output = run_etl("run_health_etl.py", ...)
        
        # 3. Calculate wait time
        elapsed = (datetime.now() - start_time).total_seconds()
        wait_time = 30 * 60 - elapsed  # 1800 seconds - elapsed
        
        log_scheduler(f"Next run in {wait_time} seconds")
        
        # 4. Sleep until next interval
        time.sleep(wait_time)
```

### Loop Timeline

| Time | Action |
|------|--------|
| 00:00 | Start iteration 1 |
| 00:00-00:45 | Run Prediction ETL (fetch data → compute predictions → write CSV) |
| 00:45-01:30 | Run Health Scoring ETL (fetch metrics → compute scores → write CSV) |
| 01:30 | Calculate wait time, sleep for ~28.5 minutes |
| 01:59 | Wake up and repeat iteration 2 |

**Note:** The actual interval is ~28.5 minutes (not exactly 30) because ETL pipelines take ~1-2 minutes to run.

---

## How CSVs Are Generated Fresh Every 30 Minutes

### Step 1: Prediction ETL Writes New Data

```python
# scripts/run_prediction_etl.py
def run_prediction_etl(level_filter=None, output_path=None, dry_run=False):
    """Run the complete prediction ETL pipeline."""
    
    # Step 1: EXTRACT - Fetch hourly data
    df_raw = extract_prediction_data(device_ids)
    
    # Step 2: TRANSFORM - Compute predictions
    df['predicted_kwh'] = df.apply(compute_predicted, axis=1)
    # Formula: ŷ(t) = avg(yesterday_kwh, last_week_kwh, two_weeks_kwh)
    
    df['delta_kwh'] = df.apply(compute_delta, axis=1)
    # Formula: Δkwh = E(t) - ŷ(t)
    
    # Step 3: LOAD - Append to CSV
    load_to_csv(df_predictions, output_path)
```

**What happens to the CSV:**
- The CSV is **appended**, not replaced
- Each run adds new rows with current timestamp
- Data grows over time: 121 AHUs × ~48 runs/day = ~5,800+ rows/day

### Step 2: Health Scoring ETL Reads Predictions

```python
# scripts/run_health_etl.py
def run_etl_pipeline(output_path=None, dry_run=False, level=None):
    """Run the complete ETL pipeline."""
    
    # Step 1: EXTRACT - Fetch metrics from InfluxDB
    df_raw = extract_raw_data(level_filter=level)
    
    # Step 2: TRANSFORM - Compute health scores
    for ahu_id in device_ids:
        # Load prediction deltas from CSV
        pred_df = pd.read_csv("data/predictions.csv")
        
        # Get latest delta for this AHU
        latest_delta = pred_df[pred_df['ahu_id'] == ahu_id].iloc[-1]['delta_kwh']
        
        # Compute FAIR health scores using prediction deltas
        energy_score = score_energy_anomaly(
            delta_kwh=latest_delta,
            ahu_median_delta=baseline["delta_kwh"]["median"],
            ...
        )
    
    # Step 3: LOAD - Append to CSV
    load_to_csv(df_scores, output_path)
```

---

## Complete Data Flow

```
┌──────────────┐
│ InfluxDB     │ ← Time-series database with hourly energy data
│ (Infinite)   │    Contains: power_total, energy_import, power_factor_avg, etc.
└──────┬───────┘
       │
       │ 1. Fetch E(t), E(t-24h), E(t-168h), E(t-336h)
       ▼
┌──────────────────┐
│ Prediction ETL   │  ← Runs every 30 minutes
├──────────────────┤
│ • EXTRACT:       │
│   InfluxDB query │
│   returns 4      │
│   data points    │
│ • TRANSFORM:     │
│   ŷ(t) = avg()   │
│   Δkwh = E(t)-ŷ  │
│ • LOAD:          │
│   APPEND to      │
│   predictions.csv│
└────────┬───────┘
         │
         ▼
┌──────────────────┐
│ data/            │
│ predictions.csv  │ ← Grows continuously
│ Row format:      │
│ timestamp,       │
│ ahu_id, level,   │
│ energy_current,  │
│ predicted_kwh,   │
│ delta_kwh, ...   │
└────────┬───────┘
         │
         │ 2. Fetch latest metrics + load predictions.csv
         ▼
┌──────────────────┐
│ Health Scoring   │  ← Runs every 30 minutes
├──────────────────┤
│ • EXTRACT:       │
│   InfluxDB query │
│   for all metrics│
│ • TRANSFORM:     │
│   Load           │
│   predictions.csv│
│   Compute FAIR   │
│   health scores  │
│ • LOAD:          │
│   APPEND to      │
│   health CSV     │
└────────┬───────┘
         │
         ▼
┌──────────────────┐
│ data/            │
│ health_all_levels│ ← Grows continuously
│ Row format:      │
│ timestamp,       │
│ ahu_id, level,   │
│ health_index,    │
│ energy_anomaly,  │
│ pf_degradation,  │
│ phase_imbalance, │
│ thd_drift,       │
│ overload, tier   │
└────────┬───────┘
         │
         │ 3. Frontend reads latest CSV rows
         ▼
┌──────────────────┐
│ Dashboard        │ ← Shows most recent health scores
└──────────────────┘
```

---

## scheduler.py Code Breakdown

### Main Loop (lines ~230-265)

```python
def main():
    """Main scheduler loop."""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", default=30, help="Run interval in minutes")
    args = parser.parse_args()
    
    # Start scheduler
    log_scheduler("WACH Insight ETL Scheduler Started")
    log_scheduler(f"Interval: Every {args.interval} minutes")
    
    iteration = 0
    while True:  # Continuous loop
        iteration += 1
        start_time = datetime.now()
        
        log_scheduler(f"Iteration {iteration}")
        
        # Run Prediction ETL
        run_prediction_etl(dry_run=args.dry_run)
        
        # Run Health Scoring ETL
        run_health_etl(dry_run=args.dry_run)
        
        # Calculate wait time
        elapsed = (datetime.now() - start_time).total_seconds()
        wait_time = max(0, args.interval * 60 - elapsed)
        
        log_scheduler(f"Next run in {wait_time} seconds")
        
        # Sleep until next iteration
        time.sleep(wait_time)
```

### ETL Runner (lines ~75-105)

```python
def run_etl(script_name: str, log_file: str, extra_args: list = None) -> tuple:
    """Run an ETL script and return (success, output)."""
    
    cmd = [
        sys.executable,
        os.path.join(PROJECT_ROOT, "scripts", script_name),
        "--level", "all"
    ]
    
    # Run with timeout (5 minutes max)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    output = result.stdout + result.stderr
    
    # Write to log file
    with open(log_file, "a") as f:
        timestamp = datetime.now().isoformat()
        f.write(f"\n{'='*70}\n")
        f.write(f"RUN: {timestamp}\n")
        f.write(f"COMMAND: {' '.join(cmd)}\n")
        if result.stdout:
            f.write("STDOUT:\n" + result.stdout)
        if result.stderr:
            f.write("STDERR:\n" + result.stderr)
        f.write(f"STATUS: {'SUCCESS' if result.returncode == 0 else 'FAILED'}\n")
    
    return result.returncode == 0, output
```

---

## Log File Format

### scheduler.log

```log
[2026-03-06T13:54:33.857] WACH Insight ETL Scheduler Started
[2026-03-06T13:54:33.857]   Interval: Every 30 minutes
[2026-03-06T13:54:33.857]   Prediction ETL Log: /Users/rdmasia/wach-insight/logs/prediction_etl.log
[2026-03-06T13:54:33.857]   Health Scoring Log: /Users/rdmasia/wach-insight/logs/health_etl.log

----------------------------------------------------------------------
Iteration 1 - 2026-03-06 13:54:33
----------------------------------------------------------------------

Starting Prediction ETL...
[OK] ETL Complete: 121 rows written
Prediction ETL completed successfully

Starting Health Scoring ETL...
[OK] ETL Complete: 121 rows written
Health Scoring ETL completed successfully

  Iteration completed in 86.5 seconds
  Next run in 1714 seconds (28.6 minutes)
```

### prediction_etl.log

```log
======================================================================
RUN: 2026-03-06T13:54:51
COMMAND: python scripts/run_prediction_etl.py --level all
======================================================================
STDOUT:

PREDICTION ETL PIPELINE
======================================================================

[INFO] Processing all levels (121 AHUs)

STEP 1: EXTRACT - Fetching hourly data
  11 levels processed

STEP 2: TRANSFORM - Computing Predictions
  [OK] Computed predictions for 121 AHUs

STEP 3: LOAD - Writing to data/predictions.csv
  [OK] ETL Complete: 121 rows written

[OK] Overall Data Quality:
  Sufficient (≥3 slots): 121/121 (100.0%)
  Insufficient (<3 slots): 0/121 (0.0%)

STATUS: SUCCESS
```

### health_etl.log

```log
======================================================================
RUN: 2026-03-06T13:56:00
COMMAND: python scripts/run_health_etl.py --level all
======================================================================
STDOUT:

FAIR HEALTH SCORING ETL PIPELINE
Started at: 2026-03-06T13:55:15
Level filter: All levels

STEP 1: Extract raw data
STEP 2: Transform with FAIR scoring
STEP 3: Load to CSV

ETL Complete | Status: success | Rows: 121 | Time: 45.2s

STATUS: SUCCESS
```

---

## How to Use the Scheduler

### 1. Manual Testing (One-shot Mode)

```bash
# Run both ETL pipelines once and exit
python scripts/scheduler.py --one-shot

# Output:
# - Runs Prediction ETL
# - Runs Health Scoring ETL
# - Exits after one iteration
```

### 2. Dry Run (Preview Mode)

```bash
# See what would run without executing
python scripts/scheduler.py --dry-run

# Output:
# - Shows Prediction ETL would run
# - Shows Health Scoring ETL would run
# - Exits without executing anything
```

### 3. Continuous Loop (Default)

```bash
# Run forever, every 30 minutes
python scripts/scheduler.py

# Or with custom interval:
python scripts/scheduler.py --interval 60  # Every hour
```

### 4. Background Execution

```bash
# Run in background with nohup (process survives terminal close)
nohup python scripts/scheduler.py > logs/scheduler.log 2>&1 &

# Or with screen/tmux for detachable sessions
screen -dmS wach-scheduler python scripts/scheduler.py

# View logs
tail -f logs/scheduler.log
```

---

## Making It Run Automatically (3 Options)

### Option 1: LaunchAgent (macOS Native - Recommended)

Create `~/Library/LaunchAgents/com.wach.insight.scheduler.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.wach.insight.scheduler</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/rdmasia/wach-insight/scripts/scheduler.sh</string>
  </array>

  <key>WorkingDirectory</key>
  <string>/Users/rdmasia/wach-insight</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/Users/rdmasia/wach-insight/venv/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>

  <key>StandardOutPath</key>
  <string>/tmp/wach-scheduler.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/wach-scheduler-error.log</string>

  <key>KeepAlive</key>
  <true/>

  <key>RunAtLoad</key>
  <true/>
</dict>
</plist>
```

Create `scripts/scheduler.sh`:

```bash
#!/bin/bash
cd /Users/rdmasia/wach-insight
source venv/bin/activate
exec python scripts/scheduler.py --interval 30
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.wach.insight.scheduler.plist
```

### Option 2: Cron (Linux/macOS)

```bash
# Edit crontab
crontab -e

# Add this line (runs every 30 minutes):
*/30 * * * * cd /Users/rdmasia/wach-insight && source venv/bin/activate && python scripts/scheduler.py >> logs/cron.log 2>&1
```

### Option 3: Systemd (Linux)

Create `/etc/systemd/system/wach-scheduler.service`:

```ini
[Unit]
Description=WACH Insight ETL Scheduler
After=network.target

[Service]
Type=simple
User=rdmasia
WorkingDirectory=/Users/rdmasia/wach-insight
ExecStart=/bin/bash -c "cd /Users/rdmasia/wach-insight && source venv/bin/activate && python scripts/scheduler.py"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo systemctl enable wach-scheduler
sudo systemctl start wach-scheduler
```

---

## Troubleshooting

### Scheduler Exits Immediately

**Problem:** `python scripts/scheduler.py` exits without looping.

**Solution:**
- Check if `--one-shot` or `--dry-run` flag is set
- Remove these flags for continuous loop

### ETL Pipeline Fails

**Problem:** `Prediction ETL failed` in scheduler log.

**Solution:**
1. Check detailed logs:
   ```bash
   tail -50 logs/prediction_etl.log
   tail -50 logs/health_etl.log
   ```
2. Check InfluxDB connection:
   ```bash
   cat backend/.env | grep INFLUXDB
   ```

### High Latency Warnings

**Problem:** Log shows "Pipeline took Xs (TARGET: <45s)"

**Solution:**
- Check InfluxDB query performance
- Consider limiting to single level for testing:
  ```bash
  python scripts/scheduler.py --one-shot
  ```

---

## Monitoring

### Check Last Run

```bash
# View recent scheduler activity
tail -30 logs/scheduler.log

# Count successful runs today
grep "completed successfully" logs/prediction_etl.log | wc -l

# Check output files were updated
ls -lh data/predictions.csv data/health_all_levels.csv
```

### Verify Data Freshness

```bash
# Check if CSVs have recent data (within last hour)
python -c "
import pandas as pd
from datetime import datetime, timedelta

for csv in ['data/predictions.csv', 'data/health_all_levels.csv']:
    df = pd.read_csv(csv)
    latest = max(pd.to_datetime(df['timestamp']))
    age = (datetime.now() - latest).total_seconds() / 60
    print(f'{csv}: {age:.1f} minutes old')
"
```

---

## Summary

| Component | Purpose |
|-----------|---------|
| `scheduler.py` | Continuous loop running ETL every 30 minutes |
| `run_prediction_etl.py` | Fetches energy data, computes predictions, writes to CSV |
| `run_health_etl.py` | Fetches metrics, reads predictions, computes health scores |
| `data/predictions.csv` | Energy predictions (grows ~121 rows/30 min) |
| `data/health_all_levels.csv` | Health scores (grows ~121 rows/30 min) |
| `logs/` | Scheduler and ETL logs for monitoring |

**Key Point:** The scheduler runs **continuously**, waking up every 30 minutes to run both ETL pipelines. Each pipeline appends new rows to its respective CSV, creating a continuously growing dataset that the dashboard reads for real-time monitoring.
