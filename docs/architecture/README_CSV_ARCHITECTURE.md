# Documentation Index: Health Index CSV Architecture

## Overview

This directory contains documentation for the dual CSV architecture implementation that enables hourly granularity for 24h health index charts.

## Documentation Files

### 1. [data_flows.md](./data_flows.md)

**Purpose**: Explains the complete data flow through the dual CSV system.

**Key Sections:**
- Architecture decision (why two CSVs)
- Data flow diagrams (ETL → API → Frontend)
- Time range selection logic
- Regenerating historical data
- Migration notes from single CSV to dual CSV

**When to Read:**
- Understanding how data flows through the system
- Debugging missing chart data
- Planning CSV storage/retention strategy

---

### 2. [csv_file_formats.md](./csv_file_formats.md)

**Purpose**: Complete schema documentation for both CSV files.

**Key Sections:**
- **health_hourly.csv** (41 columns, hourly granularity)
- **health_all_levels.csv** (23 columns, daily aggregation)
- Health index calculation formula
- Tier definitions and color mappings
- Safety flag specifications
- Retention policies (30 days vs indefinite)

**When to Read:**
- Adding new columns to CSV output
- Understanding column data types and defaults
- API response format documentation

**Quick Reference:**

| File | Rows/Day | Retention | Columns |
|------|----------|-----------|---------|
| health_hourly.csv | 1,200 (50 AHUs × 24h) | 30 days | 41 |
| health_all_levels.csv | 70 (50 AHUs × 1d) | Indefinite | 23 |

---

### 3. [health_index_chart.md](./health_index_chart.md)

**Purpose**: Frontend-facing documentation for chart integration and troubleshooting.

**Key Sections:**
- Problem statement (before/after comparison)
- Architecture decision explanation
- Code change details (3 modified files)
- Data flow diagrams
- API response examples
- Maintenance guide and troubleshooting

**When to Read:**
- Debugging chart display issues
- Understanding frontend-backend data flow
- Maintaining ETL pipeline

---

## Quick Start Guide

### For Developers New to This System

1. **Read this index** → [data_flows.md](./data_flows.md) (skim)
2. **Learn the schema** → [csv_file_formats.md](./csv_file_formats.md) (reference)
3. **Understand charts** → [health_index_chart.md](./health_index_chart.md) (how-to)

### For Maintainers

1. **ETL Pipeline**: [run_health_etl.py](../../scripts/etl/run_health_etl.py) + [history_generator.py](../../scripts/etl/history_generator.py)
2. **CSV Reader**: [csv_reader.py](../../backend/core/csv_reader.py)
3. **Frontend**: [AhuHealthTrendDashboard.jsx](../../frontend/src/components/AhuHealthTrendDashboard.jsx)

---

## Architecture Quick Reference

```
┌──────────────────────────────────────────────────────────────┐
│                    Dual CSV Architecture                       │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────┐        ┌─────────────┐                      │
│  │health_hourly│        │health_all_  │                      │
│  │   _hourly.csv│       │    levels.csv│                     │
│  └─────────────┘        └─────────────┘                      │
│       │                        │                              │
│  Hourly (24h)            Daily (7d/30d)                      │
│  50 AHUs × 24h          50 AHUs × N days                    │
│       │                        │                              │
│  ┌────▼────┐            ┌─────▼──────┐                       │
│  │24h chart │            │7d/30d charts│                      │
│  └──────────┘            └─────────────┘                      │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

### File Selection Logic

```python
# backend/core/csv_reader.py

def _load_csv(time_range: str = "7d") -> pd.DataFrame:
    """Load CSV; return empty DataFrame if missing."""
    path = HOURLY_CSV_PATH if time_range == "24h" else CSV_PATH
    # ...
```

| Frontend Input | Backend Parameter | CSV Used |
|----------------|-------------------|----------|
| "24h" | `time_range="24h"` | health_hourly.csv |
| "7d" | `time_range="7d"` | health_all_levels.csv |
| "30d" | `time_range="30d"` | health_all_levels.csv |

---

## Common Tasks

### Regenerate All Historical Data

```bash
# Full historical run (one-shot)
python scripts/etl/history_generator.py --level all

# Verify both CSVs were created
ls -la data/health_hourly.csv data/health_all_levels.csv

# Check row counts
wc -l data/health_hourly.csv data/health_all_levels.csv
```

### Verify CSV Data Quality

```bash
# Check hourly CSV has recent data
python -c "
import pandas as pd
from datetime import datetime, timedelta

df = pd.read_csv('data/health_hourly.csv', parse_dates=['timestamp'])
cutoff = datetime.now() - timedelta(hours=24)
recent = df[df['timestamp'] >= cutoff]

print(f'Hourly CSV: {len(df)} total rows')
print(f'Recent (24h): {len(recent)} rows')
print(f'Unique AHUs: {df[\"ahu_id\"].nunique()}')
"

# Check daily CSV
python -c "
import pandas as pd
df = pd.read_csv('data/health_all_levels.csv', parse_dates=['timestamp'])
print(f'Daily CSV: {len(df)} rows')
"
```

### Debug Chart Not Showing Data

```bash
# 1. Check CSV files exist and have data
ls -la data/health_*.csv

# 2. Verify ETL ran recently
tail -5 logs/health_etl.log | grep "update"

# 3. Test backend endpoint
curl -s "http://localhost:8081/api/dashboard/trend?level=1&time_range=24h" | jq '.series[0].data | length'

# 4. Check scheduler is running
ps aux | grep scheduler.py
```

---

## Related Documentation

### ETL Pipeline
- [ETL Reports](../etl_reports/) - 8 detailed ETL pipeline documentation files
- [Scheduler Setup](../automation/) - Continuous execution setup

### Scoring Algorithm
- [FAIR Health Scoring](../scoring/) - 9 files on health index calculation
- [Risk Engine](../../backend/core/risk_engine.py) - Scoring implementation

### Architecture
- [Architecture Overview](../architecture/HEALTH_RANKINGS_ARCHITECTURE.md) - Health rankings system
- [Learning History](./learning_history.md) - Project timeline

---

## Maintenance Checklist

### Daily (Automated)

- [ ] Scheduler runs every 30 minutes
- [ ] Both CSVs are appended with latest hour
- [ ] No errors in `logs/health_etl.log`
- [ ] CSV file sizes are growing

### Weekly (Manual)

- [ ] Verify data quality (non-empty, valid timestamps)
- [ ] Check for duplicate rows
- [ ] Review storage usage
- [ ] Test chart display in frontend

### Monthly (Maintenance)

- [ ] Clean up hourly CSV (>30 days old)
- [ ] Archive daily CSV to backup
- [ ] Review InfluxDB retention policies
- [ ] Update documentation if needed

---

## Migration Path

### From Single CSV to Dual CSV

**Old System (v1.0):**
```
health_all_levels.csv → 24h chart shows only 1 point
```

**New System (v2.0):**
```
health_hourly.csv → 24h chart shows 24 points
health_all_levels.csv → 7d/30d charts show daily aggregates
```

**Migration Steps:**
1. Run `python scripts/etl/run_health_etl.py --output-hourly`
2. Verify `data/health_hourly.csv` is created
3. Test 24h chart shows smooth data
4. Update documentation

---

## Troubleshooting

### Issue: 24h Chart Shows Only 1 Point

**Root Cause**: Frontend is querying daily CSV instead of hourly.

**Checklist:**
1. Verify `time_range` parameter = "24h" in frontend
2. Check backend logs for CSV path selection
3. Confirm `health_hourly.csv` exists and has data

### Issue: Data Not Updating Every 30 Minutes

**Root Cause**: Scheduler not running or ETL failing.

**Checklist:**
1. Check scheduler process: `ps aux | grep scheduler.py`
2. Review logs: `tail -50 logs/scheduler.log`
3. Test manual ETL: `python scripts/etl/run_health_etl.py --output-hourly`

### Issue: Duplicate Rows in CSV

**Root Cause**: ETL ran twice with same data.

**Fix:**
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/health_hourly.csv')
df = df.drop_duplicates(subset=['timestamp', 'ahu_id'], keep='last')
df.to_csv('data/health_hourly.csv', index=False)
"
```

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| March 5, 2026 | v1.0 | Single daily CSV only |
| March 12, 2026 | v2.0 | Dual CSV architecture added |

---

## Quick Links

| Document | Link |
|----------|------|
| Full Data Flows | [data_flows.md](./data_flows.md) |
| CSV Schema | [csv_file_formats.md](./csv_file_formats.md) |
| Chart Integration | [health_index_chart.md](./health_index_chart.md) |
| ETL Pipeline | [run_health_etl.py](../../scripts/etl/run_health_etl.py) |
| CSV Reader | [csv_reader.py](../../backend/core/csv_reader.py) |

---

**Last Updated**: March 12, 2026  
**Author**: WACH Insight Team
