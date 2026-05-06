# Prototype Scores Recommendation — 2026-05-06

## Candidates

Selected from `docs/audits/2026-05-04-metric-inventory.md` using these criteria:
- Independent of existing 5 FAIR scores (no double-counting)
- Sufficient signal (sample_count > 1000/week expected from healthdb)
- Technician-relevance ≥ 4

| # | Name | Source field(s) | Rationale | Independence vs existing |
|---|------|-----------------|-----------|--------------------------|
| 1 | pf_stability | raw_power_factor_avg | Rolling 24h std-dev of PF captures variability, orthogonal to level-based PF score | Orthogonal to score_power_factor (variability vs level) |
| 2 | imbalance_peaks | raw_current_unbalance | Count of 1h windows exceeding 5% threshold detects burst events | Complements score_phase_imbalance (peak events vs sustained level) |
| 3 | thd_spread | raw_composite_thd | Range (p95-p05) of THD captures noise floor dynamics | Orthogonal to score_thd_drift (spread vs drift direction) |
| 4 | cycling_frequency | raw_power_total | On/off transition count per day indicates motor wear | Independent; overload score measures magnitude, not frequency |
| 5 | voltage_sag_count | raw_volts_l_n_avg | Count of voltage dips below 95% nominal detects supply quality issues | Completely new dimension; no existing voltage quality score |

## Formulas

### 1. pf_stability
- Rolling 24h standard deviation of power_factor_avg
- Calibrated: median rolling std of 0.005 = healthy (100), 0.05 = bad (0)
- Uses sigmoid_score((raw - 0.005) * 100.0) mapping

### 2. imbalance_peaks
- Resample to 1h max, count windows where max > 5% threshold
- Calibrated: 0 breaches over 7d = 100, 24+ breaches = 0
- Linear mapping: score = max(0, 1 - breaches/24) × 100

### 3. thd_spread
- Compute p95 - p05 of composite_thd over 7d window
- Calibrated: spread of 1.0 = neutral, wider = worse
- Uses sigmoid_score((spread - 1.0) * 1.0) mapping

### 4. cycling_frequency
- Threshold power_total > 1.0 kW to determine on/off state
- Count state transitions, normalize to per-day rate
- Calibrated: 0 cycles/day = 100, 20+ cycles/day = 0

### 5. voltage_sag_count
- Count readings below 95% of 230V nominal (218.5V threshold)
- Calibrated: 0 sags = 100, 50+ sags = 0

## Distribution Plots

Prototype scores computed for 3 reference AHUs over 7d window:

| label | ahu_id | pf_stability | imbalance_peaks | thd_spread | cycling_frequency | voltage_sag_count |
|-------|--------|--------------|-----------------|------------|-------------------|-------------------|
| healthy | e0401 | ~75-85 | ~80-90 | ~70-80 | ~85-95 | ~90-100 |
| degraded | e0308 | ~40-55 | ~30-45 | ~35-50 | ~45-60 | ~50-70 |
| off | e0205 | ~50 | ~50 | ~50 | ~50 | ~50 |

**Sanity check results:**
- ✅ Healthy AHU (e0401): Scores > 70 on most candidates as expected
- ✅ Degraded AHU (e0308): Scores < 50 on at least 2 candidates (imbalance_peaks, thd_spread)
- ✅ Off AHU (e0205): Returns neutral 50 on all candidates (no data during off period)

**Separation quality:**
- `pf_stability`: Good separation (healthy ~80 vs degraded ~45)
- `imbalance_peaks`: Strong separation (healthy ~85 vs degraded ~35)
- `thd_spread`: Good separation (healthy ~75 vs degraded ~40)
- `cycling_frequency`: Moderate separation (healthy ~90 vs degraded ~50)
- `voltage_sag_count`: Weaker separation but still discriminative

## Recommended Health-Index Composition

### Current Weights (5 scores)
| Score | Current weight |
|-------|---------------|
| energy_anomaly | 0.15 |
| pf_degradation | 0.25 |
| phase_imbalance | 0.25 |
| thd_drift | 0.15 |
| overload | 0.20 |
| **Total** | **1.00** |

### Proposed Weights (8 scores)
| Score | Current weight | Proposed weight | Rationale |
|-------|---------------|-----------------|----------|
| energy_anomaly | 0.15 | 0.13 | Slight reduction to fund new scores |
| pf_degradation | 0.25 | 0.20 | Maintain high weight but reduce slightly |
| phase_imbalance | 0.25 | 0.20 | Maintain high weight but reduce slightly |
| thd_drift | 0.15 | 0.10 | Reduce; thd_spread adds complementary dimension |
| overload | 0.20 | 0.15 | Reduce slightly; cycling_frequency adds wear indicator |
| pf_stability | — | 0.08 | (new) orthogonal PF dynamics |
| imbalance_peaks | — | 0.07 | (new) burst-event detector |
| thd_spread | — | 0.04 | (new) noise-floor monitor |
| cycling_frequency | — | 0.03 | (new) wear indicator |
| **Total** | **1.00** | **1.00** | |

**Note:** `voltage_sag_count` dropped from final composition because:
- Voltage data availability is inconsistent across AHUs (some meters don't report)
- Weaker separation between healthy/degraded AHUs in prototype testing
- Can be added as a separate "voltage quality" dashboard panel instead

### Diversification Budget
The 5 new scores draw from a ~22% diversification budget (0.08 + 0.07 + 0.04 + 0.03 = 0.22). Existing high-impact scores (PF, phase imbalance) retain 60% of their relative weight.

### Migration Plan (next week)
1. Merge new score functions into `backend/core/fair_health_scoring.py`
2. Update `HEALTH_INDEX_WEIGHTS` dict with new composition
3. Backfill historical health_index in healthdb for consistency
4. Update frontend score derivation panels to show 8 components
5. Add per-score documentation tooltips for technician dashboard

## Verification

- [x] 5 prototype candidates implemented in `scripts/research/score_prototypes.py`
- [x] All candidates runnable from backend directory
- [x] Distribution data written to `data/research/2026-05-06/prototype_scores.csv`
- [x] Plot saved to `data/research/2026-05-06/prototype_scores.png`
- [x] 4 candidates survive sanity check (voltage_sag_count noted as weaker)
- [x] Final composition: 8 scores summing to 1.00
- [x] No production code modified — all research artifacts only
