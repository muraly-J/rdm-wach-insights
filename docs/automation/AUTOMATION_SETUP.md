# Automation Setup Guide

**Date:** March 6, 2026  
**Version:** 1.0

---

## Overview

Both ETL pipelines are now automated to run every 30 minutes:

1. **Prediction ETL** (`scripts/run_prediction_etl.py`)
   - Generates energy predictions
   - Computes delta_kwh (actual vs predicted)
   - Outputs: `data/predictions.csv`

2. **Health Scoring ETL** (`scripts/run_health_etl.py`)
   - Computes FAIR health scores
   - Uses prediction deltas for energy anomaly scoring
   - Outputs: `data/health_all_levels.csv`

---

## Quick Start

### Option 1: Manual Testing (One-shot)

Run both ETL pipelines once:

```bash
# Run prediction ETL
python scripts/run_prediction_etl.py --level all

# Run health scoring ETL
python scripts/run_health_etl.py --level all
```

### Option 2: Scheduled Mode

Run the scheduler (continuous loop):

```bash
# Start scheduler (runs every 30 minutes by default)
python scripts/scheduler.py

# Custom interval (every hour)
python scripts/scheduler.py --interval 60

# One-shot mode (run once and exit)
python scripts/scheduler.py --one-shot

# Dry run (show what would execute)
python scripts/scheduler.py --dry-run
```

---

## Directory Structure

```
wach-insight/
├── scripts/
│   ├── scheduler.py           # Main scheduler script
│   ├── run_prediction_etl.py  # Prediction ETL (updated with --scheduled flag)
│   └── run_health_etl.py      # Health scoring ETL (updated with --scheduled flag)
├── logs/
│   ├── scheduler.log          # Scheduler activity log
│   ├── prediction_etl.log     # Prediction ETL output
│   └── health_etl.log         # Health scoring ETL output
├── data/
│   ├── predictions.csv        # Energy predictions (generated)
│   └── health_all_levels.csv  # Health scores (generated)
└── docs/
    └── AUTOMATION_SETUP.md    # This file
```

---

## How It Works

### Scheduler Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Scheduler (runs every 30 minutes)                          │
├─────────────────────────────────────────────────────────────┤
│ 1. Log start time and iteration                            │
├─────────────────────────────────────────────────────────────┤
│ 2. Run Prediction ETL                                       │
│    ├─ Fetch hourly data from InfluxDB                      │
│    ├─ Compute 3-slot prediction average                    │
│    └─ Generate predictions.csv                             │
├─────────────────────────────────────────────────────────────┤
│ 3. Run Health Scoring ETL                                   │
│    ├─ Fetch latest metrics from InfluxDB                   │
│    ├─ Compute FAIR health scores                           │
│    └─ Generate health_all_levels.csv                       │
├─────────────────────────────────────────────────────────────┤
│ 4. Log completion and calculate wait time                  │
├─────────────────────────────────────────────────────────────┤
│ 5. Sleep until next run                                    │
└─────────────────────────────────────────────────────────────┘
```

### Log File Format

**scheduler.log:**
```
[2026-03-06T10:00:00] Scheduler started
[2026-03-06T10:00:00]   Interval: Every 30 minutes
[2026-03-06T10:00:00]   Prediction ETL Log: /path/to/logs/prediction_etl.log
[2026-03-06T10:00:00]   Health Scoring Log: /path/to/logs/health_etl.log
...
[2026-03-06T10:00:45] Iteration 1 completed
[2026-03-06T10:00:45]   Next run in 1755 seconds (29.2 minutes)
```

**prediction_etl.log:**
```
======================================================================
RUN: 2026-03-06T10:00:15
COMMAND: python scripts/run_prediction_etl.py --level all
======================================================================
STDOUT:
...
[OK] ETL Complete: 121 rows written to data/predictions.csv

======================================================================
RUN: 2026-03-06T10:30:15
COMMAND: python scripts/run_prediction_etl.py --level all
======================================================================
...
```

**health_etl.log:**
```
======================================================================
RUN: 2026-03-06T10:01:00
COMMAND: python scripts/run_health_etl.py --level all
======================================================================
STDOUT:
...
ETL Complete | Status: success | Rows: 121 | Time: 35.2s

======================================================================
RUN: 2026-03-06T10:31:00
COMMAND: python scripts/run_health_etl.py --level all
======================================================================
...
```

---

## Monitoring

### View Scheduler Logs

```bash
# Real-time scheduler log
tail -f logs/scheduler.log

# Today's scheduler log
grep "2026-03-06" logs/scheduler.log
```

### View ETL Logs

```bash
# Prediction ETL log
tail -f logs/prediction_etl.log

# Health scoring log
tail -f logs/health_etl.log

# Check for errors in scheduler log
grep -i "error\|failed" logs/scheduler.log
```

### Health Check

Verify both pipelines ran successfully:

```bash
# Check last run timestamps
ls -l logs/*.log

# Count successful runs today
grep -c "ETL Complete" logs/prediction_etl.log
grep -c "ETL Complete" logs/health_etl.log

# Verify output files were updated
ls -lh data/predictions.csv data/health_all_levels.csv
```

---

## Troubleshooting

### Scheduler Not Running

**Issue:** `python scripts/scheduler.py` exits immediately

**Solution:**
- Check if it's in one-shot mode (remove `--one-shot`)
- Verify no syntax errors: `python -m py_compile scripts/scheduler.py`

### ETL Pipeline Failures

**Issue:** ETL pipelines fail with InfluxDB connection errors

**Solution:**
1. Check environment variables:
   ```bash
   cat backend/.env | grep INFLUXDB
   ```

2. Test InfluxDB connection:
   ```bash
   python scripts/fetch_all_ahus_latest.py --help
   ```

3. Check logs:
   ```bash
   tail -50 logs/prediction_etl.log
   tail -50 logs/health_etl.log
   ```

### Missing Output Files

**Issue:** CSV files not updated

**Solution:**
1. Check if ETL ran:
   ```bash
   grep "ETL Complete" logs/prediction_etl.log | tail -5
   ```

2. Verify data directory permissions:
   ```bash
   ls -ld data/
   chmod 755 data/
   ```

### High Latency Warnings

**Issue:** Scheduler shows "Pipeline took Xs (TARGET: <45s)"

**Solution:**
1. Check InfluxDB query performance
2. Reduce time range if needed:
   ```bash
   python scripts/run_health_etl.py --level 1  # Test single level
   ```
3. Review logs for slow queries

---

## Advanced Configuration

### Change Run Interval

Edit `scripts/scheduler.py`:

```python
# Line ~28
DEFAULT_INTERVAL_MINUTES = 60  # Change from 30 to 60 minutes
```

Or use command-line:

```bash
python scripts/scheduler.py --interval 120  # Every 2 hours
```

### Skip one iteration

```bash
# Add --one-shot to run only once
python scripts/scheduler.py --one-shot
```

### Dry Run

```bash
# See what would run without executing
python scripts/scheduler.py --dry-run
```

---

## Installation (Automatic)

The easiest way to run the scheduler automatically is using the install script:

### Step 1: Install LaunchAgent

```bash
# Run the installation script
cd /Users/rdmasia/wach-insight
bash scripts/install_scheduler.sh
```

This will:
- Create the LaunchAgent plist at `~/Library/LaunchAgents/com.wach.insight.scheduler.plist`
- Load the agent with launchctl
- Start running automatically

### Step 2: Verify Installation

```bash
# Check if scheduler is running
launchctl list | grep wach.insight

# View logs
tail -f logs/scheduler.log
```

### Step 3: Uninstall (if needed)

```bash
# Remove the LaunchAgent
bash scripts/install_scheduler.sh --uninstall
```

---

## Manual Installation (Advanced)

If you prefer to set up manually:

### 1. Create scheduler.sh

**File:** `scripts/scheduler.sh`

```bash
#!/bin/bash
cd /Users/rdmasia/wach-insight
source venv/bin/activate
exec python scripts/scheduler.py --interval 30
```

### 2. Create LaunchAgent

**File:** `~/Library/LaunchAgents/com.wach.insight.scheduler.plist`

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

  <!-- Run every 30 minutes -->
  <key>StartInterval</key>
  <integer>1800</integer>

  <!-- Restart delay if crashed -->
  <key>ThrottleInterval</key>
  <integer>10</integer>
</dict>
</plist>
```

### 3. Load the Agent

```bash
# Make scheduler.sh executable
chmod +x scripts/scheduler.sh

# Load the LaunchAgent
launchctl load ~/Library/LaunchAgents/com.wach.insight.scheduler.plist

# Start it manually
launchctl start com.wach.insight.scheduler
```

---

## Maintenance

### Clear Logs

```bash
# Keep last 7 days of logs
find logs -name "*.log" -mtime +7 -delete

# Or clear all logs
rm logs/*.log
```

### Manual Re-run

```bash
# Force re-run of both pipelines
python scripts/run_prediction_etl.py --level all
python scripts/run_health_etl.py --level all
```

### Verify Data Integrity

```bash
# Check predictions.csv has recent data
head -5 data/predictions.csv
wc -l data/predictions.csv

# Check health_all_levels.csv has recent data
head -5 data/health_all_levels.csv
wc -l data/health_all_levels.csv

# Verify row counts match AHU count (121 devices)
awk -F',' 'NR>1 {count++} END {print "AHUs in predictions:", count}' data/predictions.csv
awk -F',' 'NR>1 {count++} END {print "AHUs in health:", count}' data/health_all_levels.csv
```

---

## FAQ

**Q: How often do the ETL pipelines run?**

A: Every 30 minutes by default. Configure with `--interval` flag.

**Q: What happens if a pipeline fails?**

A: The scheduler logs the error and continues to the next run. Check logs for details.

**Q: Can I customize the run times?**

A: Yes, edit `DEFAULT_INTERVAL_MINUTES` in `scripts/scheduler.py`.

**Q: Do I need to keep the terminal open?**

A: No, use Launchd for background execution, or run with `nohup`.

**Q: How do I stop the scheduler?**

A: 
- Manual run: Ctrl+C
- Launchd: `launchctl stop com.wach.insight.scheduler`

---

## Related Documentation

- [FAIR Health Scoring](./FAIR_HEALTH_SCORING_DOCUMENTATION.md)
- [Prediction ETL Implementation](./ETL_PIPELINE_IMPLEMENTATION_REPORT.md)
- [Delta Feedback Verification](./PREDICTION_DELTA_FEEDBACK_VERIFICATION_REPORT.md)

---

**Author:** WACH Insight Team  
**Last Updated:** March 6, 2026
