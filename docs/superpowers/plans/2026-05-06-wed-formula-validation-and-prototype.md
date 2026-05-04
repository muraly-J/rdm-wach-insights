# Wed — Formula Validation + Prototype New Scores Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AM — produce a written validation report that documents every active FAIR-style score formula, recomputes each on a 1-week historical sample for 3 reference AHUs, and flags drift or edge-case bugs. PM — prototype 3–5 new candidate scores driven by Tue's metric inventory and recommend a new health-index composition (7–9 blended scores) with weights. **No production code shipped today.**

**Architecture:** Pure research day. AM is a recompute harness in a notebook-style script that pulls historical data via `backend/core/influx_client.py`, recomputes scores using the existing functions in `backend/core/fair_health_scoring.py`, and diffs against stored values from `backend/core/healthdb.py`. PM extends the same harness with new candidate score formulas, runs them on the same sample, and produces distribution plots + a weighting recommendation.

**Tech Stack:** Python 3.11, pandas, numpy, matplotlib (for distribution plots), InfluxDB Python client, the project's existing `score_*` functions reused as-is.

**Inputs (must exist before starting):**
- `docs/audits/2026-05-04-scoring-audit.md` (Mon)
- `docs/audits/2026-05-04-metric-inventory.md` (Tue) — specifically the `promote` and `?` tagged rows
- Tue PM canonical converter `backend/core/score_normalize.py` (used for plotting on a unified 0–100 axis)

**Important factual correction surfaced during exploration:**
The week plan calls these "the 4 FAIR formulas." `backend/core/fair_health_scoring.py` actually defines **5** scores: `score_energy_anomaly`, `score_power_factor`, `score_phase_imbalance`, `score_thd_drift`, `score_overload`. Plan validates all 5. Note this discrepancy in the report's intro.

---

## File Structure

**Created today:**
- `scripts/research/recompute_scores.py` — AM harness: load 1-week sample, recompute 5 scores, diff vs stored
- `scripts/research/score_prototypes.py` — PM harness: 3–5 new candidate scores + weighting recommendation
- `docs/audits/2026-05-04-formula-validation.md` — AM report
- `docs/audits/2026-05-04-prototype-scores.md` — PM recommendation
- `data/research/2026-05-06/` — output directory for plots and CSV diffs (NOT committed to git; add to `.gitignore` if not already)

**Read-only:**
- `backend/core/fair_health_scoring.py`
- `backend/core/influx_client.py`
- `backend/core/healthdb.py`
- `docs/audits/2026-05-04-metric-inventory.md`

---

### Task 1: Pick 3 reference AHUs (healthy / degraded / off)

**Files:**
- Create: `data/research/2026-05-06/reference_ahus.json`

- [ ] **Step 1: Ensure output directory exists**

```bash
mkdir -p data/research/2026-05-06
```

- [ ] **Step 2: Query healthdb for 3 candidates**

Run a one-shot query against the production health DB. From repo root:

```bash
python - <<'PY'
import json
from backend.core import db_reader

# Pull recent health_index per AHU; pick representatives.
rows = db_reader.get_health_index_series(level=None, device_id=None, time_range="7d")
latest = {}
for entry in rows:
    aid = entry["ahu_id"]
    cur = entry["scores"]["health_index"]["current"]
    latest[aid] = cur

healthy = max(latest.items(), key=lambda kv: kv[1])
degraded = min(
    [kv for kv in latest.items() if kv[1] is not None and kv[1] > 20],
    key=lambda kv: kv[1],
)
# "off" = AHU with operational_state == off in last 24h; fall back to lowest health_index
off_candidate = min(latest.items(), key=lambda kv: kv[1])

print(json.dumps({
    "healthy": {"ahu_id": healthy[0], "health_index": healthy[1]},
    "degraded": {"ahu_id": degraded[0], "health_index": degraded[1]},
    "off": {"ahu_id": off_candidate[0], "health_index": off_candidate[1]},
}, indent=2))
PY
```

- [ ] **Step 3: Sanity-check the off-state pick**

For the `off` candidate, confirm operational state actually went off in the last 7 days. Run:

```bash
python - <<'PY'
from backend.core import healthdb
state = healthdb.get_operational_state("<off_ahu_id_from_step_2>", lookback_hours=168)
print(state)
PY
```

If no off transition found, swap the `off` candidate manually (use a level-7 AHU or any with sparse data — tag this choice in the JSON).

- [ ] **Step 4: Write `reference_ahus.json`**

Create `data/research/2026-05-06/reference_ahus.json`:

```json
{
  "healthy": {"ahu_id": "<id>", "rationale": "highest health_index over 7d window"},
  "degraded": {"ahu_id": "<id>", "rationale": "lowest non-off health_index over 7d"},
  "off": {"ahu_id": "<id>", "rationale": "operational_state went off in last 168h"}
}
```

- [ ] **Step 5: Commit (file is small + reference; commit despite output dir)**

```bash
git add -f data/research/2026-05-06/reference_ahus.json
git commit -m "chore(research): pin 3 reference AHUs for Wed formula validation"
```

(`-f` in case `data/` is gitignored. If commit blocked, instead place the file at `docs/audits/2026-05-06-reference-ahus.json` and update Task 2 path.)

---

### Task 2: Build the recompute harness

**Files:**
- Create: `scripts/research/recompute_scores.py`

- [ ] **Step 1: Write harness skeleton**

Create `scripts/research/recompute_scores.py`:

```python
"""Recompute FAIR-style scores from raw InfluxDB data and diff against stored values.

Run: python -m scripts.research.recompute_scores
Output: data/research/2026-05-06/recompute_diffs.csv + per-AHU plots.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from backend.core import db_reader, influx_client
from backend.core.fair_health_scoring import (
    build_baselines,
    calculate_health_index,
    score_energy_anomaly,
    score_overload,
    score_phase_imbalance,
    score_power_factor,
    score_thd_drift,
)

REF_PATH = Path("data/research/2026-05-06/reference_ahus.json")
OUT_DIR = Path("data/research/2026-05-06")
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOOKBACK = "7d"


def load_reference() -> dict:
    return json.loads(REF_PATH.read_text())


def fetch_raw(ahu_id: str) -> pd.DataFrame:
    """Pull raw fields needed by all 5 score functions for one AHU over LOOKBACK."""
    fields = [
        "delta_kwh",
        "power_factor_avg",
        "current_unbalance",
        "thd_24h",
        "power_total",
    ]
    frames = []
    for f in fields:
        df = influx_client.fetch_time_series(
            device_ids=[ahu_id], metric=f, time_range=LOOKBACK
        )
        if df is None or df.empty:
            continue
        df = df.rename(columns={"_value": f}).set_index("_time")[[f]]
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, axis=1).sort_index()
    return out


def recompute_for(ahu_id: str) -> pd.DataFrame:
    raw = fetch_raw(ahu_id)
    if raw.empty:
        return pd.DataFrame()

    baselines = build_baselines(raw.assign(ahu_id=ahu_id).reset_index())
    base = baselines.get(ahu_id, {})

    rows = []
    for ts, r in raw.iterrows():
        energy_s, _ = score_energy_anomaly(
            r.get("delta_kwh"),
            base.get("delta_kwh_median", np.nan),
            base.get("delta_kwh_rstd", np.nan),
            raw["delta_kwh"].dropna().to_numpy() if "delta_kwh" in raw else np.array([]),
        )
        pf_s, _ = score_power_factor(
            r.get("power_factor_avg"),
            r.get("power_total"),
            base.get("power_factor_avg_median", np.nan),
            base.get("power_factor_avg_rstd", np.nan),
            raw["power_factor_avg"].dropna().to_numpy() if "power_factor_avg" in raw else np.array([]),
        )
        unbal_s, _ = score_phase_imbalance(
            r.get("current_unbalance"),
            base.get("current_unbalance_median", np.nan),
            base.get("current_unbalance_rstd", np.nan),
            raw["current_unbalance"].dropna().to_numpy() if "current_unbalance" in raw else np.array([]),
        )
        thd_s, _ = score_thd_drift(
            r.get("thd_24h"),
            base.get("thd_24h_median", np.nan),
            base.get("thd_24h_rstd", np.nan),
            raw["thd_24h"].dropna().to_numpy() if "thd_24h" in raw else np.array([]),
        )
        ovl_s, _ = score_overload(
            r.get("power_total"),
            base.get("power_total_median", np.nan),
            base.get("power_total_rstd", np.nan),
            base.get("power_total_p95", np.nan),
            raw["power_total"].dropna().to_numpy() if "power_total" in raw else np.array([]),
        )
        scores = {
            "energy_anomaly": energy_s,
            "pf_degradation": pf_s,
            "phase_imbalance": unbal_s,
            "thd_drift": thd_s,
            "overload": ovl_s,
        }
        idx = calculate_health_index(scores)
        rows.append({"timestamp": ts, "ahu_id": ahu_id, **scores, "health_index_recomputed": idx})

    return pd.DataFrame(rows)


def fetch_stored(ahu_id: str) -> pd.DataFrame:
    """Pull stored health_index series from healthdb for the same AHU + window."""
    series = db_reader.get_health_index_series(
        level=None, device_id=ahu_id, time_range=LOOKBACK
    )
    if not series:
        return pd.DataFrame()
    rows = []
    for entry in series:
        if entry["ahu_id"] != ahu_id:
            continue
        for ts, v in entry["scores"]["health_index"].get("series", []):
            rows.append({"timestamp": ts, "health_index_stored": v})
    return pd.DataFrame(rows)


def main() -> int:
    ref = load_reference()
    all_diffs = []
    for label, info in ref.items():
        ahu = info["ahu_id"]
        recomputed = recompute_for(ahu)
        stored = fetch_stored(ahu)
        if recomputed.empty:
            print(f"[{label}] {ahu}: no raw data; skipping")
            continue
        merged = recomputed.merge(stored, on="timestamp", how="outer")
        merged["label"] = label
        merged["diff"] = merged["health_index_recomputed"] - merged["health_index_stored"]
        all_diffs.append(merged)

    if not all_diffs:
        print("No data to write.")
        return 1

    df = pd.concat(all_diffs, ignore_index=True)
    out = OUT_DIR / "recompute_diffs.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {out} ({len(df)} rows)")
    print(df.groupby("label")["diff"].describe())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Sanity-check field names against `influx_client.py`**

Open `backend/core/influx_client.py`. Confirm `fetch_time_series` signature accepts `device_ids`, `metric`, `time_range` (line 71). If field names differ (e.g. `pf_avg` vs `power_factor_avg`), update the `fields` list in the harness to match what InfluxDB actually has. Cross-reference with Tue's `docs/audits/2026-05-04-metric-inventory.md`.

- [ ] **Step 3: Run the harness**

```bash
python -m scripts.research.recompute_scores
```

Expected: `Wrote data/research/2026-05-06/recompute_diffs.csv (<n> rows)` and a describe block. If a `KeyError` on baseline keys appears, inspect `build_baselines()` return shape and adjust the `base.get(...)` keys.

- [ ] **Step 4: Commit harness (do NOT commit CSV output)**

```bash
git add scripts/research/recompute_scores.py
git commit -m "chore(research): add FAIR score recompute + diff harness"
```

---

### Task 3: Document each formula in plain English

**Files:**
- Create: `docs/audits/2026-05-04-formula-validation.md`

- [ ] **Step 1: Write doc skeleton**

Create `docs/audits/2026-05-04-formula-validation.md`:

```markdown
# FAIR Formula Validation Report — 2026-05-06

> **Note:** Week plan refers to "4 FAIR formulas." The codebase defines **5** scores in `backend/core/fair_health_scoring.py`. This report covers all 5.

## Reference AHUs

See `data/research/2026-05-06/reference_ahus.json`.

| Label | AHU ID | Rationale |
|-------|--------|-----------|
| healthy | <id> | <rationale> |
| degraded | <id> | <rationale> |
| off | <id> | <rationale> |

## Score Catalog

For each score: name, weight in health_index, inputs, formula in plain English, edge cases observed.

### 1. Energy Anomaly (`score_energy_anomaly`, weight 15%)
- **Input fields:** `delta_kwh`, plus per-AHU baseline (`delta_kwh_median`, `delta_kwh_rstd`) and 168h history.
- **Level term (70%):** z = (delta_kwh − median) / rstd; raw = 0.6·|z| + 0.4·max(0, z); sigmoid scaled.
- **Trend term (30%):** OLS slope of 168h history, normalized by rstd, sigmoid scaled.
- **Returns:** 1 − clamp01(0.7·level + 0.3·trend), 0–1, high=good.
- **Min history:** 24h returns neutral 0.5; <168h zeros the trend term.

### 2. Power-Factor Degradation (`score_power_factor`, weight 25%)
(...)

### 3. Phase Imbalance (`score_phase_imbalance`, weight 25%)
(...)

### 4. THD Drift (`score_thd_drift`, weight 15%)
(...)

### 5. Overload (`score_overload`, weight 20%)
- A. Ceiling (50%): max(0, power/p95 − 0.85), sigmoid×8.
- B. Z-score (30%): (power − median)/rstd, sigmoid×1.5.
- C. Trend (20%): rising-load slope sigmoid.
- Returns 1 − clamp01(0.5A + 0.3B + 0.2C).

## Composite

`calculate_health_index(scores)` = clip(Σ weight · score × 100, 0, 100).
Weights live in `HEALTH_INDEX_WEIGHTS` constant (capture exact dict in this section).

## Recompute vs Stored — Per-AHU Diff Stats

(Filled in Task 4.)

## Edge Cases & Bugs Found

(Filled in Task 5.)

## Recommendation

(Filled in Task 5.)
```

- [ ] **Step 2: Fill scores 2, 3, 4 by reading source**

Open `backend/core/fair_health_scoring.py` lines 358 (PF), 412 (phase imbalance), 456 (THD). Translate each docstring + body into the same pattern shown for scores 1 and 5. Capture the actual `HEALTH_INDEX_WEIGHTS` dict literal in the Composite section.

- [ ] **Step 3: Commit**

```bash
git add docs/audits/2026-05-04-formula-validation.md
git commit -m "docs(audit): document all 5 FAIR-style score formulas"
```

---

### Task 4: Fill the diff statistics

**Files:**
- Modify: `docs/audits/2026-05-04-formula-validation.md`

- [ ] **Step 1: Compute summary stats from `recompute_diffs.csv`**

```bash
python - <<'PY'
import pandas as pd
df = pd.read_csv("data/research/2026-05-06/recompute_diffs.csv")
print("Per-label diff stats (recomputed - stored, in 0-100 health_index units):")
print(df.groupby("label")["diff"].describe().to_markdown())
print()
print("Per-label NaN counts:")
print(df.groupby("label")[["health_index_recomputed", "health_index_stored", "diff"]].apply(lambda g: g.isna().sum()).to_markdown())
PY
```

- [ ] **Step 2: Paste output into the "Recompute vs Stored" section**

Format as two markdown tables: one for diff stats, one for NaN counts. Include written commentary: "Healthy AHU diff median X, IQR Y; degraded median Z" etc.

- [ ] **Step 3: Decide pass/fail per AHU**

For each label, mark:
- **Pass** if |median diff| < 2 (on 0–100) AND IQR < 5
- **Drift** if |median diff| ≥ 2 OR IQR ≥ 5 — write a hypothesis (baseline computed differently? rolling vs snapshot?)
- **Bug** if NaN ratio differs by >10pp between recomputed and stored

- [ ] **Step 4: Commit**

```bash
git add docs/audits/2026-05-04-formula-validation.md
git commit -m "docs(audit): record recompute-vs-stored diff statistics"
```

---

### Task 5: Catalog edge cases and bugs

**Files:**
- Modify: `docs/audits/2026-05-04-formula-validation.md`

- [ ] **Step 1: Run targeted edge-case probes**

For each edge case below, write a small script snippet, run it, paste the result into the "Edge Cases & Bugs Found" section:

a. **Div-by-zero**: confirm every score returns 0.5 when `rstd <= 0`. Verify by passing `ahu_rstd_*=0.0` to each `score_*` and observing return.
b. **Missing metric**: pass `value=None` and `value=float('nan')`. Confirm 0.5 + nan z-diagnostic.
c. **Off state**: query a known off-window from the `off` reference AHU. Check whether stored `health_index` is calculated, null, or frozen via confidence decay (commit `7b444fd`). Compare with recompute behavior.
d. **Low confidence**: simulate by passing only 12h of history to `score_energy_anomaly` and `score_overload`. Confirm 0.5 returned (min_history_hours guard).

```bash
python - <<'PY'
import numpy as np
from backend.core.fair_health_scoring import (
    score_energy_anomaly, score_power_factor, score_phase_imbalance,
    score_thd_drift, score_overload,
)

# (a) rstd=0
print("rstd=0 energy:", score_energy_anomaly(1.0, 0.0, 0.0, np.ones(48)))
print("rstd=0 pf:", score_power_factor(0.95, 1000, 0.92, 0.0, np.full(48, 0.92)))
# (b) None
print("None energy:", score_energy_anomaly(None, 0.0, 0.05, np.ones(48)))
# (d) <24h history
print("12h energy:", score_energy_anomaly(1.0, 0.0, 0.05, np.ones(12)))
print("12h overload:", score_overload(100, 50, 0.05, 60, np.ones(12)))
PY
```

- [ ] **Step 2: Write findings**

Per edge case, write a bullet:
- **(a) rstd=0**: behaves correctly — returns 0.5. ✅
- **(b) None/NaN**: ✅ returns 0.5 except `<exception>` in `<func>` if any.
- **(c) off-state**: stored value = X, recomputed = Y, gap reason = Z. May need `operational_state` gate at recompute time.
- **(d) low-confidence**: ✅ neutral 0.5 returned for `<24h.

Mark each as ✅ pass / ⚠️ documented behavior / 🐛 bug. Bugs become entries in the "Recommendation" section with file:line.

- [ ] **Step 3: Write the AM recommendation**

In the "Recommendation" section list:
- **Bugs to fix** (with severity high/medium/low) → these become next-week tickets, not this week's work.
- **Documented quirks to keep** (e.g. neutral 0.5 fallback is intentional).
- **Validation verdict per score**: pass / drift / bug.

- [ ] **Step 4: Commit**

```bash
git add docs/audits/2026-05-04-formula-validation.md
git commit -m "docs(audit): catalog FAIR score edge cases + AM recommendation"
```

---

### Task 6: AM verification gate

- [ ] **Step 1: Confirm all 5 scores covered**

Run `grep -c '^### [0-9]' docs/audits/2026-05-04-formula-validation.md`. Expected: 5.

- [ ] **Step 2: Confirm 3 reference AHUs in diff table**

Run `grep -c '^| healthy\|^| degraded\|^| off' docs/audits/2026-05-04-formula-validation.md`. Expected: ≥ 3.

- [ ] **Step 3: Confirm bugs (if any) have file:line citations**

Eyeball the "Bugs to fix" list — each item must include `backend/core/fair_health_scoring.py:<line>`.

---

### Task 7: PM — pick 3–5 prototype candidates from inventory

**Files:**
- Read: `docs/audits/2026-05-04-metric-inventory.md`
- Create: `docs/audits/2026-05-04-prototype-scores.md` (skeleton)

- [ ] **Step 1: Pull `promote` and `?` rows from inventory**

```bash
grep -E 'promote|\| \? \|' docs/audits/2026-05-04-metric-inventory.md
```

- [ ] **Step 2: Pick 3–5 candidates**

Selection rule:
- Prefer fields independent of existing 5 scores (no double-counting).
- Prefer fields with sample_count > 1000/week (sufficient signal).
- Prefer technician-relevance ≥ 4.

Likely candidates (final picks driven by inventory):
1. **PF stability** — std-dev of `power_factor_avg` over rolling 24h (separate from level-based PF score)
2. **Current imbalance peaks** — max `current_unbalance` over rolling 1h, count of breaches
3. **THD spectral spread** — if individual harmonic fields exist, ratio of dominant harmonic to total
4. **Runtime / cycling frequency** — derived from `power_total` thresholding (count on/off transitions per day)
5. **Voltage sag count** — count of `voltage_*` dips below 95% of nominal in 24h

Document chosen candidates + rationale in `docs/audits/2026-05-04-prototype-scores.md`:

```markdown
# Prototype Scores Recommendation — 2026-05-06

## Candidates

| # | Name | Source field(s) | Rationale | Independence vs existing |
|---|------|-----------------|-----------|--------------------------|
| 1 | pf_stability | power_factor_avg | (...) | orthogonal to score_power_factor (level vs variability) |
| 2 | imbalance_peaks | current_unbalance | (...) | (...) |
...

## Formulas

(Filled in Task 8.)

## Distribution Plots

(Filled in Task 8.)

## Recommended Health-Index Composition

(Filled in Task 9.)
```

- [ ] **Step 3: Commit**

```bash
git add docs/audits/2026-05-04-prototype-scores.md
git commit -m "docs(research): pick prototype score candidates from metric inventory"
```

---

### Task 8: Implement candidates and run on sample

**Files:**
- Create: `scripts/research/score_prototypes.py`

- [ ] **Step 1: Write prototype harness**

Create `scripts/research/score_prototypes.py`:

```python
"""Prototype 3-5 new candidate scores. Reuse Wed AM data fetch. Plot distributions.

Run: python -m scripts.research.score_prototypes
Output: data/research/2026-05-06/prototype_scores.csv + PNG plots.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from backend.core import influx_client
from backend.core.fair_health_scoring import sigmoid_score
from backend.core.score_normalize import to_canonical

REF_PATH = Path("data/research/2026-05-06/reference_ahus.json")
OUT_DIR = Path("data/research/2026-05-06")
LOOKBACK = "7d"


def fetch(ahu_id: str, field: str) -> pd.Series:
    df = influx_client.fetch_time_series(device_ids=[ahu_id], metric=field, time_range=LOOKBACK)
    if df is None or df.empty:
        return pd.Series(dtype=float)
    return df.set_index("_time")["_value"].astype(float).sort_index()


# ─── Candidate score formulas ───────────────────────────────────────────────

def pf_stability(pf_series: pd.Series) -> float:
    """Lower rolling std = more stable = healthier. Returns 0-100 high=good."""
    if pf_series.empty:
        return 50.0
    rolling = pf_series.rolling("24h").std().dropna()
    if rolling.empty:
        return 50.0
    raw = float(rolling.median())
    # Calibrate: median rolling std of 0.005 = healthy, 0.05 = bad.
    score_0_1 = 1.0 - sigmoid_score((raw - 0.005) * 100.0)
    return to_canonical(score_0_1, scale="0-1", direction="high-good")


def imbalance_peaks(unbal_series: pd.Series, threshold: float = 5.0) -> float:
    """Count of 1h windows exceeding threshold. More breaches = worse."""
    if unbal_series.empty:
        return 50.0
    hourly_max = unbal_series.resample("1h").max().dropna()
    if hourly_max.empty:
        return 50.0
    breaches = int((hourly_max > threshold).sum())
    # Calibrate: 0 breaches = 100, 24+ breaches over 7d = 0.
    score_0_1 = max(0.0, 1.0 - breaches / 24.0)
    return to_canonical(score_0_1, scale="0-1", direction="high-good")


def thd_spread(thd_series: pd.Series) -> float:
    """Range (p95 - p05) of THD. Wider range = noisier = worse."""
    if thd_series.empty:
        return 50.0
    p95 = float(thd_series.quantile(0.95))
    p05 = float(thd_series.quantile(0.05))
    spread = p95 - p05
    score_0_1 = 1.0 - sigmoid_score((spread - 1.0) * 1.0)
    return to_canonical(score_0_1, scale="0-1", direction="high-good")


def cycling_frequency(power_series: pd.Series, on_threshold_kw: float = 1.0) -> float:
    """Excessive on/off cycling = motor wear. Returns 0-100 high=good."""
    if power_series.empty:
        return 50.0
    on = power_series > on_threshold_kw
    transitions = int((on.astype(int).diff().abs() == 1).sum())
    cycles_per_day = transitions / 7.0
    # Calibrate: 0 cycles = 100, 20+/day = 0.
    score_0_1 = max(0.0, 1.0 - cycles_per_day / 20.0)
    return to_canonical(score_0_1, scale="0-1", direction="high-good")


def voltage_sag_count(voltage_series: pd.Series, nominal: float = 230.0) -> float:
    """Count of dips below 95% nominal in 24h windows."""
    if voltage_series.empty:
        return 50.0
    sags = (voltage_series < 0.95 * nominal).sum()
    score_0_1 = max(0.0, 1.0 - sags / 50.0)
    return to_canonical(score_0_1, scale="0-1", direction="high-good")


CANDIDATES = {
    "pf_stability": ("power_factor_avg", pf_stability),
    "imbalance_peaks": ("current_unbalance", imbalance_peaks),
    "thd_spread": ("thd_24h", thd_spread),
    "cycling_frequency": ("power_total", cycling_frequency),
    "voltage_sag_count": ("voltage_avg", voltage_sag_count),
}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ref = json.loads(REF_PATH.read_text())

    rows = []
    for label, info in ref.items():
        ahu = info["ahu_id"]
        record = {"label": label, "ahu_id": ahu}
        for name, (field, fn) in CANDIDATES.items():
            series = fetch(ahu, field)
            record[name] = fn(series)
        rows.append(record)

    df = pd.DataFrame(rows)
    csv_path = OUT_DIR / "prototype_scores.csv"
    df.to_csv(csv_path, index=False)
    print(df.to_markdown(index=False))

    # Distribution plots
    fig, axes = plt.subplots(1, len(CANDIDATES), figsize=(4 * len(CANDIDATES), 4))
    for ax, name in zip(axes, CANDIDATES, strict=True):
        ax.bar(df["label"], df[name])
        ax.set_title(name)
        ax.set_ylim(0, 100)
        ax.axhline(50, color="grey", linestyle="--")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "prototype_scores.png", dpi=120)
    print(f"Wrote {csv_path} + plot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Replace candidate names if Task 7 picks differ**

If the inventory drove a different candidate set, edit the `CANDIDATES` dict. Keep exactly 3–5 entries. Update calibration constants based on inventory `sample_min`/`sample_max` columns.

- [ ] **Step 3: Run prototype script**

```bash
python -m scripts.research.score_prototypes
```

Expected: a markdown table printed and `data/research/2026-05-06/prototype_scores.png` written. If a candidate consistently returns 50.0, the source field is empty for the reference AHUs — pick a different candidate or different reference AHU.

- [ ] **Step 4: Paste table + plot reference into prototype doc**

Add to `docs/audits/2026-05-04-prototype-scores.md` under "Distribution Plots":

```markdown
## Distribution Plots

![Prototype scores by reference AHU](../../data/research/2026-05-06/prototype_scores.png)

| label | ahu_id | pf_stability | imbalance_peaks | thd_spread | cycling_frequency | voltage_sag_count |
|-------|--------|--------------|-----------------|------------|-------------------|-------------------|
| (paste from Step 3) |
```

- [ ] **Step 5: Sanity-check separation**

Verify: healthy AHU > 70 on most candidates; degraded < 50 on at least 2; off shows neutral 50 (no data) on most. If a candidate gives no separation between healthy and degraded, mark it "weak — drop" in the report.

- [ ] **Step 6: Commit script + updated doc**

```bash
git add scripts/research/score_prototypes.py docs/audits/2026-05-04-prototype-scores.md
git commit -m "feat(research): prototype 3-5 candidate scores with distribution sanity check"
```

---

### Task 9: Recommend new health-index composition

**Files:**
- Modify: `docs/audits/2026-05-04-prototype-scores.md`

- [ ] **Step 1: Decide which prototypes survive**

From Task 8 Step 5 sanity check, drop weak candidates. Surviving set + 5 existing scores = total. Target 7–9 total. If you end at 6 or 10, justify in writing.

- [ ] **Step 2: Propose weights**

Write a weight table. Constraints: weights sum to 1.0; existing high-impact scores keep their relative weight (PF and phase imbalance already at 25% each, energy/THD at 15%, overload at 20%); new scores draw from a small "diversification budget" (~20–30%).

```markdown
## Recommended Health-Index Composition

| Score | Current weight | Proposed weight | Rationale |
|-------|----------------|-----------------|-----------|
| energy_anomaly | 0.15 | 0.12 | (small reduction to fund new scores) |
| pf_degradation | 0.25 | 0.20 | (...) |
| phase_imbalance | 0.25 | 0.20 | (...) |
| thd_drift | 0.15 | 0.10 | (...) |
| overload | 0.20 | 0.15 | (...) |
| pf_stability | — | 0.08 | (new) orthogonal PF dynamics |
| imbalance_peaks | — | 0.07 | (new) burst-event detector |
| thd_spread | — | 0.04 | (new) noise-floor monitor |
| cycling_frequency | — | 0.04 | (new) wear indicator |
| **Total** | 1.00 | 1.00 | |
```

- [ ] **Step 3: Provide migration note**

Write a paragraph: "Ship sequence next week — (1) merge new score functions into `fair_health_scoring.py`, (2) update `HEALTH_INDEX_WEIGHTS`, (3) backfill historical health_index in `healthdb`, (4) update frontend score derivation panels."

- [ ] **Step 4: Commit**

```bash
git add docs/audits/2026-05-04-prototype-scores.md
git commit -m "docs(research): recommend expanded 7-9 score health-index composition"
```

---

### Task 10: End-of-day verification

- [ ] **Step 1: Confirm both reports exist and are committed**

```bash
git log --oneline --since="2026-05-06 00:00" -- docs/audits/2026-05-04-formula-validation.md docs/audits/2026-05-04-prototype-scores.md
```
Expected: at least one commit per file.

- [ ] **Step 2: Confirm prototype script reproducible**

```bash
python -m scripts.research.score_prototypes
```
Expected: prints a table without error.

- [ ] **Step 3: Confirm no production code changed**

```bash
git diff --name-only main..HEAD | grep -v -E '^docs/|^scripts/research/|^data/research/' || echo "OK: only research artifacts changed"
```
Expected: `OK: only research artifacts changed` OR empty (if working on `main`).

- [ ] **Step 4: Push**

```bash
git push origin main
```

---

## Verification (end of Wed)

- [ ] All 5 actual FAIR-style scores documented in plain English with weights and edge-case bullets in `docs/audits/2026-05-04-formula-validation.md`.
- [ ] Recompute-vs-stored diff stats present for 3 reference AHUs (healthy / degraded / off).
- [ ] Edge-case probe results (rstd=0, None/NaN, off-state, low-confidence) recorded with ✅/⚠️/🐛 tags.
- [ ] Bugs (if any) cite `backend/core/fair_health_scoring.py:<line>` and are queued for next-week tickets.
- [ ] 3–5 prototype score candidates implemented in `scripts/research/score_prototypes.py`, runnable, with distribution data in `prototype_scores.csv` + PNG.
- [ ] `docs/audits/2026-05-04-prototype-scores.md` includes weight-sum-to-1.0 recommendation for a 7–9 score composite.
- [ ] **No edits to `backend/core/fair_health_scoring.py` formulas, no edits to `HEALTH_INDEX_WEIGHTS` constant, no production-code shipped today.**

---

## Risks

- **Baseline shape mismatch in harness**: `build_baselines()` may expect a different DataFrame schema than `fetch_raw()` produces. Symptom: `KeyError` on `base.get(...)`. Fix by reading the function body around line 595 and reshaping input.
- **InfluxDB field-name drift between Tue inventory and harness**: if the inventory revealed unexpected names (e.g. `pf_avg` not `power_factor_avg`), update `fields` in `recompute_scores.py` and `CANDIDATES` source-field column in `score_prototypes.py` together.
- **Off-state AHU has no raw data → harness emits empty diffs**: use a degraded-with-gaps AHU instead, OR widen `LOOKBACK` to `30d` to capture an off-window with surrounding data.
- **Weak prototype separation**: if 2+ candidates fail the sanity check, do NOT pad the recommendation to hit 7–9; ship 6 with a written note. Forced diversification is worse than honest scope.
- **Time pressure on PM half**: if AM validation overruns past lunch, cut prototype set to the 3 strongest candidates and skip Task 9's migration paragraph until Friday QA day.
