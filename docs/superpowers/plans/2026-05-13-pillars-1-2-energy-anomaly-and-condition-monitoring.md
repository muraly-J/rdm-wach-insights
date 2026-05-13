# Pillars 1 & 2 — Energy Anomaly + Condition Monitoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship two predictive layers on top of the WACH Insight HVAC pipeline: (1) a per-AHU hourly *energy residual* model that flags units consuming more electricity than the cooling they actually delivered justifies, and (2) a three-track condition-monitoring stack (operating-envelope anomaly detection, physics-derived degradation trends, IEEE/NEMA/ASHRAE rule alerts) — all driven from existing telemetry plus a small set of zero-capex external feeds.

**Architecture:** Three layers. (a) **Data layer**: extend the existing InfluxDB → SQLite ETL with `total_tons`, `sat`, `am`, control deviations, weather (open-meteo), holidays, CMMS events. (b) **Inference layer**: pure Python services under `backend/core/ml/` and `backend/core/cm/` (condition monitoring), each writing results back to SQLite + InfluxDB for fast read paths. (c) **Delivery layer**: new FastAPI routes (`/api/energy/residual`, `/api/cm/alerts`, `/api/cm/trends`, `/api/cm/envelope`) wired into the existing dashboard. No new framework, no new infra — everything composes with the current FastAPI/Zustand/Recharts stack. Pillar 1 = LightGBM per-AHU (or shared with embeddings, decided post-EDA). Pillar 2 Track A = IsolationForest/Mahalanobis. Track B = rolling OLS. Track C = stateful threshold engine. Supervised failure classification is **explicitly deferred** until ≥12 months of data + ≥10 labeled failures.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, LightGBM, scikit-learn (IsolationForest, RANSAC, Mahalanobis), statsmodels (OLS + CIs), pandas, numpy, InfluxDB Cloud (read), SQLite (cache + audit), APScheduler (already present via `backend/core/watchman.py`), pytest + pytest-cov. Frontend: React + Zustand + Recharts (existing).

---

## Phase Overview

| Phase | Title | Duration (est.) | Blocking |
|-------|-------|-----------------|----------|
| 0 | Data audit + schema verification | 3–5 days | gates everything |
| 1 | Data layer: feature ETL + external feeds | 5–7 days | gates 2–5 |
| 2 | Pillar 1 — Energy residual model | 7–10 days | independent of 3–5 |
| 3 | Pillar 2 Track C — Rule-based threshold engine | 4–5 days | independent |
| 4 | Pillar 2 Track B — Degradation trend service | 4–6 days | needs 1 |
| 5 | Pillar 2 Track A — Envelope anomaly detection | 6–8 days | needs 1 |
| 6 | API + frontend integration | 5–7 days | needs 2–5 |
| 7 | Shadow-mode validation + threshold calibration | 7–14 days | needs 6 |
| 8 | Sensor expansion pilot prep | parallel, 3–4 days | independent |

Phases 2, 3, 4/5, 8 can run in parallel after Phase 1. Phase 6 fans them into a single delivery.

---

# Phase 0 — Data Audit & Schema Verification

**Why first:** every assumption in the spec hinges on what's actually in the InfluxDB measurements and the power-meter dataset. Validate before writing one line of model code.

### Task 0.1: Inventory existing telemetry per AHU

**Files:**
- Create: `scripts/audit/inventory_signals.py`
- Create: `docs/audit/2026-05-13-signal-inventory.md` (output)

- [ ] **Step 1: Write a Pydantic-typed script that queries InfluxDB for the last 30 days, lists every field present per `e[LEVEL][NN]` device, computes non-null %, min, max, mean, stddev, and 5-min sample density.**
- [ ] **Step 2: Run it against the live bucket.**

```bash
python scripts/audit/inventory_signals.py --days 30 --out docs/audit/2026-05-13-signal-inventory.md
```

Expected output: a markdown table with one row per (device, signal). Verify the following signals exist and have ≥80% non-null coverage: `energy_import`, `total_tons`, `sat`, `rat`, `rah`, `co2`, `wst`, `wrt`, `dsp`, `dsp_sp`, `rat_sp`, `co2_sp`, `rah_sp`, `mvlv`, `mcvlv`, `fa_dmpr`, `fa_dmpr_min`, `vsd_fb`, `vsd_ctrl`, `fltr`, `sts`, `dp`, `am`, `oct`, `runtime`, `starts`, `power_factor_avg`, `pf_l1`, `pf_l2`, `pf_l3`, `volts_l1_thd`, `volts_l2_thd`, `volts_l3_thd`, `current_l1_thd`, `current_l3_thd`, `current_unbalance`, `volts_unbalance`, `freq`, `power_demand`, `power_total`, `trip`, `hwst`, `hws`, `hwvlv`, `mhvlv`, `heat_p`, `heat_i`, `clg_p`, `clg_i`, `digital_input_1`, `digital_input_2`.

- [ ] **Step 3: Flag every missing or <80% signal in the report under a "Gaps" section. Do NOT proceed to Phase 1 features that depend on missing signals — escalate first.**
- [ ] **Step 4: Commit.**

```bash
git add scripts/audit/inventory_signals.py docs/audit/2026-05-13-signal-inventory.md
git commit -m "chore(audit): signal inventory + coverage report for pillars 1-2"
```

### Task 0.2: Validate `total_tons` per AHU

**Files:**
- Create: `scripts/audit/validate_total_tons.py`
- Create: `docs/audit/2026-05-13-total-tons-validation.md`

- [ ] **Step 1: Pull 14 days of `total_tons`, `wst`, `wrt`, `mvlv`, `sat`, `rat` per AHU.**
- [ ] **Step 2: Sanity checks:** `total_tons ≥ 0` when `sts == 1`; `total_tons ≈ 0` when `sts == 0`; `total_tons` correlates positively with `(rat − sat)` and with `(wrt − wst)`. Report Pearson r per AHU.
- [ ] **Step 3: Identify AHUs where `total_tons` looks calculated (smooth, derived) vs measured (noisy). Document who/what computes it — ask controls team if unclear.**
- [ ] **Step 4: Decide: is raw chilled-water flow per AHU separately available? If yes, add it to Phase 1 ETL. If no, accept `total_tons` as the cooling-work feature and downgrade the "chilled water flow per AHU" sensor gap.**
- [ ] **Step 5: Commit.**

### Task 0.3: Auto/manual mode (`am`) prevalence analysis

**Files:**
- Create: `scripts/audit/am_mode_analysis.py`
- Append: `docs/audit/2026-05-13-signal-inventory.md` (section "AM mode")

- [ ] **Step 1: For each AHU, compute % of last 90 days spent in `am == 1`. Histogram by hour-of-day and day-of-week.**
- [ ] **Step 2: For AHUs with >5% manual-mode time, plot energy distribution under `am == 0` vs `am == 1`.**
- [ ] **Step 3: Decide policy (record in the doc): (a) drop `am == 1` rows from Pillar 1 training, (b) keep them and use `am` as feature, or (c) train two models. Default recommendation: drop from training, keep as feature for Track C alerting (sustained `am==1 > 8h`).**

### Task 0.4: Hot-water signal EDA

**Files:** `scripts/audit/hot_water_eda.py`, append to inventory doc.

- [ ] **Step 1: For 90 days, plot `hwst`, `hws`, `hwvlv`, `mhvlv`, `heat_p`, `heat_i` per AHU. Compute % time non-zero.**
- [ ] **Step 2: If >1% of any AHU shows non-zero hot-water activity, KEEP these signals in Phase 1 ETL and reinstate as Pillar 1 features. Otherwise mark for ETL removal.**
- [ ] **Step 3: Record decision per AHU in doc.**

### Task 0.5: `digital_input_1` / `digital_input_2` semantics

**Files:** `docs/audit/2026-05-13-digital-input-semantics.md`

- [ ] **Step 1: Email/Slack the commissioning engineer with the list of AHUs and ask what these inputs are wired to. No code in this task — pure documentation.**
- [ ] **Step 2: Record per-AHU mapping. If any input is safety-related (freezestat, fire alarm, door switch), add a Track C rule in Phase 3.**

### Task 0.6: Sustained-failure ground-truth audit

**Files:** `docs/audit/2026-05-13-failure-history.md`

- [ ] **Step 1: Request the last 24 months of work orders / maintenance logs from facilities. Categorize: (a) corrective failure events, (b) planned PM, (c) filter changes, (d) coil cleanings.**
- [ ] **Step 2: Count documented failures. If ≥10 with timestamps mapped to AHU IDs, flag Phase 9 (supervised survival model) as eligible for future work. Otherwise lock supervised classification as out of scope for this plan.**

**Phase 0 exit criteria:** all audit docs committed; explicit go/no-go for each Phase 1 feature based on data availability.

---

# Phase 1 — Data Layer: Feature ETL + External Feeds

**Why:** every downstream model needs a clean, consistent, joined per-AHU feature table. Build it once, reuse everywhere. Cache to SQLite for replayability.

### Task 1.1: Define the canonical feature schema

**Files:**
- Create: `backend/models/feature_schema.py`
- Create: `backend/tests/models/test_feature_schema.py`

- [ ] **Step 1: Write failing tests asserting the existence and types of every column in the feature row.**

```python
# backend/tests/models/test_feature_schema.py
from backend.models.feature_schema import AHUFeatureRow

def test_feature_row_required_columns():
    row = AHUFeatureRow.model_construct()
    required = {
        "ahu_id", "ts",
        # target
        "hourly_energy_kwh",
        # cooling work
        "total_tons", "sat", "sat_minus_rat",
        # contextual
        "rat", "rah", "co2", "wst", "wrt", "wst_minus_wrt",
        "oat", "oah", "ghi",
        # control
        "rat_sp", "co2_sp", "rah_sp", "dsp_sp", "dsp", "dsp_dev",
        "fa_dmpr", "fa_dmpr_min", "mvlv", "mcvlv", "oct", "am",
        # health
        "vsd_fb", "vsd_ctrl", "vsd_dev", "fltr", "sts", "dp",
        "runtime", "power_factor_avg",
        # temporal
        "hour_of_day", "day_of_week", "is_weekend", "is_holiday",
        # lags
        "energy_lag_1h", "energy_lag_24h", "energy_lag_168h",
        "energy_rolling_24h_mean", "total_tons_rolling_24h_mean",
        "oat_rolling_24h_mean",
    }
    assert required.issubset(AHUFeatureRow.model_fields.keys())
```

- [ ] **Step 2: Run; expect fail (`ModuleNotFoundError`).**

```bash
cd backend && pytest tests/models/test_feature_schema.py -v
```

- [ ] **Step 3: Implement `AHUFeatureRow` as a Pydantic `BaseModel` with strict types (`float`, `bool`, `int`, `datetime`) and `Optional[float]` where appropriate.**
- [ ] **Step 4: Re-run; expect pass.**
- [ ] **Step 5: Commit.**

```bash
git commit -m "feat(models): add canonical AHU feature row schema for ML pipeline"
```

### Task 1.2: Open-meteo weather adapter

**Files:**
- Create: `backend/core/external/weather_openmeteo.py`
- Create: `backend/tests/core/external/test_weather_openmeteo.py`

- [ ] **Step 1: Failing test using `responses` or `httpx.MockTransport` — stub the open-meteo `/v1/forecast` and `/v1/archive` endpoints, assert the adapter returns a DataFrame with columns `["ts", "oat", "oah", "ghi"]` indexed hourly.**
- [ ] **Step 2: Verify fails.**
- [ ] **Step 3: Implement `fetch_weather(lat: float, lon: float, start: datetime, end: datetime) -> pd.DataFrame`. Use hospital lat/lon from `backend/config.py` (add if missing). Variables: `temperature_2m`, `relative_humidity_2m`, `shortwave_radiation`. Use the archive API for historical, forecast API for now+future. Cache responses to SQLite table `weather_cache` keyed on (lat, lon, ts).**
- [ ] **Step 4: Verify passes.**
- [ ] **Step 5: Add backfill CLI:**

```bash
python -m backend.core.external.weather_openmeteo backfill --start 2025-01-01 --end 2026-05-13
```

- [ ] **Step 6: Commit.**

### Task 1.3: Malaysian public holiday calendar

**Files:**
- Create: `backend/core/external/holidays_my.py`
- Create: `backend/tests/core/external/test_holidays_my.py`
- Optional dep: add `holidays>=0.50` to `backend/requirements.txt`

- [ ] **Step 1: Failing test asserting `is_holiday(date(2026,5,1))` returns True (Labour Day) and `is_holiday(date(2026,5,2))` returns False.**
- [ ] **Step 2: Implement using the `holidays` package (`holidays.country_holidays("MY", subdiv="<state>")`). Confirm the hospital's state subdivision with facilities; default to federal if unknown.**
- [ ] **Step 3: Verify, commit.**

### Task 1.4: CMMS event ingestion (stub-first)

**Files:**
- Create: `backend/core/external/cmms.py`
- Create: `backend/models/cmms_event.py`
- Create: `backend/tests/core/external/test_cmms.py`
- DB migration: `backend/data/migrations/0001_cmms_events.sql`

- [ ] **Step 1: Failing test asserting `CMMSClient.events_for(ahu_id, since)` returns `list[CMMSEvent]` with fields `event_id, ahu_id, ts, event_type ∈ {"filter_change","coil_clean","belt_replace","corrective_failure","planned_pm","other"}, notes`.**
- [ ] **Step 2: SQL migration: `CREATE TABLE cmms_events (event_id TEXT PRIMARY KEY, ahu_id TEXT NOT NULL, ts TIMESTAMP NOT NULL, event_type TEXT NOT NULL, notes TEXT, source TEXT NOT NULL DEFAULT 'manual')`.**
- [ ] **Step 3: Implement two backends behind one interface: `CSVCMMSBackend` (reads `data/cmms_export.csv`) and `APICMMSBackend` (HTTP — stubbed for now, returns NotImplemented). Default to CSV.**
- [ ] **Step 4: Add CLI for facilities to import CSV exports: `python -m backend.core.external.cmms import data/cmms_export.csv`.**
- [ ] **Step 5: Verify, commit.**

### Task 1.5: Feature builder service

**Files:**
- Create: `backend/core/etl/feature_builder.py`
- Create: `backend/tests/core/etl/test_feature_builder.py`
- Fixtures: `backend/tests/fixtures/influx_sample_e0101_30d.parquet`

- [ ] **Step 1: Failing test — `build_features(ahu_id="e0101", start, end)` returns DataFrame conforming to `AHUFeatureRow` for every hour in range, with derived columns populated (`sat_minus_rat`, `wst_minus_wrt`, `dsp_dev`, `vsd_dev`, lags, rolling means, temporal flags).**
- [ ] **Step 2: Implement the builder:**
  - Pull raw 5-min telemetry from InfluxDB via `backend/core/influx_client.py`.
  - Resample to hourly: `energy_import` → diff; `total_tons` → mean; everything else → mean except `sts`, `am`, `oct`, `fltr`, `trip` → mode/max.
  - Join weather on hourly `ts`.
  - Join holiday flag.
  - Compute derived columns.
  - Drop rows where `sts == 0` (AHU off) for Pillar 1 training set; keep them tagged for Track C.
  - Apply `am` policy from Task 0.3.
  - Persist to SQLite table `ahu_features` keyed on `(ahu_id, ts)`.
- [ ] **Step 3: Verify, commit.**

### Task 1.6: Backfill + scheduled refresh

**Files:**
- Modify: `backend/core/watchman.py` (existing scheduler)
- Create: `backend/core/etl/scheduler_features.py`

- [ ] **Step 1: Add APScheduler job `refresh_features_hourly` running at HH:05 — builds the most recent 2 hours of features for every AHU in `AHU_LEVEL_CONFIG`.**
- [ ] **Step 2: Add backfill CLI:**

```bash
python -m backend.core.etl.scheduler_features backfill --start 2025-01-01
```

- [ ] **Step 3: Smoke test:** run backfill for one AHU, query SQLite, assert row count = expected hours.
- [ ] **Step 4: Commit.**

**Phase 1 exit criteria:** SQLite contains complete, validated `ahu_features` rows for every AHU in `AHU_LEVEL_CONFIG` over the full history available in InfluxDB; weather + holidays + CMMS joined; scheduler running.

---

# Phase 2 — Pillar 1: Energy Residual Model

### Task 2.1: Baseline — seasonal naive

**Files:**
- Create: `backend/core/ml/pillar1/baselines.py`
- Create: `backend/tests/core/ml/pillar1/test_baselines.py`

- [ ] **Step 1: Failing test — `SeasonalNaive(period_hours=168).predict(history)` returns `history[t-168]` for each forecast index.**
- [ ] **Step 2: Implement `SeasonalNaive` and `WeekdayHourMean` baselines.**
- [ ] **Step 3: Compute MAPE on the most recent 14 days per AHU; save to `data/baselines_e<id>.json`.**
- [ ] **Step 4: Verify, commit.**

### Task 2.2: Walk-forward time-based CV harness

**Files:**
- Create: `backend/core/ml/pillar1/cv.py`
- Create: `backend/tests/core/ml/pillar1/test_cv.py`

- [ ] **Step 1: Failing test asserting `walk_forward_splits(df, train_days=42, test_days=7, step_days=7)` yields tuples of `(train_idx, test_idx)` with no overlap and strictly increasing `ts`.**
- [ ] **Step 2: Implement and verify.**
- [ ] **Step 3: Commit.**

### Task 2.3: LightGBM training pipeline

**Files:**
- Create: `backend/core/ml/pillar1/train.py`
- Create: `backend/core/ml/pillar1/model_registry.py`
- Create: `backend/tests/core/ml/pillar1/test_train.py`
- Add dep: `lightgbm>=4.3` to `requirements.txt`

- [ ] **Step 1: Failing test using a synthetic 90-day dataframe — `train_per_ahu("e0101")` returns a fitted `lgb.Booster`, training MAPE < 50%, and persists to `data/models/pillar1/e0101.lgb` + a sidecar JSON of `{feature_list, train_window, train_mape, val_mape, version, git_sha}`.**
- [ ] **Step 2: Implement:**
  - Feature list: every column in `AHUFeatureRow` except identifiers and target.
  - Filter: `sts == 1`, `am == 0` (per Task 0.3 policy).
  - Hyperparameters: start with `num_leaves=31, learning_rate=0.05, n_estimators=600, min_data_in_leaf=50, objective="regression_l1"` (MAE — robust to outliers).
  - Early stopping on last fold of walk-forward CV.
  - Log to MLflow if `MLFLOW_TRACKING_URI` is set, else to local JSON.
- [ ] **Step 3: Verify, commit.**

### Task 2.4: Shared-vs-per-AHU model decision

**Files:**
- Create: `scripts/ml/compare_shared_vs_per_ahu.py`
- Create: `docs/audit/2026-05-13-pillar1-model-topology.md`

- [ ] **Step 1: Train (a) one model per AHU and (b) one shared model with `ahu_id` as a categorical feature + per-AHU embeddings (LightGBM `categorical_feature`).**
- [ ] **Step 2: Compare hold-out MAPE per AHU. Decision rule: pick shared model if median per-AHU MAPE is within 2 percentage points of per-AHU models; otherwise per-AHU.**
- [ ] **Step 3: Record decision + numbers in the audit doc.**
- [ ] **Step 4: Commit.**

### Task 2.5: Residual service

**Files:**
- Create: `backend/core/ml/pillar1/residual_service.py`
- Create: `backend/tests/core/ml/pillar1/test_residual_service.py`
- DB migration: `backend/data/migrations/0002_residuals.sql`

- [ ] **Step 1: SQL migration: `CREATE TABLE energy_residuals (ahu_id TEXT, ts TIMESTAMP, actual_kwh REAL, predicted_kwh REAL, residual_kwh REAL, residual_pct REAL, model_version TEXT, PRIMARY KEY (ahu_id, ts))`.**
- [ ] **Step 2: Failing test — `compute_residuals("e0101", start, end)` writes rows to `energy_residuals` matching `(actual - predicted)`.**
- [ ] **Step 3: Implement. Also compute rolling 24h mean residual per AHU and persist.**
- [ ] **Step 4: Verify, commit.**

### Task 2.6: Inefficiency flag

**Files:** `backend/core/ml/pillar1/flags.py`, test file mirror.

- [ ] **Step 1: Failing test — `is_inefficient("e0101", as_of)` returns True iff rolling-24h residual mean > AHU-specific threshold (default: 2σ above the AHU's own residual std over the last 30 days, *and* persistently positive for ≥18 of last 24 hours).**
- [ ] **Step 2: Implement, verify, commit.**

### Task 2.7: Scheduled hourly inference

**Files:** modify `backend/core/watchman.py`; add `inference_pillar1` job at HH:10.

- [ ] **Step 1: Job loads model registry, pulls last 2 hours of features, runs inference, persists residuals + flags.**
- [ ] **Step 2: Verify with a one-AHU smoke run.**
- [ ] **Step 3: Commit.**

**Phase 2 exit criteria:** every active AHU has hourly residuals being written; per-AHU hold-out MAPE ≤ 15% on stable units; ≥20% MAPE improvement over the seasonal-naive baseline (success criteria from spec).

---

# Phase 3 — Pillar 2 Track C: Rule-Based Threshold Engine

**Why first among Pillar 2 tracks:** lowest risk, fastest to value, no model training. Establishes the alert taxonomy other tracks plug into.

### Task 3.1: Rule definition DSL

**Files:**
- Create: `backend/core/cm/track_c/rules.py`
- Create: `backend/core/cm/track_c/rule_loader.py`
- Create: `backend/core/cm/track_c/rules.yaml`
- Create: `backend/tests/core/cm/track_c/test_rules.py`

- [ ] **Step 1: Failing test — load `rules.yaml`, evaluate a rule against a sample timeseries, assert an alert is raised iff threshold breached for the required sustain duration.**
- [ ] **Step 2: Implement YAML schema:**

```yaml
- name: voltage_thd_high
  signal: volts_l1_thd
  op: ">"
  threshold: 5.0
  sustain: 1h
  standard: IEEE 519
  severity: medium
  action: "Power quality investigation"
```

- [ ] **Step 3: Implement `RuleEngine.evaluate(df: pd.DataFrame) -> list[Alert]` with stateful sustain-duration logic (uses prior evaluation state from SQLite to handle restarts).**
- [ ] **Step 4: Encode all rules from the spec:**
  - `volts_l{1,2,3}_thd > 5% / 1h` → IEEE 519
  - `current_l{1,3}_thd > 8% / 1h` → IEEE 519
  - `current_unbalance > 10% / 15min` → NEMA MG-1
  - `volts_unbalance > 2% / 15min` → NEMA MG-1
  - `power_factor_avg < 0.85 / 1h` → site policy
  - `max(pf_l1,pf_l2,pf_l3) - min(...) > 0.1 / 1h` → derived
  - `dp > fltr_threshold` (per-AHU config) → filter replace
  - `abs(dsp - dsp_sp) > 30Pa / 30min` → damper/fan
  - `trip == 1` → immediate dispatch
  - `starts_per_day > baseline + 3σ` → control loop
  - `am == 1 / >8h` → manual override left active
  - `abs(freq - 50) > 0.5Hz / 5min` → grid stability
  - `sts == 0 during scheduled occupancy` → unplanned downtime
  - `mvlv == 100% / 2h AND abs(rat - rat_sp) > 1°C` → coil fouling/undersized
  - Add any safety-related rule that emerges from Task 0.5 (digital inputs).
- [ ] **Step 5: Verify, commit.**

### Task 3.2: Alert persistence + dedup

**Files:**
- DB migration: `backend/data/migrations/0003_alerts.sql`
- Create: `backend/core/cm/alerts/store.py`
- Test mirror.

- [ ] **Step 1: SQL: `CREATE TABLE cm_alerts (alert_id TEXT PRIMARY KEY, ahu_id TEXT, rule_name TEXT, opened_at TIMESTAMP, closed_at TIMESTAMP, peak_value REAL, severity TEXT, status TEXT CHECK(status IN ('open','acknowledged','closed')) DEFAULT 'open', source_track TEXT CHECK(source_track IN ('A','B','C')))`.**
- [ ] **Step 2: Dedup rule: within an open alert window for the same `(ahu_id, rule_name)`, do not open a second alert; update `peak_value`. Close when condition clears for the rule's sustain duration.**
- [ ] **Step 3: Failing test, implement, verify, commit.**

### Task 3.3: Scheduled evaluation

**Files:** modify `backend/core/watchman.py`; add `cm_track_c` job every 5 minutes.

- [ ] **Step 1: Job pulls the last 1 hour of raw telemetry per AHU, runs `RuleEngine.evaluate`, persists alerts.**
- [ ] **Step 2: Smoke test, commit.**

**Phase 3 exit criteria:** all spec rules implemented, false-positive rate < 1 alert per AHU per week measured during Phase 7 shadow mode.

---

# Phase 4 — Pillar 2 Track B: Degradation Trend Service

### Task 4.1: Derived metric calculators

**Files:**
- Create: `backend/core/cm/track_b/metrics.py`
- Create: `backend/tests/core/cm/track_b/test_metrics.py`

- [ ] **Step 1: Failing tests — given synthetic dataframes, assert each calculator returns the right value:**
  - `heat_exchange_delta_T = wst - wrt` (per row, then daily mean)
  - `filter_loading = dp` rolling 24h mean
  - `valve_authority = Δsat / Δmvlv` via RANSAC fit (robust slope) on a 24h window
  - `cooling_efficiency = hourly_energy_kwh / total_tons` (guarded for `total_tons > 0.1`)
  - `fan_effort_per_pressure = vsd_fb / dsp` at constant load buckets (binned by `total_tons` deciles)
  - `start_frequency = starts_per_day`
  - `pf_trend = power_factor_avg` daily median
  - `runtime_since_last_reset = runtime - runtime_at_last_cmms_event`
- [ ] **Step 2: Implement each, verify, commit.**

### Task 4.2: Rolling OLS trend with CIs

**Files:**
- Create: `backend/core/cm/track_b/trend.py`
- Create: `backend/tests/core/cm/track_b/test_trend.py`

- [ ] **Step 1: Failing test — `fit_trend(series, window_days=30)` returns `TrendResult(slope, slope_ci_low, slope_ci_high, p_value, projected_breach_days)` using statsmodels OLS with HAC (Newey-West) standard errors.**
- [ ] **Step 2: Implement. `projected_breach_days = (threshold - current_value) / slope` (None if slope direction is opposite of failure direction).**
- [ ] **Step 3: Verify, commit.**

### Task 4.3: Per-metric threshold + direction config

**Files:** `backend/core/cm/track_b/config.yaml`, loader, tests.

- [ ] **Step 1: YAML maps each metric to `failure_direction ∈ {"up","down"}` and `threshold` (where applicable). Examples:**
  - `cooling_efficiency`: direction `up`, threshold = AHU's 30-day baseline mean × 1.2
  - `heat_exchange_delta_T`: direction `down`, threshold = baseline × 0.7
  - `dp` (filter loading): direction `up`, threshold = AHU-specific `fltr` alarm point
  - `valve_authority` (|slope|): direction `down`, threshold = baseline × 0.5
  - `fan_effort_per_pressure`: direction `up`, threshold = baseline × 1.15
- [ ] **Step 2: Loader + tests, commit.**

### Task 4.4: Alert emission

**Files:** `backend/core/cm/track_b/service.py`, test mirror.

- [ ] **Step 1: Failing test — when slope CI excludes zero in failure direction AND `projected_breach_days < 30`, emit an alert through `backend/core/cm/alerts/store.py` with `source_track='B'`.**
- [ ] **Step 2: Implement, verify, commit.**

### Task 4.5: Scheduled daily evaluation

**Files:** modify `backend/core/watchman.py`; add `cm_track_b` job at 02:00.

- [ ] **Step 1: Job runs trend calc per (AHU, metric) over 30 and 90 day windows, persists `TrendResult` to SQLite `cm_trends`, emits alerts.**
- [ ] **Step 2: DB migration: `CREATE TABLE cm_trends (ahu_id TEXT, metric TEXT, window_days INT, computed_at TIMESTAMP, slope REAL, slope_ci_low REAL, slope_ci_high REAL, p_value REAL, current_value REAL, projected_breach_days REAL, PRIMARY KEY (ahu_id, metric, window_days, computed_at))`.**
- [ ] **Step 3: Smoke test, commit.**

**Phase 4 exit criteria:** every AHU has fresh 30/90-day trends nightly for all derived metrics; trends visible via Phase 6 API.

---

# Phase 5 — Pillar 2 Track A: Operating Envelope Anomaly Detection

### Task 5.1: Baseline window selection

**Files:**
- Create: `backend/core/cm/track_a/baseline.py`
- Create: `backend/tests/core/cm/track_a/test_baseline.py`

- [ ] **Step 1: Failing test — `select_baseline_window("e0101")` returns the earliest 60 contiguous days where `sts==1` and `am==0` ≥ 80% of the time AND no Track C high-severity alerts fired AND no CMMS corrective event.**
- [ ] **Step 2: Implement, verify, commit.**

### Task 5.2: Feature vector for envelope

**Files:** `backend/core/cm/track_a/features.py`, test mirror.

- [ ] **Step 1: Failing test — `envelope_features(df)` returns DataFrame with exactly these columns:**
  - `vsd_dev`, `dp`, `dsp_dev`
  - `vsd_fb_std_5min`, `dsp_std_5min`
  - `sat_minus_rat`, `wst_minus_wrt`
  - `tons_per_vsd = total_tons / max(vsd_fb, 1)`
  - `valve_response_err = mvlv - expected_mvlv_given_rat_error` (linear pre-fit on baseline)
  - `clg_p`, `clg_i`
  - `current_unbalance`, `volts_unbalance`, `power_factor_avg`
  - `pf_phase_spread = max(pf_l1,pf_l2,pf_l3) - min(...)`
  - `volts_l1_thd, volts_l2_thd, volts_l3_thd, current_l1_thd, current_l3_thd`
  - `freq`, `power_demand_to_total = power_demand / max(power_total, 1)`
  - `starts_per_day`, `runtime`, `am_duration_24h`
- [ ] **Step 2: Implement, verify, commit.**

### Task 5.3: Model — IsolationForest + per-AHU Mahalanobis

**Files:**
- Create: `backend/core/cm/track_a/model.py`
- Create: `backend/core/cm/track_a/train.py`
- Test mirror.

- [ ] **Step 1: Failing test — `fit("e0101", baseline_df)` produces a fitted artifact persisted at `data/models/track_a/e0101.joblib` containing both an `IsolationForest(n_estimators=200, contamination=0.01, random_state=42)` and a Mahalanobis covariance estimator (`sklearn.covariance.MinCovDet`) over the same features.**
- [ ] **Step 2: `score(df)` returns DataFrame with `iso_score` (normalized to 0–1) and `mahal_score` (chi² p-value transformed to 0–1) and `anomaly_score = max(iso_score, mahal_score)` per row.**
- [ ] **Step 3: Implement, verify, commit.**

### Task 5.4: Threshold calibration

**Files:** `backend/core/cm/track_a/threshold.py`, test.

- [ ] **Step 1: Failing test — `calibrate_threshold("e0101")` returns the 99.5th percentile of `anomaly_score` over the baseline window.**
- [ ] **Step 2: Implement, verify, commit.**

### Task 5.5: Inference + alert emission

**Files:** `backend/core/cm/track_a/service.py`; modify `watchman.py` (`cm_track_a` job every 30 min).

- [ ] **Step 1: Failing test — when rolling 24h mean of `anomaly_score` exceeds threshold for ≥3h, emit Track A alert.**
- [ ] **Step 2: Implement, verify.**
- [ ] **Step 3: DB migration `0004_envelope_scores.sql`: `CREATE TABLE cm_envelope_scores (ahu_id TEXT, ts TIMESTAMP, iso_score REAL, mahal_score REAL, anomaly_score REAL, threshold REAL, PRIMARY KEY (ahu_id, ts))`.**
- [ ] **Step 4: Commit.**

**Phase 5 exit criteria:** every AHU scored every 30 min; threshold breaches surface as Track A alerts with explanatory top-3-feature contributions.

---

# Phase 6 — API + Frontend Integration

### Task 6.1: Energy residual route

**Files:**
- Create: `backend/routes/energy_residual.py`
- Create: `backend/tests/routes/test_energy_residual.py`
- Modify: `backend/main.py` (register router)

- [ ] **Step 1: Failing test — `GET /api/energy/residual?ahu_id=e0101&range=7d` returns `{ahu_id, series: [{ts, actual_kwh, predicted_kwh, residual_kwh, residual_pct}], flag: bool, threshold: float}`.**
- [ ] **Step 2: Implement, register router, verify, commit.**

### Task 6.2: Condition-monitoring alerts route

**Files:**
- Create: `backend/routes/cm_alerts.py`
- Test mirror.

- [ ] **Step 1: Failing tests for `GET /api/cm/alerts?ahu_id=...&status=open`, `POST /api/cm/alerts/{id}/acknowledge`, `POST /api/cm/alerts/{id}/close`.**
- [ ] **Step 2: Implement, verify, commit.**

### Task 6.3: Trends + envelope routes

**Files:** `backend/routes/cm_trends.py`, `backend/routes/cm_envelope.py`, tests.

- [ ] **Step 1: `GET /api/cm/trends?ahu_id=...&metric=...&window=30` → latest `TrendResult` + history.**
- [ ] **Step 2: `GET /api/cm/envelope?ahu_id=...&range=24h` → time series of `anomaly_score` + threshold.**
- [ ] **Step 3: Verify, commit.**

### Task 6.4: Zustand store extensions

**Files:**
- Modify: `frontend/src/store/useAppStore.ts`
- Create: `frontend/src/api/pillar1.ts`, `frontend/src/api/cm.ts`

- [ ] **Step 1: Add typed fetchers + store slices `energyResidual`, `cmAlerts`, `cmTrends`, `cmEnvelope`.**
- [ ] **Step 2: Failing Jest test for store actions, verify, commit.**

### Task 6.5: Residual chart component

**Files:**
- Create: `frontend/src/components/Pillar1/EnergyResidualChart.tsx`
- Create: `frontend/src/__tests__/EnergyResidualChart.test.tsx`

- [ ] **Step 1: Failing test — renders dual-line chart (actual vs predicted) with shaded residual band and red marker when `flag === true`.**
- [ ] **Step 2: Implement using Recharts `LineChart` + `ReferenceArea`. Follow existing dark-luxury theme (`#00E5A0` accent).**
- [ ] **Step 3: Verify, commit.**

### Task 6.6: Alert inbox component

**Files:**
- Create: `frontend/src/components/Pillar2/AlertInbox.tsx`
- Test mirror.

- [ ] **Step 1: Failing test — renders open alerts grouped by AHU + severity, supports ack/close actions hitting the API.**
- [ ] **Step 2: Implement, verify, commit.**

### Task 6.7: Trends + envelope panels

**Files:**
- Create: `frontend/src/components/Pillar2/DegradationTrendsPanel.tsx`
- Create: `frontend/src/components/Pillar2/EnvelopePanel.tsx`
- Tests.

- [ ] **Step 1: Trends panel: small-multiples (Recharts) per derived metric with slope arrow + projected breach date.**
- [ ] **Step 2: Envelope panel: anomaly score time series with threshold line, plus top-3 contributing features as a bar list.**
- [ ] **Step 3: Verify, commit.**

### Task 6.8: Dashboard wiring

**Files:** modify `frontend/src/App.tsx` and the existing dashboard composition.

- [ ] **Step 1: Add a "Predictive" tab (or extend existing dashboard) showing the three new panels gated on a selected AHU.**
- [ ] **Step 2: Manual UI test: `cd frontend && npm run dev`, open `http://localhost:3000`, pick an AHU, verify panels render with live data. Test golden path + a known-anomalous AHU.**
- [ ] **Step 3: Commit.**

**Phase 6 exit criteria:** all four endpoints live; the dashboard surfaces Pillar 1 residual, Pillar 2 alerts/trends/envelope for every AHU in `AHU_LEVEL_CONFIG`; Jest + pytest both green; manual UI sanity passes.

---

# Phase 7 — Shadow-Mode Validation + Threshold Calibration

**Why a distinct phase:** thresholds set in code are guesses. Real values come from observing the system in production with humans in the loop.

### Task 7.1: Shadow-mode flag

**Files:** modify `backend/config.py`, add `CM_ALERTS_SHADOW=true` (default true initially).

- [ ] **Step 1: When true, alerts are written but their `severity` is forced to `shadow` and they do NOT trigger any downstream notification (email/Slack/Telegram).**
- [ ] **Step 2: Commit.**

### Task 7.2: Daily alert review report

**Files:**
- Create: `backend/core/cm/reports/daily_review.py`
- Create: a Markdown report generator → `data/reports/cm_daily_<date>.md`
- Modify scheduler to run at 08:00.

- [ ] **Step 1: Report shows: alerts opened/closed in last 24h per AHU per track, FP candidates (low-severity, brief), rules with highest fire rates.**
- [ ] **Step 2: Verify on a 7-day backfill, commit.**

### Task 7.3: Threshold calibration loop

**Files:** `scripts/cm/calibrate_thresholds.py`, `docs/audit/2026-05-13-threshold-calibration-log.md`.

- [ ] **Step 1: For each rule and Track A threshold, compute alerts/AHU/week over the last 30 days. If > 1/AHU/week and ops marks them as non-actionable, raise the threshold by one step (per rule's defined granularity) and re-run.**
- [ ] **Step 2: After 14 days of shadow + calibration, flip `CM_ALERTS_SHADOW=false`. Document in log.**
- [ ] **Step 3: Commit.**

### Task 7.4: Pillar 1 hold-out report

**Files:** `scripts/ml/pillar1_eval_report.py`, `docs/audit/2026-05-13-pillar1-eval.md`.

- [ ] **Step 1: Compute per-AHU hold-out MAPE on the most recent 14 days. Compare to seasonal-naive baseline. Flag AHUs missing the ≤15% MAPE target.**
- [ ] **Step 2: For failing AHUs, classify cause: insufficient data, unstable operating profile, missing feature, sensor drift. Record decision: (a) retrain with more data, (b) per-AHU hyperparameter tune, (c) exclude from inefficiency flagging until profile stabilizes.**
- [ ] **Step 3: Commit.**

**Phase 7 exit criteria:** Pillar 1 meets the ≥20%-over-baseline + ≤15% per-AHU MAPE success criteria; Pillar 2 FP rate < 1 alert/AHU/week; shadow mode disabled.

---

# Phase 8 — Sensor Expansion Pilot Prep (parallel)

### Task 8.1: Vibration sensor pilot spec

**Files:** `docs/specs/2026-05-13-vibration-pilot.md`.

- [ ] **Step 1: Pick 3–5 candidate AHUs (largest motors, most critical zones — e.g. ICU, OT). Document model selection criteria. Suggested hardware: Banner QM30VT or ABB Smart Sensor; triaxial; ≥5 kHz; wireless if conduit access is hard.**
- [ ] **Step 2: Define ingestion path: vibration → MQTT broker → InfluxDB → existing ETL. Spec the FFT-band features to extract (1×, 2×, blade-pass, BPFO/BPFI/BSF/FTF given bearing geometry).**
- [ ] **Step 3: Cost estimate + procurement ask. No code yet.**

### Task 8.2: Stub ingestion adapter

**Files:** `backend/core/external/vibration.py`, test mirror.

- [ ] **Step 1: Define `VibrationReading` Pydantic schema (axes, ts, rms, peak, crest_factor, kurtosis, fft_bands).**
- [ ] **Step 2: Stub backend that reads from a CSV (for pilot) or MQTT (later). Tests assert schema conformance.**
- [ ] **Step 3: Commit.**

### Task 8.3: Track A/B/C extension hooks

**Files:** add vibration-aware feature paths into existing Track A features (Task 5.2), Track B metrics (Task 4.1), and Track C rules (Task 3.1) — guarded by `if vibration_available(ahu_id)`.

- [ ] **Step 1: Track C: add ISO 10816-3 vibration severity zone rules (zones A/B/C/D).**
- [ ] **Step 2: Tests + commit. These remain inactive until hardware arrives.**

**Phase 8 exit criteria:** pilot spec approved by facilities; ingestion + scoring paths ready to receive data on day one of sensor install.

---

# Out of Scope (Explicit)

These will be addressed in follow-up plans, not here:

- **Supervised failure classification / survival analysis** — gated on ≥12 months data + ≥10 labeled failure events (Task 0.6 determines whether this is feasible later).
- **Setpoint optimization / counterfactual "what-if"** — needs offline RL on the trained residual model or controlled A/B perturbation; both are downstream initiatives.
- **Chiller plant + hot water plant telemetry integration** — listed in the sensor gap analysis; separate plan.
- **MCSA (motor current signature analysis) high-frequency waveforms** — needs dedicated hardware; separate plan.

---

# Cross-Cutting Conventions

- **Commits:** one per checkbox step where it changes code. Follow `<type>: <scope>` from `CLAUDE.md`.
- **Tests:** TDD throughout — every task starts with a failing test. Tests live next to source: `backend/tests/core/ml/pillar1/...` mirrors `backend/core/ml/pillar1/...`.
- **AHU IDs:** every code path validates against `AHU_LEVEL_CONFIG` in `backend/models/schemas.py`. Never hardcode.
- **Persistence:** SQLite for cache + audit + dedup state; InfluxDB read-only for raw telemetry; no new datastore.
- **Scheduler:** one APScheduler instance in `backend/core/watchman.py`. Jobs: `refresh_features_hourly`, `inference_pillar1`, `cm_track_a`, `cm_track_b`, `cm_track_c`, `cm_daily_review`.
- **Config:** all thresholds + windows live in YAML under `backend/core/cm/**/*.yaml` — never in Python literals — so ops can tune without redeploying.
- **Logging:** every alert + model decision logged with `model_version` and `git_sha` for audit.

---

# Self-Review Notes (author's pass)

1. **Spec coverage** — every variable in the original spec is allocated: target & contextual features → Task 1.5 (ETL); cooling work → 1.5 + 0.2; control + health features → 1.5; lag/rolling → 1.5; exclusions (hot water, clg_p/i, discrete events) → 0.4 / handled in Track A or C as appropriate; AM mode policy → 0.3 + 2.3; sensor gaps → Phase 8 + Task 0.5.
2. **No placeholders** — file paths, SQL DDL, rule list, hyperparameters, success thresholds, scheduler cadence, and YAML schema are all concrete. Where the choice depends on data (per-AHU vs shared model, AM policy, hot-water inclusion), the decision is gated on a Phase 0 audit task whose output drives the call.
3. **Type consistency** — `AHUFeatureRow` is the single canonical row schema referenced by Phase 1 ETL, Phase 2 training, Phase 4 metrics, and Phase 5 envelope features. Alert and trend SQL DDL is defined once and referenced from all downstream tracks.
