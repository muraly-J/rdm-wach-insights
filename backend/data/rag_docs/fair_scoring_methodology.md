# FAIR Health Scoring Methodology

WACH uses a proprietary scoring system called FAIR to express the electrical health of each AHU as a single number from 0 to 100. This document explains how it is calculated, what each component means, and how to interpret the results.

## What Does FAIR Stand For?

FAIR is a composite health index derived from five electrical performance indicators. The name reflects the goal: provide a Fair, Actionable, Interpretable Result for facility operators and engineers.

## The Five Component Scores

Each component is independently scored 0–100, where 100 = perfect health and 0 = severe degradation.

### 1. Energy Anomaly (weight: 15%)

Measures how much the AHU's current energy consumption deviates from its own rolling baseline. The baseline is calculated from the device's own historical patterns (same time of day, same weekday pattern).

- Score 100: energy consumption is normal, within expected range
- Score 50: energy is ~15–20% above baseline (e.g., clogged filters, fouled coil)
- Score 0: energy is severely elevated or has spiked anomalously

**Why it catches problems early**: energy anomaly often appears before PF or current imbalance degrades, because fouled coils and clogged filters increase the motor's mechanical load before it is reflected in electrical imbalance.

### 2. Power Factor Degradation (weight: 25%)

Measures how far the AHU's power factor has fallen below the target of ≥ 0.90.

- Score 100: PF ≥ 0.90
- Score 75: PF ~ 0.87 (approaching TNB penalty threshold)
- Score 50: PF ~ 0.85 (at TNB penalty threshold)
- Score 0: PF ≤ 0.70 (severe degradation, substantial TNB penalty)

Highest individual weight (25%) because poor PF has direct financial consequences via TNB penalty, and is the most actionable single-fix item (capacitor bank).

### 3. Phase Imbalance (weight: 25%)

Measures current unbalance across the three phases.

- Score 100: imbalance < 1%
- Score 75: imbalance ~ 2–3%
- Score 50: imbalance ~ 4–5% (NEMA MG1 action threshold)
- Score 0: imbalance > 10% (severe, motor damage risk)

High weight (25%) because phase imbalance directly degrades motor life and can cause thermal runaway in hospital AHUs running 24/7.

### 4. THD Drift (weight: 15%)

Measures how much the current THD has drifted upward from the device's own baseline.

- Score 100: THD-I at or below baseline (< 5%)
- Score 50: THD-I has drifted 3–5 percentage points above baseline
- Score 0: THD-I is severely elevated (> 15% or trending rapidly upward)

Lower weight (15%) because THD's direct operational impact on hospital AHUs is less immediate than PF or phase imbalance, but it is an early warning of harmonic source degradation.

### 5. Overload (weight: 20%)

Measures whether the motor is drawing current above its rated FLA.

- Score 100: current ≤ FLA × 1.00
- Score 75: current at FLA × 1.05 (5% above rated — normal service factor operation)
- Score 50: current at FLA × 1.10
- Score 0: current at FLA × 1.25 or thermal relay has tripped

Weight 20% — significant because overload leads directly to unplanned shutdown, which in ICU/OT environments is a patient safety event.

## Composite Health Index

```
health_index = (
    0.15 × energy_anomaly +
    0.25 × pf_degradation +
    0.25 × phase_imbalance +
    0.15 × thd_drift +
    0.20 × overload
)
```

Result: 0–100.

## Health Tiers

| Tier | Range | Meaning | Action |
|------|-------|---------|--------|
| Healthy | 80–100 | All indicators within normal range | Scheduled PM only |
| Monitor | 60–79 | One or more indicators showing early degradation | Investigate trend, consider early intervention |
| Maintenance | 40–59 | Clear degradation, performance impacted | Book work order within 1–2 weeks |
| Critical | 0–39 | Severe degradation, risk of failure | Immediate action required |

**Note on thresholds**: the Monitor range starts at 60, not 50. This is intentional — an AHU with a PF of 0.83 (close to TNB penalty threshold) will score in the Monitor range even if other components are healthy, prompting investigation before the penalty is incurred.

## Safety Flags

In addition to the composite score, WACH raises binary safety flags when individual components breach hard thresholds:

- `PF_CHRONIC_LOW`: PF < 0.82 sustained for > 24 hours
- `THD_CHRONIC_HIGH`: THD-I > 8% sustained for > 12 hours
- `PHASE_IMBALANCE_HIGH`: current unbalance > 5%
- `OVERLOAD_ACTIVE`: current > 110% FLA

Safety flags appear as alert badges on the dashboard and are returned in `search_docs` results. They trigger regardless of the composite score — an AHU can have a health_index of 72 (Monitor) but still carry a `PF_CHRONIC_LOW` flag.

## How to Read a Score in Practice

**health_index = 65, pf_degradation = 28**
→ Power factor is the dominant problem. The AHU is in Monitor tier. Address PF first (check capacitor bank). Other components are relatively healthy.

**health_index = 45, phase_imbalance = 30, overload = 50**
→ Maintenance tier. Phase imbalance and overload are both degraded. Check supply voltage balance, contactor contacts, and air filters immediately.

**health_index = 25, safety_flags = "PF_CHRONIC_LOW,OVERLOAD_ACTIVE"**
→ Critical. Both PF and overload are severe and have been sustained. Isolate AHU for inspection if patient safety allows. In OT or ICU: escalate to facilities engineer immediately.

## Temporal Behaviour

Scores are computed hourly by the ETL pipeline. A single bad reading does not immediately tank the score — the scoring uses a rolling window approach. However, chronic issues compound over time. An AHU that has been running at PF 0.80 for a week will have a lower accumulated penalty contribution than one that has been at 0.80 for a month.

This means: Monitor tier today → if not addressed → likely Maintenance tier within weeks for a trend issue. The dashboard's trend charts show this progression.
