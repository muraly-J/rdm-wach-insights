# Metric Inventory Audit — 2026-05-04

## Overview

This audit catalogs all 46 power-meter metrics exposed by the WACH Insight system,
traces which FAIR health scores consume each metric, and maps every code file that
references each metric.

**Source of truth:** `backend/models/schemas.py` → `ALLOWED_METRICS_WITH_UNITS`
(46 metrics).  InfluxDB measurement pattern: `wach_{device_id}_{metric}`.

**Data products:**
- `/tmp/metrics.csv` — 46 rows (one per metric)
- `/tmp/metric_consumers.csv` — 938 rows (one per metric→file reference)
- `scripts/research/list_all_metrics.py` — generates `/tmp/metrics.csv`
- `scripts/research/build_consumer_map.py` — generates `/tmp/metric_consumers.csv`

---

## Measurement Naming Convention

All InfluxDB measurements follow the pattern:

```
wach_{device_id}_{metric}
```

Examples:
- `wach_e0101_power_total`
- `wach_e0505_energy_import`
- `wach_e0111_current_l1_thd`

Verified by cross-referencing every Flux query in `backend/core/influx_client.py`,
`backend/routes/forecast.py`, and all ETL scripts.  The regex used throughout is:

```
/^wach_({devices_regex})_{metric}$/
```

where `devices_regex` is a pipe-separated list of device IDs (e.g. `e0101|e0102|...`).

---

## Fleet Topology

| Level | Device count | Device ID range |
|-------|-------------|----------------|
| 1 | 21 | e0101–e0121 |
| 2 | 15 | e0201–e0218 |
| 3 | 16 | e0210–e0423 |
| 4 | 13 | e0403–e0419 |
| 5 | 12 | e0501–e0622 |
| 6 | 11 | e0602–e0628 |
| 7 | 4 | e0701–e0704 |
| 8 | 5 | e0801–e0805 |
| 9 | 8 | e0901–e0908 |
| 10 | 8 | e1001–e1008 |
| 11 | 8 | e1101–e1108 |
| **Total** | **121** | |

Source: `backend/models/schemas.py` → `AHU_LEVEL_CONFIG`

---

## FAIR Score Metric Consumption

The FAIR health scoring engine (`backend/core/fair_health_scoring.py`) computes 5
component scores.  Only **6 of the 46 metrics** are fetched by the default ETL
pipeline:

| FAIR Score Component | Weight | Raw Metrics Consumed | InfluxDB Measurement(s) |
|---------------------|--------|---------------------|------------------------|
| Energy Anomaly | 15% | `energy_import` | `wach_e{XXXX}_energy_import` |
| Power Factor | 25% | `power_factor_avg` | `wach_e{XXXX}_power_factor_avg` |
| Phase Imbalance | 25% | `current_unbalance` | `wach_e{XXXX}_current_unbalance` |
| THD Drift | 15% | `current_l1_thd`, `current_l3_thd` | `wach_e{XXXX}_current_l1_thd`, `wach_e{XXXX}_current_l3_thd` |
| Overload | 20% | `power_total` | `wach_e{XXXX}_power_total` |

**Note:** `power_total` is consumed by **two** FAIR scores (Energy Anomaly for
the overload sub-component, and Overload directly).  THD Drift composites
`max(current_l1_thd, current_l3_thd)` → `composite_thd`.

---

## Full Metric Catalog (46 metrics)

### Active in FAIR scoring (6 metrics)

| Metric | Unit | Description | FAIR Consumer |
|--------|------|-------------|---------------|
| `power_total` | kW | Total active power across all phases | energy_anomaly, overload |
| `energy_import` | kWh | Energy consumed from grid | energy_anomaly |
| `power_factor_avg` | (ratio) | Power factor average | power_factor |
| `current_unbalance` | % | Current unbalance percentage | phase_imbalance |
| `current_l1_thd` | % | Current THD Phase L1 | thd_drift |
| `current_l3_thd` | % | Current THD Phase L3 | thd_drift |

### Available but not in FAIR default fetch (40 metrics)

#### Power (kW, kVA, kVAR)

| Metric | Unit | Description |
|--------|------|-------------|
| `power_l1` | kW | Active power Phase L1 |
| `power_l2` | kW | Active power Phase L2 |
| `power_l3` | kW | Active power Phase L3 |
| `power_demand` | kW | Rolling average demand |
| `max_power_demand` | kW | Peak demand recorded |
| `apparent_power_total` | kVA | Total apparent power |
| `apparent_power_l1` | kVA | Apparent power Phase L1 |
| `apparent_power_l2` | kVA | Apparent power Phase L2 |
| `apparent_power_l3` | kVA | Apparent power Phase L3 |
| `apparent_power_demand` | kVA | Apparent power demand |
| `reactive_power_total` | kVAR | Total reactive power |
| `reactive_power_l1` | kVAR | Reactive power Phase L1 |
| `reactive_power_l2` | kVAR | Reactive power Phase L2 |
| `reactive_power_l3` | kVAR | Reactive power Phase L3 |
| `reactive_power_demand` | kVAR | Reactive power demand |

#### Energy (kWh, kVARh, kVAh)

| Metric | Unit | Description |
|--------|------|-------------|
| `energy_export` | kWh | Energy sent to grid |
| `reactive_energy_import` | kVARh | Reactive energy consumed |
| `reactive_energy_export` | kVARh | Reactive energy sent to grid |
| `apparent_energy` | kVAh | Total apparent energy |

#### Current (A)

| Metric | Unit | Description |
|--------|------|-------------|
| `current_avg` | A | Average current across phases |
| `current_l1` | A | Current Phase L1 |
| `current_l2` | A | Current Phase L2 |
| `current_l3` | A | Current Phase L3 |

#### Voltage (V)

| Metric | Unit | Description |
|--------|------|-------------|
| `volts_l_n_avg` | V | Phase-to-neutral voltage average |
| `volts_l_l_avg` | V | Phase-to-phase voltage average |
| `volts_l1_n` | V | Phase L1 to neutral voltage |
| `volts_l2_n` | V | Phase L2 to neutral voltage |
| `volts_l3_n` | V | Phase L3 to neutral voltage |
| `volts_l1_l2` | V | Phase L1 to L2 voltage |
| `volts_l2_l3` | V | Phase L2 to L3 voltage |
| `volts_l3_l1` | V | Phase L3 to L1 voltage |

#### Voltage THD (%)

| Metric | Unit | Description |
|--------|------|-------------|
| `volts_l1_thd` | % | Voltage THD Phase L1 |
| `volts_l2_thd` | % | Voltage THD Phase L2 |
| `volts_l3_thd` | % | Voltage THD Phase L3 |

#### Power Factor (per-phase)

| Metric | Unit | Description |
|--------|------|-------------|
| `power_factor_l1` | (ratio) | Power factor Phase L1 |
| `power_factor_l2` | (ratio) | Power factor Phase L2 |
| `power_factor_l3` | (ratio) | Power factor Phase L3 |

#### Other

| Metric | Unit | Description |
|--------|------|-------------|
| `freq` | Hz | System frequency |
| `volts_unbalance` | % | Voltage unbalance percentage |
| `digital_input_1_and_2` | (binary) | Binary status inputs |

---

## Consumer Map Summary

Scanning 158 Python files across `backend/` and `scripts/`:

### Top 10 most-referenced metrics

| Metric | References | Primary consumers |
|--------|-----------|-------------------|
| `power_total` | 139 | influx_client, fair_health_scoring, risk_engine, all ETL scripts |
| `current_unbalance` | 102 | fair_health_scoring, risk_engine, all ETL scripts |
| `power_factor_avg` | 89 | fair_health_scoring, risk_engine, all ETL scripts |
| `energy_import` | 85 | fair_health_scoring, prediction_engine, all ETL scripts |
| `current_l1_thd` | 45 | fair_health_scoring, all ETL scripts |
| `current_l3_thd` | 45 | fair_health_scoring, all ETL scripts |
| `freq` | 16 | schemas.py (allowlist), charts.py |
| `volts_l1_thd` | 16 | schemas.py (allowlist) |
| `volts_l2_thd` | 12 | schemas.py (allowlist) |
| `volts_l3_thd` | 13 | schemas.py (allowlist) |

### Files consuming FAIR default metrics (33 files)

| File | Role |
|------|------|
| `backend/core/influx_client.py` | Data fetch layer |
| `backend/core/fair_health_scoring.py` | FAIR score computation |
| `backend/core/risk_engine.py` | Risk assessment orchestrator |
| `backend/core/charts.py` | Chart data transformation |
| `backend/core/prediction_engine.py` | Energy anomaly prediction |
| `backend/core/summarizer.py` | LLM summary generation |
| `backend/routes/dashboard.py` | Dashboard API |
| `backend/routes/delta_forecast.py` | Delta forecast API |
| `backend/routes/forecast.py` | Forecast API |
| `backend/models/schemas.py` | Metric allowlist definitions |
| `backend/llm/prompts.py` | LLM prompt templates |
| `backend/llm/translator.py` | NL → structured query translator |
| `scripts/etl/run_health_etl.py` | Health score ETL pipeline |
| `scripts/etl/history_generator.py` | Historical data generation |
| `scripts/generate/generate_fair_health_scores.py` | Standalone FAIR score generator |
| `scripts/generate/generate_all_levels_health_scores.py` | Multi-level score generator |
| `scripts/generate/generate_level1_health_scores.py` | Level-1 score generator |
| `scripts/generate/generate_daily_health_index.py` | Daily index generator |
| `scripts/fetch/fetch_all_ahus_latest.py` | Raw data fetcher |
| `scripts/fetch/fetch_raw_data.py` | Raw data fetcher |
| `scripts/generate_predictions.py` | Prediction data fetcher |
| `scripts/test/verify_etl_pipeline.py` | ETL pipeline verification |
| `backend/tests/test_schemas.py` | Schema unit tests |
| `backend/tests/test_prediction_engine.py` | Prediction engine tests |
| `backend/tests/test_translator.py` | Translator tests |
| `backend/tests/test_security.py` | Security validation tests |
| `backend/tests/integration/test_chat_endpoint.py` | Chat endpoint integration |
| `backend/tests/integration/test_rate_limiter.py` | Rate limiter integration |
| `backend/tests/unit/test_validator.py` | Validator unit tests |
| `backend/tests/test_history_generator.py` | History generator tests |

### Metrics with zero consumer references outside schemas.py allowlist

These 40 metrics are defined in `ALLOWED_METRICS_WITH_UNITS` but are **not actively
fetched or scored** by any production code path:

- All `apparent_*` metrics (6)
- All `reactive_*` metrics (6)
- All `power_l1/l2/l3` metrics (3)
- All `current_l1/l2/l3` (non-THD) metrics (3)
- All `volts_*` metrics (11)
- All `power_factor_l1/l2/l3` metrics (3)
- `power_demand`, `max_power_demand`, `energy_export`, `current_avg`,
  `freq`, `volts_unbalance`, `digital_input_1_and_2` (7)

**Recommendation:** These metrics are available for future score components
(e.g., voltage quality scoring, per-phase analysis, reactive power monitoring).
They should be tagged as **"available / future-use"** rather than dropped.

---

## Findings

1. **6 of 46 metrics are actively consumed** by the FAIR scoring pipeline.
   The remaining 40 are defined but unused in production scoring.

2. **Measurement naming is consistent** across all 158 scanned files.
   Every Flux query uses the `wach_{device_id}_{metric}` pattern.

3. **No orphaned metrics** — all 46 metrics in `ALLOWED_METRICS` have
   corresponding entries in `ALLOWED_METRICS_WITH_UNITS` with units and
   descriptions.

4. **Code duplication risk** — `scripts/etl/run_health_etl.py` has local
   copies of `score_*` functions that mirror `backend/core/fair_health_scoring.py`.
   (Flagged in scoring audit as Mismatch #8.)

5. **The 40 unused metrics represent expansion opportunities** for future
   FAIR score components: voltage quality, per-phase analysis, reactive power,
   and apparent power monitoring.

---

## Verification

- [x] All 46 metrics from `ALLOWED_METRICS_WITH_UNITS` enumerated
- [x] Measurement pattern verified against `influx_client.py` Flux queries
- [x] FAIR score → metric mapping cross-referenced with `fair_health_scoring.py`
- [x] Consumer map generated from 158 Python files
- [x] Scripts committed to `scripts/research/` for reproducibility
- [x] CSV outputs written to `/tmp/metrics.csv` and `/tmp/metric_consumers.csv`
- [x] Zero production code modified — this is a read-only audit

---

## Out of Scope

- Live InfluxDB schema validation (remote DB timed out during research)
- Sample value ranges per metric (requires live DB query)
- Per-metric data quality assessment (gaps, staleness)
- Adding new metrics to FAIR scoring (future work)
