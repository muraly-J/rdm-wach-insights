 Real InfluxDB Data Integration Implementation Plan

 For agentic workers: REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan.
 Steps use checkbox (- [ ]) syntax for tracking.

 Goal: Replace all mock/synthetic data in the frontend dashboard with real AHU health data sourced from InfluxDB → CSV pipeline, covering all 11 levels (122
  AHUs) with continuous 30-minute updates.

 Architecture: Run a one-time historical ETL to populate health_all_levels.csv with full time-series data for all levels, fix the scheduler so it keeps that
  CSV updated every 30 minutes, then serve the CSV through new backend endpoints that the frontend calls instead of mock generators.

 Tech Stack: Python/FastAPI backend, pandas CSV reader, React/Zustand/Recharts frontend, InfluxDB source, health_all_levels.csv as the shared data layer.

 ---
 Chunk 1: ETL Pipeline Fixes

 Task 1: Fix history_generator.py — full time-series generation

 Files:
 - Modify: scripts/etl/history_generator.py (lines ~400–530, the run_health_etl_historical function)

 Background:
 run_health_etl_historical already fetches full time-series raw metrics (df_power, df_pf, etc. with 'all_time'), and predictions_df has all timestamps per
 device. But on line 411 it uses device_data.sort_values('timestamp').iloc[-1] — the [-1] means only the LATEST timestamp is processed. We need to loop over
  every row instead.

 The raw DataFrames are indexed by timestamp, so use .asof(ts) to get the nearest value at each historical timestamp.

 The output must match the run_health_etl.py column format exactly (the columns currently in health_all_levels.csv): timestamp, ahu_id, level, health_index,
  tier, energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload, raw_power_total, raw_energy_import, raw_power_factor_avg,
 raw_current_unbalance, raw_composite_thd plus the baseline_*, z_*, level_*, trend_*, overload_*, flag_* columns.

 Add deduplication: before appending, check if (timestamp, ahu_id) pair already exists in the CSV to allow safe re-runs.

 - Step 1: Locate the exact loop to modify

 Read scripts/etl/history_generator.py lines 395–530 to confirm the loop structure and identify all variables that currently use iloc[-1] or latest_row.

 - Step 2: Write the test for full time-series output

 Create scripts/etl/test_history_fullseries.py:

 #!/usr/bin/env python3
 """Test that run_health_etl_historical produces >1 row per device."""
 import pandas as pd
 import subprocess, sys, os

 CSV_PATH = os.path.join(os.path.dirname(__file__), "../../data/health_all_levels.csv")

 def test_multiple_rows_per_device():
     """After a partial run, each device should have >1 row."""
     df = pd.read_csv(CSV_PATH)
     # Pick a device known to have historical data
     if df.empty:
         print("SKIP: CSV empty, run historical ETL first")
         return
     device_counts = df.groupby('ahu_id').size()
     multi_row_devices = (device_counts > 1).sum()
     total_devices = len(device_counts)
     print(f"Devices with >1 row: {multi_row_devices}/{total_devices}")
     assert multi_row_devices > 0, "Expected multiple rows per device, got 1 each (iloc[-1] bug still present)"
     print("PASS: Multiple rows per device confirmed")

 if __name__ == "__main__":
     test_multiple_rows_per_device()

 Run: python scripts/etl/test_history_fullseries.py
 Expected: SKIP (CSV only has 21 rows now, all level 1, one timestamp)

 - Step 3: Modify run_health_etl_historical to iterate all timestamps

 In scripts/etl/history_generator.py, find the device loop (around line 400). Change:

 # BEFORE — processes only latest row
 device_data = predictions_df[predictions_df['ahu_id'] == ahu_id]
 if device_data.empty:
     continue
 latest_row = device_data.sort_values('timestamp').iloc[-1]
 latest_ts = latest_row['timestamp']
 level_val = str(latest_row.get('level', 'Level 1'))
 energy_anomaly_val = latest_row.get('delta_kwh')
 # ... compute single health score ...
 # ... append single row to results ...

 To:

 # AFTER — processes every timestamp row
 device_data = predictions_df[predictions_df['ahu_id'] == ahu_id].sort_values('timestamp')
 if device_data.empty:
     continue

 for _, row in device_data.iterrows():
     ts = row['timestamp']
     level_val = str(row.get('level', 'Level 1'))
     energy_anomaly_val = row.get('delta_kwh')

     # Look up raw metrics at this timestamp using asof
     current_power = None
     current_pf = None
     current_unbalance = None
     current_composite_thd = None
     current_energy = None

     try:
         if not df_power.empty and ahu_id in df_power.columns:
             s = df_power[ahu_id].dropna()
             if not s.empty:
                 current_power = float(s.asof(ts)) if hasattr(s.index, 'asof') else float(s.iloc[-1])
         if not df_pf.empty and ahu_id in df_pf.columns:
             s = df_pf[ahu_id].dropna()
             if not s.empty:
                 current_pf = float(s.asof(ts)) if hasattr(s.index, 'asof') else float(s.iloc[-1])
         if not df_unbalance.empty and ahu_id in df_unbalance.columns:
             s = df_unbalance[ahu_id].dropna()
             if not s.empty:
                 current_unbalance = float(s.asof(ts)) if hasattr(s.index, 'asof') else float(s.iloc[-1])
         if not df_l1_thd.empty and ahu_id in df_l1_thd.columns:
             s = df_l1_thd[ahu_id].dropna()
             if not s.empty:
                 l1 = float(s.asof(ts)) if hasattr(s.index, 'asof') else float(s.iloc[-1])
                 current_composite_thd = l1
         if not df_l3_thd.empty and ahu_id in df_l3_thd.columns:
             s = df_l3_thd[ahu_id].dropna()
             if not s.empty:
                 l3 = float(s.asof(ts)) if hasattr(s.index, 'asof') else float(s.iloc[-1])
                 current_composite_thd = ((current_composite_thd or 0) + l3) / 2
         if not df_energy.empty and ahu_id in df_energy.columns:
             s = df_energy[ahu_id].dropna()
             if not s.empty:
                 current_energy = float(s.asof(ts)) if hasattr(s.index, 'asof') else float(s.iloc[-1])
     except Exception:
         pass

     # ... rest of health score computation uses ts, level_val, energy_anomaly_val,
     #     current_power, current_pf, current_unbalance, current_composite_thd ...
     # ... append row to results list ...

 Important: The df_power index must be a DatetimeIndex for .asof() to work. Verify and sort the index after fetching:
 df_power = fetch_time_series(...).sort_index()

 Add deduplication before appending results to CSV:
 # In the CSV write section — after building the results DataFrame:
 if os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 0:
     existing = pd.read_csv(CSV_PATH)
     existing_keys = set(zip(existing['timestamp'], existing['ahu_id']))
     new_rows = results_df[
         ~results_df.apply(lambda r: (r['timestamp'], r['ahu_id']) in existing_keys, axis=1)
     ]
     new_rows.to_csv(CSV_PATH, mode='a', header=False, index=False)
 else:
     results_df.to_csv(CSV_PATH, index=False)

 - Step 4: Run test to verify it fails on unmodified code

 Run: python scripts/etl/test_history_fullseries.py
 Expected: SKIP (CSV still has one timestamp per device)

 - Step 5: Run historical ETL for level 1 first (smoke test)

 cd /Users/rdmasia/wach-insight
 python scripts/etl/run_health_etl.py --mode historical --level 1

 Expected: New rows appended to data/health_all_levels.csv with multiple timestamps per device.
 Verify: python -c "import pandas as pd; df = pd.read_csv('data/health_all_levels.csv'); print(df.groupby('ahu_id').size()[:5])"

 - Step 6: Run test to verify it now passes

 Run: python scripts/etl/test_history_fullseries.py
 Expected: PASS

 - Step 7: Run historical ETL for all levels

 python scripts/etl/run_health_etl.py --mode historical --level all

 This is a long-running batch job. Monitor output for errors. When done:
 python -c "
 import pandas as pd
 df = pd.read_csv('data/health_all_levels.csv')
 print('Total rows:', len(df))
 print('Levels covered:', sorted(df['level'].unique()))
 print('Devices per level:', df.groupby('level')['ahu_id'].nunique().to_dict())
 print('Date range:', df['timestamp'].min(), '→', df['timestamp'].max())
 "

 Expected: Rows for all 11 levels, 122 devices total, full time range of available InfluxDB data.

 - Step 8: Commit ETL fix

 git add scripts/etl/history_generator.py scripts/etl/test_history_fullseries.py
 git commit -m "fix: iterate all timestamps in run_health_etl_historical (not just iloc[-1])"

 ---
 Task 2: Fix scheduler script path bug

 Files:
 - Modify: scripts/scheduler/scheduler.py (line 75)

 Background:
 Line 75 builds the script path as os.path.join(PROJECT_ROOT, "scripts", script_name) but the ETL scripts live at scripts/etl/. The scheduler is called with
  run_health_etl.py and run_prediction_etl.py — both in scripts/etl/, not in scripts/.

 - Step 1: Write failing test

 Create scripts/scheduler/test_scheduler_paths.py:

 """Test that scheduler resolves ETL script paths correctly."""
 import os, sys
 sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

 # Import just the path resolution logic
 PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

 def script_path_old(script_name):
     return os.path.join(PROJECT_ROOT, "scripts", script_name)

 def script_path_new(script_name):
     return os.path.join(PROJECT_ROOT, "scripts", "etl", script_name)

 def test_script_paths_exist():
     scripts = ["run_health_etl.py", "run_prediction_etl.py"]
     for s in scripts:
         old_path = script_path_old(s)
         new_path = script_path_new(s)
         assert not os.path.exists(old_path), f"Old path should NOT exist: {old_path}"
         assert os.path.exists(new_path), f"New path MUST exist: {new_path}"
     print("PASS: All ETL scripts found at scripts/etl/")

 if __name__ == "__main__":
     test_script_paths_exist()

 Run: python scripts/scheduler/test_scheduler_paths.py
 Expected: PASS (confirms old path doesn't exist, new path does)

 - Step 2: Apply the fix

 In scripts/scheduler/scheduler.py, line 75, change:

 # BEFORE
 script_path = os.path.join(PROJECT_ROOT, "scripts", script_name)

 # AFTER
 script_path = os.path.join(PROJECT_ROOT, "scripts", "etl", script_name)

 - Step 3: Verify scheduler can find and invoke script

 python -c "
 import os, sys
 PROJECT_ROOT = os.path.dirname(os.path.abspath('scripts/scheduler/scheduler.py'))
 for name in ['run_health_etl.py', 'run_prediction_etl.py']:
     path = os.path.join(PROJECT_ROOT, 'scripts', 'etl', name)
     print(name, '->', 'EXISTS' if os.path.exists(path) else 'MISSING')
 "

 Expected: Both show EXISTS.

 - Step 4: Commit

 git add scripts/scheduler/scheduler.py scripts/scheduler/test_scheduler_paths.py
 git commit -m "fix: correct ETL script path in scheduler (scripts/ -> scripts/etl/)"

 ---
 Chunk 2: Backend CSV Layer

 Task 3: Create backend/core/csv_reader.py

 Files:
 - Create: backend/core/csv_reader.py

 Background:
 The CSV data/health_all_levels.csv has these columns relevant to the frontend:
 - timestamp, ahu_id, level, health_index, tier
 - Score columns (0–100): energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload
 - Raw metric columns: raw_power_total, raw_energy_import, raw_power_factor_avg, raw_current_unbalance, raw_composite_thd

 Score → raw metric mapping:
 - energy_anomaly ↔ raw_energy_import (kWh)
 - pf_degradation ↔ raw_power_factor_avg (unitless)
 - phase_imbalance ↔ raw_current_unbalance (%)
 - thd_drift ↔ raw_composite_thd (%)
 - overload ↔ raw_power_total (kW)

 AHU name format: AHU-L{level}-{device_num} where device_num = device_id[-2:] (e.g., "e0101" → "01").

 - Step 1: Write failing tests for csv_reader

 Create backend/tests/test_csv_reader.py:

 """Tests for backend/core/csv_reader.py"""
 import pytest
 import pandas as pd
 import os, sys
 sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

 from core.csv_reader import (
     get_health_index_series,
     get_score_breakdown,
     get_raw_score_relationship,
 )

 CSV_PATH = os.path.join(os.path.dirname(__file__), '../../data/health_all_levels.csv')

 @pytest.fixture
 def csv_has_data():
     """Skip tests if CSV is empty."""
     if not os.path.exists(CSV_PATH):
         pytest.skip("CSV not found")
     df = pd.read_csv(CSV_PATH)
     if df.empty:
         pytest.skip("CSV is empty")
     return df

 def test_health_index_series_returns_list(csv_has_data):
     result = get_health_index_series(level=1, device_id=None, time_range="7d")
     assert isinstance(result, list)
     if result:
         item = result[0]
         assert 'device' in item
         assert 'data' in item
         assert 'id' in item['device']
         assert 'name' in item['device']
         if item['data']:
             assert 'timestamp' in item['data'][0]
             assert 'value' in item['data'][0]

 def test_score_breakdown_returns_fair_scores(csv_has_data):
     result = get_score_breakdown(level=1, time_range="7d")
     assert isinstance(result, list)
     if result:
         device = result[0]
         assert 'id' in device
         assert 'scores' in device
         fair_keys = {'energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload'}
         assert fair_keys.issubset(device['scores'].keys())
         score = device['scores']['energy_anomaly']
         assert 'current' in score
         assert 'trend' in score
         assert 'data' in score

 def test_raw_score_relationship_has_raw_and_score(csv_has_data):
     df = csv_has_data
     device_id = df['ahu_id'].iloc[0]
     result = get_raw_score_relationship(device_id=device_id, time_range="7d")
     assert isinstance(result, dict)
     if result:
         score_key = list(result.keys())[0]
         entry = result[score_key]
         assert 'rawMetric' in entry
         assert 'rawUnit' in entry
         assert 'rawData' in entry
         assert 'scoreData' in entry

 Run: cd backend && python -m pytest tests/test_csv_reader.py -v
 Expected: ImportError (module doesn't exist yet)

 - Step 2: Implement backend/core/csv_reader.py

 """
 csv_reader.py
 ─────────────
 Reads health_all_levels.csv and formats data for API endpoints.

 CSV columns used:
   timestamp, ahu_id, level, health_index, tier,
   energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload,
   raw_power_total, raw_energy_import, raw_power_factor_avg,
   raw_current_unbalance, raw_composite_thd
 """

 import os
 import pandas as pd
 from datetime import datetime, timedelta, timezone
 from functools import lru_cache

 CSV_PATH = os.path.join(
     os.path.dirname(__file__), '..', '..', 'data', 'health_all_levels.csv'
 )

 SCORE_COLUMNS = ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload']

 # Score → (raw column, unit)
 SCORE_RAW_MAP = {
     'energy_anomaly':  ('raw_energy_import',     'kWh'),
     'pf_degradation':  ('raw_power_factor_avg',   ''),
     'phase_imbalance': ('raw_current_unbalance',  '%'),
     'thd_drift':       ('raw_composite_thd',      '%'),
     'overload':        ('raw_power_total',         'kW'),
 }

 RANGE_DELTA = {
     '24h': timedelta(hours=24),
     '7d':  timedelta(days=7),
     '30d': timedelta(days=30),
 }


 def _load_csv() -> pd.DataFrame:
     """Load CSV; return empty DataFrame if missing."""
     if not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0:
         return pd.DataFrame()
     return pd.read_csv(CSV_PATH, parse_dates=['timestamp'])


 def _filter_time_range(df: pd.DataFrame, time_range: str) -> pd.DataFrame:
     delta = RANGE_DELTA.get(time_range, RANGE_DELTA['7d'])
     cutoff = datetime.now(timezone.utc) - delta
     ts = pd.to_datetime(df['timestamp'], utc=True)
     return df[ts >= cutoff]


 def _ahu_name(device_id: str, level: int) -> str:
     return f"AHU-L{level}-{device_id[-2:]}"


 def get_health_index_series(level: int, device_id: str | None, time_range: str) -> list[dict]:
     """
     Returns [{device: {id, name, level}, data: [{timestamp, value}]}]
     for all devices on the level (or just device_id if specified).
     """
     df = _load_csv()
     if df.empty:
         return []
     df = df[df['level'] == f"Level {level}"]
     if device_id:
         df = df[df['ahu_id'] == device_id]
     df = _filter_time_range(df, time_range).sort_values('timestamp')

     result = []
     for ahu_id, group in df.groupby('ahu_id'):
         result.append({
             'device': {
                 'id': ahu_id,
                 'name': _ahu_name(ahu_id, level),
                 'level': level,
             },
             'data': [
                 {'timestamp': row['timestamp'].isoformat(), 'value': round(float(row['health_index']), 2)}
                 for _, row in group.iterrows()
                 if pd.notna(row['health_index'])
             ],
         })
     return result


 def get_score_breakdown(level: int, time_range: str) -> list[dict]:
     """
     Returns [{id, name, scores: {energy_anomaly: {current, trend, data}, ...}}]
     """
     df = _load_csv()
     if df.empty:
         return []
     df = df[df['level'] == f"Level {level}"]
     df = _filter_time_range(df, time_range).sort_values('timestamp')

     result = []
     for ahu_id, group in df.groupby('ahu_id'):
         scores = {}
         for col in SCORE_COLUMNS:
             if col not in group.columns:
                 continue
             series = group[['timestamp', col]].dropna(subset=[col])
             if series.empty:
                 continue
             values = series[col].astype(float)
             data_points = [
                 {'timestamp': row['timestamp'].isoformat(), 'value': round(float(row[col]), 2)}
                 for _, row in series.iterrows()
             ]
             current = round(float(values.iloc[-1]), 2)
             trend = round(float(values.iloc[-1] - values.iloc[0]), 2) if len(values) > 1 else 0.0
             scores[col] = {'current': current, 'trend': trend, 'data': data_points}
         result.append({'id': ahu_id, 'name': _ahu_name(ahu_id, level), 'scores': scores})
     return result


 def get_raw_score_relationship(device_id: str, time_range: str) -> dict:
     """
     Returns {score_name: {rawMetric, rawUnit, rawData, scoreData}}
     """
     df = _load_csv()
     if df.empty:
         return {}
     df = df[df['ahu_id'] == device_id]
     df = _filter_time_range(df, time_range).sort_values('timestamp')
     if df.empty:
         return {}

     result = {}
     for score_col, (raw_col, raw_unit) in SCORE_RAW_MAP.items():
         if score_col not in df.columns or raw_col not in df.columns:
             continue
         sub = df[['timestamp', score_col, raw_col]].dropna(subset=[score_col, raw_col])
         if sub.empty:
             continue
         result[score_col] = {
             'rawMetric': raw_col,
             'rawUnit': raw_unit,
             'rawData': [
                 {'timestamp': r['timestamp'].isoformat(), 'value': round(float(r[raw_col]), 4)}
                 for _, r in sub.iterrows()
             ],
             'scoreData': [
                 {'timestamp': r['timestamp'].isoformat(), 'value': round(float(r[score_col]), 2)}
                 for _, r in sub.iterrows()
             ],
         }
     return result

 - Step 3: Run tests — expect pass

 cd backend && python -m pytest tests/test_csv_reader.py -v

 Expected: All tests PASS (or SKIP if CSV empty — run Task 1 first)

 - Step 4: Commit

 git add backend/core/csv_reader.py backend/tests/test_csv_reader.py
 git commit -m "feat: add csv_reader utility for health_all_levels.csv"

 ---
 Task 4: Update backend/routes/health_scores.py — replace mock data

 Files:
 - Modify: backend/routes/health_scores.py

 Background:
 Both /api/level/{id}/scores and /api/device/{id}/raw-score-relationship currently return synthetic random data using fake score names (temperature,
 vibration, pressure, airflow, energy). Replace with real CSV reads using csv_reader.

 Also add a new endpoint GET /api/level/{id}/health-index so the frontend can get HealthIndex data by level. The existing /api/dashboard/trend is in
 dashboard.py and queries InfluxDB live — we'll leave it as-is and add the new CSV-based endpoint here.

 - Step 1: Add failing test for real score names

 Add to backend/tests/test_csv_reader.py:

 from fastapi.testclient import TestClient
 import sys, os
 sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
 from main import app

 client = TestClient(app)

 def test_level_scores_returns_fair_names():
     resp = client.get("/api/level/1/scores?time_range=7d")
     assert resp.status_code == 200
     data = resp.json()
     assert 'devices' in data
     if data['devices']:
         scores = data['devices'][0]['scores']
         # Must NOT have fake names
         fake_names = {'temperature', 'vibration', 'pressure', 'airflow', 'energy'}
         actual_names = set(scores.keys())
         assert not actual_names.intersection(fake_names), \
             f"Found fake score names: {actual_names.intersection(fake_names)}"
         # Must have FAIR names
         fair_names = {'energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload'}
         assert fair_names.issubset(actual_names), \
             f"Missing FAIR score names: {fair_names - actual_names}"

 Run: cd backend && python -m pytest tests/test_csv_reader.py::test_level_scores_returns_fair_names -v
 Expected: FAIL (returns fake names currently)

 - Step 2: Rewrite /api/level/{id}/scores to use CSV

 In backend/routes/health_scores.py, replace the get_level_scores function body (keep signature):

 from core.csv_reader import get_score_breakdown, get_health_index_series

 @router.get("/level/{level_id}/scores")
 async def get_level_scores(
     level_id: int,
     time_range: str = Query(default="7d", description="Time range: 24h, 7d, or 30d")
 ):
     valid_ranges = ["24h", "7d", "30d"]
     if time_range not in valid_ranges:
         raise HTTPException(status_code=400, detail=f"Time range must be one of: {', '.join(valid_ranges)}")
     if level_id not in AHU_LEVEL_CONFIG:
         raise HTTPException(status_code=404, detail=f"Level {level_id} is invalid.")

     devices = await asyncio.to_thread(get_score_breakdown, level_id, time_range)
     return {
         "level": level_id,
         "time_range": time_range,
         "devices": devices,
         "generated_at": datetime.now().isoformat(),
     }

 Add the new health-index endpoint:

 @router.get("/level/{level_id}/health-index")
 async def get_level_health_index(
     level_id: int,
     device_id: str = Query(default=None, description="Filter to single device"),
     time_range: str = Query(default="7d", description="Time range: 24h, 7d, or 30d")
 ):
     valid_ranges = ["24h", "7d", "30d"]
     if time_range not in valid_ranges:
         raise HTTPException(status_code=400, detail=f"Time range must be one of: {', '.join(valid_ranges)}")
     if level_id not in AHU_LEVEL_CONFIG:
         raise HTTPException(status_code=404, detail=f"Level {level_id} is invalid.")

     series = await asyncio.to_thread(get_health_index_series, level_id, device_id, time_range)
     return {
         "level": level_id,
         "time_range": time_range,
         "devices": series,
         "generated_at": datetime.now().isoformat(),
     }

 - Step 3: Rewrite /api/device/{id}/raw-score-relationship to use CSV

 Replace the get_raw_score_relationship function body (keep signature):

 from core.csv_reader import get_raw_score_relationship as csv_raw_score

 @router.get("/device/{device_id}/raw-score-relationship")
 async def get_raw_score_relationship(
     device_id: str,
     range: str = Query(default="7d", description="Time range: 24h, 7d, or 30d")
 ):
     valid_ranges = ["24h", "7d", "30d"]
     if range not in valid_ranges:
         raise HTTPException(status_code=400, detail=f"Range must be one of: {', '.join(valid_ranges)}")

     import re
     if not re.match(r'^e\d{4}$', device_id):
         raise HTTPException(status_code=400, detail=f"Invalid device_id: {device_id}")

     from models.schemas import ALLOWED_DEVICES
     if device_id not in ALLOWED_DEVICES:
         raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

     scores = await asyncio.to_thread(csv_raw_score, device_id, range)
     return {
         "device_id": device_id,
         "range": range,
         "scores": scores,
         "generated_at": datetime.now().isoformat(),
     }

 - Step 4: Update endpoints.ts for the new health-index endpoint

 In frontend/src/api/endpoints.ts, add:

 HEALTH_INDEX: (levelId: number, deviceId: string | null, range: string) =>
   `/level/${levelId}/health-index?time_range=${range}${deviceId ? `&device_id=${deviceId}` : ''}`,

 Also fix the existing SCORE_BREAKDOWN endpoint — note backend param is time_range not range:
 SCORE_BREAKDOWN: (levelId: number, range: string) => `/level/${levelId}/scores?time_range=${range}`,

 - Step 5: Run tests

 cd backend && python -m pytest tests/test_csv_reader.py -v

 Expected: All PASS (or SKIP for CSV-dependent tests if CSV is empty)

 - Step 6: Commit

 git add backend/routes/health_scores.py frontend/src/api/endpoints.ts
 git commit -m "feat: replace mock health scores with CSV-backed endpoints, add /health-index route"

 ---
 Chunk 3: Frontend Real Data Integration

 Task 5: Update score types to FAIR names

 Files:
 - Modify: frontend/src/types/index.ts
 - Modify: frontend/src/mocks/generateMockData.ts
 - Modify: frontend/src/components/dashboard/CombinedScoresChart.tsx
 - Modify: frontend/src/components/dashboard/ScoreCardsGrid.tsx (if it has hardcoded score names)

 Background:
 types/index.ts line 5–10 defines ScoreName as 'temperature' | 'vibration' | 'pressure' | 'airflow' | 'energy'. ScoresResponse on line 86 also uses these
 fake names. Both need to become the real FAIR names.

 - Step 1: Locate all uses of fake score names

 grep -r "temperature\|vibration\|pressure\|airflow" frontend/src --include="*.ts" --include="*.tsx" -l

 Note all files returned.

 - Step 2: Update types/index.ts

 Change ScoreName type:

 // BEFORE
 export type ScoreName =
   | 'temperature'
   | 'vibration'
   | 'pressure'
   | 'airflow'
   | 'energy';

 // AFTER
 export type ScoreName =
   | 'energy_anomaly'
   | 'pf_degradation'
   | 'phase_imbalance'
   | 'thd_drift'
   | 'overload';

 Update ScoresResponse:

 // BEFORE
 scores: Record<
   'temperature' | 'vibration' | 'pressure' | 'airflow' | 'energy',
   ...
 >

 // AFTER
 scores: Record<
   'energy_anomaly' | 'pf_degradation' | 'phase_imbalance' | 'thd_drift' | 'overload',
   ...
 >

 - Step 3: Update CombinedScoresChart.tsx SCORE_NAMES

 In frontend/src/components/dashboard/CombinedScoresChart.tsx, update the SCORE_NAMES array:

 const SCORE_NAMES = [
   { key: 'energy_anomaly',  label: 'Energy Anomaly',   color: '#3B82F6' },
   { key: 'pf_degradation',  label: 'PF Degradation',   color: '#8B5CF6' },
   { key: 'phase_imbalance', label: 'Phase Imbalance',  color: '#F59E0B' },
   { key: 'thd_drift',       label: 'THD Drift',        color: '#10B981' },
   { key: 'overload',        label: 'Overload',         color: '#EF4444' },
 ] as const;

 - Step 4: Update generateMockData.ts score keys

 In frontend/src/mocks/generateMockData.ts, update any object keys that use fake score names to FAIR names. This keeps mock data shape consistent so App.tsx
  works during development.

 - Step 5: Update ScoreCardsGrid if it has hardcoded score labels

 Check frontend/src/components/dashboard/ScoreCardsGrid.tsx and update any score name references.

 - Step 6: Confirm TypeScript compiles

 cd frontend && npx tsc --noEmit

 Expected: No errors (or only pre-existing errors).

 - Step 7: Commit

 git add frontend/src/types/index.ts frontend/src/mocks/generateMockData.ts \
         frontend/src/components/dashboard/CombinedScoresChart.tsx \
         frontend/src/components/dashboard/ScoreCardsGrid.tsx
 git commit -m "feat: rename frontend score types from fake names to FAIR names"

 ---
 Task 6: Wire real API calls into App.tsx

 Files:
 - Modify: frontend/src/App.tsx
 - Modify: frontend/src/store/useAppStore.ts (add timeRange state)
 - Modify: frontend/src/api/endpoints.ts (verified in Task 4)

 Background:
 App.tsx currently calls generateHealthIndex(selectedLevel, 48) and generateScoreBreakdowns(selectedLevel, 48). Replace these with useEffect calls to the
 real API endpoints. Show loading skeletons while fetching.

 The API client at frontend/src/api/client.ts already exists — use it.

 - Step 1: Add timeRange to Zustand store

 In frontend/src/store/useAppStore.ts, add:

 // In the state interface:
 timeRange: '24h' | '7d' | '30d';

 // In the initial state:
 timeRange: '7d',

 // Action:
 setTimeRange: (range: '24h' | '7d' | '30d') => set({ timeRange: range }),

 - Step 2: Write a smoke test for App with real API

 Add to frontend/src/__tests__/App.test.tsx (or create if missing):

 import { render, screen, waitFor } from '@testing-library/react';
 import { rest } from 'msw';
 import { setupServer } from 'msw/node';
 import App from '../App';

 const server = setupServer(
   rest.get('http://localhost:8000/api/levels', (req, res, ctx) =>
     res(ctx.json({ levels: [1, 2, 3] }))
   ),
   rest.get('http://localhost:8000/api/level/:id/health-index', (req, res, ctx) =>
     res(ctx.json({ level: 1, devices: [], time_range: '7d' }))
   ),
   rest.get('http://localhost:8000/api/level/:id/scores', (req, res, ctx) =>
     res(ctx.json({ level: 1, devices: [], time_range: '7d' }))
   ),
 );

 beforeAll(() => server.listen());
 afterAll(() => server.close());

 test('renders without crashing', () => {
   render(<App />);
   expect(document.body).toBeTruthy();
 });

 Run: cd frontend && npx jest src/__tests__/App.test.tsx
 Expected: May fail due to missing msw — that's OK, just verify it finds the test file.

 - Step 3: Replace mock generators in App.tsx with API calls

 // Add to imports:
 import { apiClient } from './api/client';
 import { ENDPOINTS } from './api/endpoints';
 import type { HealthIndexResponse, ScoresResponse } from './types';

 // Remove mock data imports (generateHealthIndex, generateScoreBreakdowns, generateRawScoreRelationship)

 // In App():
 const { selectedLevel, selectedDevice, selectDevice, timeRange } = useAppStore();
 const [healthData, setHealthData] = React.useState<HealthIndexResponse | null>(null);
 const [scoresData, setScoresData] = React.useState<ScoresResponse | null>(null);
 const [isLoading, setIsLoading] = React.useState(false);
 const [error, setError] = React.useState<string | null>(null);

 React.useEffect(() => {
   if (!selectedLevel) return;
   setIsLoading(true);
   setError(null);

   Promise.all([
     apiClient.get<HealthIndexResponse>(ENDPOINTS.HEALTH_INDEX(selectedLevel, selectedDevice, timeRange)),
     apiClient.get<ScoresResponse>(ENDPOINTS.SCORE_BREAKDOWN(selectedLevel, timeRange)),
   ])
     .then(([health, scores]) => {
       setHealthData(health);
       setScoresData(scores);
     })
     .catch((err) => setError(err.message))
     .finally(() => setIsLoading(false));
 }, [selectedLevel, selectedDevice, timeRange]);

 Update devices derivation:
 const devices = React.useMemo(
   () => (healthData?.devices ?? []).map((d) => ({ id: d.id, name: d.name, level: selectedLevel! })),
   [healthData, selectedLevel]
 );

 Update healthChartData derivation:
 const healthChartData = React.useMemo(() => {
   if (!healthData?.devices?.length) return [];
   const series = selectedDevice && selectedDevice !== 'all'
     ? healthData.devices.filter((d) => d.id === selectedDevice)
     : healthData.devices;
   const refData = series[0]?.data ?? [];
   return refData.map((point, idx) => {
     const entry: Record<string, any> = {
       timestamp: new Date(point.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
     };
     series.forEach(({ name, data }) => { entry[name] = data[idx]?.value ?? null; });
     return entry;
   });
 }, [healthData, selectedDevice]);

 Update scoreData derivation:
 const scoreData = React.useMemo(() => {
   if (!scoresData?.devices?.length) return {};
   // Use first selected device, or first device in list
   const device = selectedDevice && selectedDevice !== 'all'
     ? scoresData.devices.find((d) => d.id === selectedDevice)
     : scoresData.devices[0];
   return device?.scores ?? {};
 }, [scoresData, selectedDevice]);

 Pass isLoading to components that support it (e.g., show <SkeletonCard /> while loading).

 - Step 4: Add time range selector to dashboard

 In App.tsx, add a <TimeRangePicker> component above the charts. It can be inline — no new file needed:

 const TIME_RANGES = ['24h', '7d', '30d'] as const;

 // In JSX, after LevelSelectorBar:
 <div className="flex gap-2 justify-end px-6 py-2">
   {TIME_RANGES.map((range) => (
     <button
       key={range}
       onClick={() => setTimeRange(range)}
       className={`px-3 py-1 rounded text-sm border ${
         timeRange === range
           ? 'bg-[#1E2A3A] border-[#3B82F6] text-white'
           : 'bg-transparent border-[#1E2A3A] text-[#8A95A5] hover:border-[#3B82F6]'
       }`}
     >
       {range}
     </button>
   ))}
 </div>

 - Step 5: Test in browser

 Start backend: cd backend && uvicorn main:app --reload
 Start frontend: cd frontend && npm run dev

 1. Open http://localhost:5173
 2. Click a level button → verify loading skeleton appears then charts render with real data
 3. Change time range (24h/7d/30d) → verify charts re-fetch and update
 4. Select a specific device → verify health index chart shows single device line

 - Step 6: Commit

 git add frontend/src/App.tsx frontend/src/store/useAppStore.ts \
         frontend/src/api/endpoints.ts
 git commit -m "feat: replace mock data generators with real API calls in App.tsx, add time range selector"

 ---
 Verification

 End-to-End Test Checklist

 # 1. Verify CSV has full history
 python -c "
 import pandas as pd; df = pd.read_csv('data/health_all_levels.csv')
 print('Rows:', len(df))
 print('Levels:', sorted(df['level'].unique()))
 print('Date range:', df['timestamp'].min(), '→', df['timestamp'].max())
 print('Rows per level:', df.groupby('level').size().to_dict())
 "

 # 2. Test backend endpoints
 cd backend && uvicorn main:app --reload &
 curl "http://localhost:8000/api/level/1/health-index?time_range=7d" | python -m json.tool | head -40
 curl "http://localhost:8000/api/level/1/scores?time_range=7d" | python -m json.tool | head -40
 curl "http://localhost:8000/api/device/e0101/raw-score-relationship?range=7d" | python -m json.tool | head -40

 # 3. Verify FAIR score names in response (not fake names)
 curl "http://localhost:8000/api/level/1/scores?time_range=7d" | python -c "
 import json, sys; d = json.load(sys.stdin)
 if d['devices']:
     print('Score keys:', list(d['devices'][0]['scores'].keys()))
 "
 # Expected: ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload']

 # 4. Frontend TypeScript compile check
 cd frontend && npx tsc --noEmit

 # 5. Frontend visual test
 cd frontend && npm run dev
 # Open http://localhost:5173, click level, verify real data in charts

 Critical Files Modified

 ┌───────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────┐
 │                           File                            │                            Change                            │
 ├───────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
 │ scripts/etl/history_generator.py                          │ Iterate all timestamps per device (not just iloc[-1])        │
 ├───────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
 │ scripts/scheduler/scheduler.py                            │ Fix path: scripts/ → scripts/etl/                            │
 ├───────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
 │ backend/core/csv_reader.py                                │ New — CSV reader utilities                                   │
 ├───────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
 │ backend/routes/health_scores.py                           │ Replace mock data with CSV reads; add /health-index endpoint │
 ├───────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
 │ frontend/src/types/index.ts                               │ ScoreName type → FAIR names                                  │
 ├───────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
 │ frontend/src/mocks/generateMockData.ts                    │ Update score keys to FAIR names                              │
 ├───────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
 │ frontend/src/components/dashboard/CombinedScoresChart.tsx │ Update SCORE_NAMES to FAIR names                             │
 ├───────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
 │ frontend/src/api/endpoints.ts                             │ Add HEALTH_INDEX, fix SCORE_BREAKDOWN param name             │
 ├───────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
 │ frontend/src/store/useAppStore.ts                         │ Add timeRange state                                          │
 ├───────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
 │ frontend/src/App.tsx                                      │ Replace mock generators with real API calls                  │
 └───────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────┘
