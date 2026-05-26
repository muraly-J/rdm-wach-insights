# RDMI-004 — WACH Health Scoring Formula

**Date:** 2026-05-28
**Ticket:** RDMI-004
**Source:** `backend/core/fair_health_scoring.py` (1149 LOC)
**Unblocks:** RDMI-035 / Plan B T2 (WACH scoring engine port)
**Method name:** **FAIR Health Scoring — Per-AHU Baseline Method**

---

## Philosophy

Every AHU is judged entirely against **its own** personal baseline. No AHU's score is influenced by any other AHU's operating level.

A hospital AHU fleet never performs similarly. `e0101` runs at 0.67 kW with PF 0.35. `e0105` runs at 35 kW with PF 0.74. Applying the same threshold to both produces meaningless scores. The right question is not "is this AHU good or bad in absolute terms?" but "is this AHU behaving differently than it normally does?"

A z-score answers that for any AHU regardless of size, load, or PF characteristic.

---

## Top-level formula

```
health_index = clip( Σ ( weight_i × component_score_i ) × 100 , 0 , 100 )
```

Implemented at `fair_health_scoring.py:584` → `calculate_health_index(scores: dict)`.

`component_score_i ∈ [0, 1]` where **1 = healthy**, **0 = critical**.

### Component weights (must sum to 1.0)

| Component | Weight | Source |
|---|---:|---|
| `energy_anomaly` | **0.15** | `HEALTH_INDEX_WEIGHTS` (`fair_health_scoring.py:110`) |
| `power_factor` (PF degradation) | **0.25** | same |
| `phase_imbalance` | **0.25** | same |
| `thd_drift` | **0.15** | same |
| `overload` | **0.20** | same |

### Health tiers

| Range | Tier |
|---|---|
| 80 – 100 | Healthy |
| 60 – 79 | Monitor |
| 40 – 59 | Maintenance Soon |
| 0 – 39 | Critical |

Implemented at `fair_health_scoring.py:274` → `get_health_tier(index: float)`.

---

## Component score shape (shared by all 5 components)

Each component score is a weighted blend of a **LEVEL** term and a **TREND** term:

```
component_score = 1.0 − penalty

penalty = clip( LEVEL_WEIGHT × level_term + TREND_WEIGHT × trend_term , 0 , 1 )

LEVEL_WEIGHT = 0.70       # "is it bad RIGHT NOW?"
TREND_WEIGHT = 0.30       # "is it GETTING WORSE?"
```

Constants from `fair_health_scoring.py:136-137`.

### LEVEL term

```
z         = ( current_value − own_median ) / own_robust_std       # (sign convention varies, see per-component)
raw       = SENSITIVITY[component] × penalty_function(z)
level_term = sigmoid_score(raw)
```

### TREND term

```
slope_per_hour    = ols_slope(history_last_168h)
slope_normalised  = clip( slope_per_hour / own_robust_std , −10 , +10 )
trend_term        = sigmoid_score( SLOPE_SENS × max(0, ±slope_normalised) )

SLOPE_SENS = 3.0     # constant for all components
```

Slope window = **168 hours (7 days)**. If history < 168h, trend_term = 0 (level-only score).

### `sigmoid_score`

Maps any real number to `[0, 1]`, anchored so that `raw = 0 → score = 0` (no penalty).

```python
sigmoid_score(raw) = clip( sigmoid(raw) × 2 − 1 , 0 , 1 )

sigmoid(x) = 1 / (1 + exp(−x))
```

Implemented at `fair_health_scoring.py:220`.

| raw | sigmoid_score |
|---:|---:|
| 0 | 0.00 |
| 1 | 0.46 |
| 2 | 0.76 |
| 3 | 0.91 |

### Sensitivity table

| Component | `SENSITIVITY` | `fair_health_scoring.py:127` |
|---|---:|---|
| `energy_anomaly` | 2.0 | |
| `pf_degradation` | 2.5 | |
| `phase_imbalance` | 2.0 | |
| `thd_drift` | 2.0 | |
| `overload` | 2.0 | |

---

## Robust statistics

Baselines use **median + 1.4826 × MAD** (robust std), not mean + std. This is mandatory.

```python
robust_params(values):
    median = numpy.median(values)
    MAD    = numpy.median( |values − median| )
    rstd   = max( 1.4826 × MAD , MIN_RSTD[metric] )
    return median, rstd
```

Implemented at `fair_health_scoring.py:236`.

For normal distributions, `1.4826 × MAD ≈ std`. For bimodal/heavy-tailed distributions (e.g. `e0111` THD alternates 14% / 97%), robust stats correctly identify the lower mode as "normal" and treat the high mode as anomaly. Plain mean+std is useless here.

### `MIN_RSTD` (prevents division by near-zero)

| Metric | Min rstd | `fair_health_scoring.py:153` |
|---|---:|---|
| `delta_kwh` | 0.05 | |
| `power_factor_avg` | 0.008 | |
| `current_unbalance` | 0.15 | |
| `composite_thd_24h` | 0.15 | |
| `power_total` | 0.05 | |

---

## Per-component definitions

### 1 · Energy Anomaly (weight 15%) — `score_energy_anomaly`

**Input:** `delta_kwh` from prediction ETL.

```
hourly_delta(t)     = E(t) − E(t − 1h)
predicted_delta(t)  = mean( δ(t − 24h) , δ(t − 168h) , δ(t − 336h) )
delta_kwh           = energy_anomaly = hourly_delta(t) − predicted_delta(t)
```

Note: `delta_kwh` here is the **prediction residual**, not raw consumption. Loaded from DuckDB `predictions` table via `load_prediction_deltas()` (`fair_health_scoring.py:174`).

**Level term:**
```
z   = (delta_kwh − own_median_delta) / own_rstd_delta
raw = 0.6 × |z| + 0.4 × max(0, z)             # asymmetric: over-consumption penalised harder
lv  = sigmoid_score( raw × 2.0 )
```

**Trend term:** rising delta over 7 days = worsening → `max(0, slope_normalised) × 3.0` → sigmoid_score.

**Edge cases:**
- `len(hist_delta_series) < 24` → return neutral `(0.5, NaN)` (no score).
- `len(hist_delta_series) < 168` → level-only, trend_term = 0.
- `delta_kwh` is `None`/`NaN` → `(0.5, NaN)`.
- `own_median` `None`/`NaN` → `(0.5, NaN)`.

### 2 · Power Factor Degradation (weight 25%) — `score_power_factor`

**Level term:**
```
z   = (own_median_pf − current_pf) / own_rstd_pf   # positive = below own normal = bad
lv  = sigmoid_score( z × 2.5 )
```

**Trend term:** **declining** slope = bad → `max(0, −slope_normalised) × 3.0` → sigmoid_score.

**Load discount (defined but not currently applied — see Note 3):**
```
if current_power < 0.60 × own_median_power:
    score = score × 0.35
```
Constants: `PF_DISCOUNT_THRESHOLD = 0.60`, `PF_DISCOUNT_FACTOR = 0.35` (`fair_health_scoring.py:143-144`).

**Edge cases:**
- `pf` or `own_median_pf` `None`/`NaN` → `(0.5, NaN)`.
- `own_rstd_pf ≤ 0` → `(0.5, NaN)`.

### 3 · Phase Imbalance (weight 25%) — `score_phase_imbalance`

**Level term:**
```
z   = (current_unbal − own_median_unbal) / own_rstd_unbal   # positive = above own normal = bad
lv  = sigmoid_score( z × 2.0 )
```

**Trend term:** rising slope = worsening → `max(0, slope_normalised) × 3.0` → sigmoid_score.

**Edge cases:** same NaN-passthrough pattern as PF.

### 4 · THD Drift (weight 15%) — `score_thd_drift`

**Critical detail:** input is the **24-hour rolling mean** of composite THD (max of L1 and L3), **not instantaneous** values.

```python
composite_thd        = max(L1_THD, L3_THD)
thd_24h              = composite_thd.rolling(24h, min_periods=1).mean()
```

The baseline (median + rstd) must **also** be computed on the 24h-mean series. Tested: using instantaneous baseline against 24h-mean scoring inflates z by ~10× on `e0111` (false-alarm storm). Both sides of the comparison must use the same time-scale.

`THD_ROLLING_H = 24` (`fair_health_scoring.py:147`).

**Level term:**
```
z   = (thd_24h − own_median_thd) / own_rstd_thd
lv  = sigmoid_score( z × 2.0 )
```

**Trend term:** rising slope = worsening → `max(0, slope_normalised) × 3.0`.

### 5 · Overload (weight 20%) — `score_overload`

Three sub-components instead of level+trend pair:

```
# A. Ceiling proximity (50%)
power_ratio = current_power / own_p95_power
demand      = max(0, power_ratio − 0.85)
score_A     = sigmoid_score( demand × 8.0 )

# B. Z-score vs own median (30%)
z       = (current_power − own_median_power) / own_rstd_power
score_B = sigmoid_score( z × 1.5 )

# C. Trend (20%)
slope_n = clip( ols_slope(hist_power[-168h]) / own_rstd_power , −10, +10 )
score_C = sigmoid_score( max(0, slope_n) × 3.0 )       # 0 if <168h history

penalty       = 0.50 × score_A + 0.30 × score_B + 0.20 × score_C
overload_score = 1.0 − clip(penalty, 0, 1)
```

**Note:** ceiling uses **p95** (named `ahu_p95_power` in code, even though comments sometimes say "p99"). Diagnostic strings in `get_overload_signal()` also say "p95 ceiling". The variable `historical_p99` in the signal dict is a misnomer; it holds p95.

**Edge cases:**
- `len(hist_power_series) < 24` → `(0.5, NaN)`.
- `power` / `own_median` / `own_p95` `None`/`NaN`/`≤0` → `(0.5, NaN)`.
- `own_rstd_power` invalid → falls back to `MIN_RSTD["power_total"] = 0.05`.

---

## OLS slope (used by all trend terms)

Closed-form, equally-spaced points, returns slope in **metric-units per hour**:

```
β = [ n·Σ(i·y) − Σ(i)·Σ(y) ]  /  [ n·Σ(i²) − (Σ(i))² ]
```

Requires `n ≥ 3` non-NaN points, else returns 0. Implemented at `fair_health_scoring.py:255`.

---

## Static safety flags (separate engineering audit layer)

Computed from baseline medians. **They do NOT enter the health index** — they appear as metadata in the assessment payload.

Implemented at `fair_health_scoring.py:682` → `compute_safety_flags()`.

| Flag | Condition |
|---|---|
| `THD_CHRONIC_HIGH` | `median(thd_24h) > 5.0%` |
| `IMBALANCE_SEVERE` | `median(unbalance) > 5.0%` |
| `PF_CHRONIC_LOW` | `median(pf) < 0.85` |
| `OVERLOAD_CHRONIC` | `median(power) / p95(power) > 0.90` |

---

## Inputs required per AHU

The scoring engine requires the following per-AHU time series (one row per hour):

| Column | Used in | Notes |
|---|---|---|
| `device_id` | grouping | `e\d{4}` |
| `timestamp` | ordering | hourly UTC |
| `power_total` | overload, PF load-discount | kW |
| `power_factor_avg` | PF | |
| `current_unbalance` | imbalance | percent |
| `composite_thd` | THD (computed → 24h mean) | percent |
| `delta_kwh` | energy anomaly | from prediction ETL; falls back to `E(t) − E(t−1h)` |

**Trend windows:**
- `TREND_WINDOW_H = 168` hours (7 days) — used for slope computation.
- THD rolling mean: 24 hours.
- Minimum history for any score: 24 hours (else `0.5` neutral).
- Minimum for trend term: 168 hours (else `level-only`).

---

## Output schema per AHU

(See `fair_health_scoring.py:912` for the full dict literal.)

```jsonc
{
  "device_id": "e0101",
  "timestamp": "2026-02-23T14:00:00+08:00",
  "level": "Level 1",
  "health_index": 84.0,
  "health_tier": "Healthy",
  "risk_scores": {
    "energy_anomaly": 0.92,                               // bare float
    "power_factor":   { "score": 0.88, "severity": "Normal", ... },
    "phase_imbalance":{ "score": 0.81, "severity": "Normal", ... },
    "thd_drift":      { "score": 0.74, "severity": "Monitor", ... },
    "overload":       { "score": 0.86, "severity": "Normal", ... }
  },
  "data_quality": { ... },
  "power_total": 5.2,
  "power_factor": 0.93,
  "unbalance_pct": 2.1,
  "thd_24h": 4.3,
  "delta_kwh": 0.05,
  "safety_flags": "THD_CHRONIC_HIGH,PF_CHRONIC_LOW",
  // diagnostic z-scores (not used in computation, surfaced for chat/explain)
  "z_energy": 0.2, "z_pf": 0.4, "z_imbalance": -0.1, "z_thd": 1.2, "z_overload": 0.3
}
```

**Severity mapping** (from each component score, not the index) — `fair_health_scoring.py:1012`:

| Score range | Severity |
|---|---|
| ≤ 0.2 | Critical |
| ≤ 0.4 | Attention Required |
| ≤ 0.6 | Monitor |
| > 0.6 | Normal |

---

## Notes & caveats discovered during extraction

1. **THD baseline must use 24h-mean series.** Comments in source mark this explicitly. Tested failure mode = z ≈ 10 permanently on `e0111` if violated.
2. **Asymmetric energy penalty.** Energy_anomaly uses `0.6·|z| + 0.4·max(0,z)`. Over-consumption is penalised more than under-consumption. No other component does this; PF/imbalance/THD/overload use symmetric `|z|` (via direct sigmoid on signed z with sign convention setting which direction is "bad").
3. **PF load discount is defined but not wired.** The constants `PF_DISCOUNT_THRESHOLD = 0.60` / `PF_DISCOUNT_FACTOR = 0.35` exist (`fair_health_scoring.py:143`) and the docstring of `score_power_factor` references the discount, but the actual code path does **not** apply it — function signature accepts `power` but never uses it. Two options when porting:
   - **Strict port**: replicate the bug. Document it. Defer fix.
   - **Faithful port**: implement the load discount per docstring. Confirm with Raj which is the source of truth.
   Recommend: strict port for MVP demo parity, then file a follow-up to implement properly.
4. **`p95` vs `p99` naming inconsistency.** Code uses p95, some comments/signal strings say p99. Use p95 in port; rename signal strings during port.
5. **Slope direction conventions** differ per component:
   - energy/imbalance/THD/overload: rising slope = worsening → `max(0, slope_normalised)`.
   - PF: falling slope = worsening → `max(0, −slope_normalised)`.
6. **Fallback values are NOT silent.** When inputs are NaN/missing, score returns `0.5` (neutral) and `z_diagnostic = NaN`. This is correct behaviour; do not "fix" by zeroing.
7. **`load_prediction_deltas` does a sys.path insert.** The DuckDB lookup path has a `sys.path.insert(0, os.path.dirname(...))` hack (`fair_health_scoring.py:194`). Drop this in the port — RDM Insight uses proper package imports.
8. **`generate_fleet_risk_assessment_fair` is the orchestrator.** This is the end-to-end function the dashboard route calls. Port it as the adapter method `WachAdapter.compute_fleet_assessment(level, time_range)`.

---

## Port acceptance checks (for Plan B T2)

The scoring port is correct when, given identical inputs (same DataFrames passed in), it produces:

1. **Bit-equal `health_index`** to within ±0.1 vs WACH reference for every AHU at every hour in a 7-day sample. Test fixture: copy a 7-day slice of `data/healthdb.duckdb` and freeze the expected output.
2. **Same tier label** for every AHU.
3. **Same `safety_flags` set** (order-independent).
4. **Same z-diagnostics** to within ±0.01.
5. **CI guard passes**: no `TODO`, `placeholder`, or `raise NotImplementedError` in `sites/wach/scoring.py` (Plan B T2 step 7).

---

## File map (Plan B T2 port target)

| WACH source | RDM Insight target | Type |
|---|---|---|
| `core/fair_health_scoring.py` | `apps/api/sites/wach/scoring.py` | LIFT verbatim |
| `core/score_normalize.py` | `apps/api/core/scoring/normalize.py` | promote to core (cross-site) |
| `compute_predictions_async` from `core/prediction_engine.py` | `apps/api/sites/wach/prediction.py` | LIFT (only piece needed by scoring) |
| Constants `HEALTH_INDEX_WEIGHTS`, `HEALTH_TIERS`, `SENSITIVITY`, `MIN_RSTD`, etc. | top of `sites/wach/scoring.py` | inline |

---

## Verification

- [x] All 5 component formulas extracted with code references.
- [x] Top-level weighted-sum formula documented.
- [x] Robust-statistics method documented.
- [x] Edge cases enumerated for each component.
- [x] Caveats and known inconsistencies flagged for porter.
- [x] Acceptance check defined for Plan B T2 CI.

## Next

- RDMI-035 / Plan B T2 unblocked. Porter can paste algorithm into `sites/wach/scoring.py` without re-deriving.
- Open question for Raj before Sprint 4: confirm "PF load discount" intent — strict-port (bug) or faithful-port (docstring)?
