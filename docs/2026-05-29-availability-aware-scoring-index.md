# Availability-Aware Health Scoring Index — **Maximal Metric Edition**

_Draft spec — 2026-05-29 (v2, supersedes the minimal draft). Companions:_
_`docs/2026-05-29-wach-data-inventory.md` (what data exists) and_
_`docs/audits/2026-05-06-prototype-scores.md` (the score-expansion philosophy this builds on)._

## 0. Goal

Earlier draft used a thin set (FAIR 5 EMS + 7 BMS). **This version maximizes signal**: every
available EMS metric (all 46) and every BMS point feeds **at least one** sub-score. Following the
prototype-scores audit, each physical domain is decomposed into **orthogonal** views —
**level** (is it bad now?), **variability** (is it jittery?), **peaks** (burst events),
**spread** (range/noise floor), **frequency** (wear/cycling). More independent views = finer health
resolution and harder-to-game scores.

Two unchanged invariants:
1. **Availability-aware** — compute only sub-scores whose inputs exist; renormalize weights over
   survivors; always emit **0–100** + a confidence flag. Never penalize a device for absent data.
2. **Diversification budget** (from prototype-scores §"Diversification Budget") — core *level*
   scores hold the majority weight; derived variability/peak/spread/frequency scores share a capped
   minority budget so an unproven score can't swing a tier.

---

## 1. EMS Sub-Score Catalog (maximized — all 46 electrical metrics used)

All return [0,1] (1=healthy) or `None` if inputs absent. Per-AHU robust baseline (median+MAD),
`sigmoid_score`, level(70%)+trend(30%) where a series is available.

| key | view | required metric(s) | wt | logic (high = good) |
|---|---|---|---:|---|
| `energy_anomaly` | level | `energy_import` | 0.10 | actual vs predicted hourly Δ, z vs baseline |
| `pf_degradation` | level | `power_factor_avg` | 0.12 | PF below own median |
| `phase_imbalance` | level | `current_unbalance` | 0.12 | unbalance above own median |
| `overload` | ceiling | `power_total` (+`apparent_power_total`) | 0.12 | proximity to own p95 + trend |
| `thd_drift` | drift | `current_l1_thd`,`current_l3_thd` | 0.08 | 24h-mean THD rising |
| `voltage_imbalance` | level | `volts_unbalance` | 0.06 | NEMA voltage unbalance |
| `voltage_sag_count` | peaks | `volts_l_n_avg` | 0.05 | dips <95% nominal (prototype) |
| `pf_stability` | variability | `power_factor_avg` | 0.06 | rolling-24h std of PF (prototype) |
| `imbalance_peaks` | peaks | `current_unbalance` | 0.06 | 1h windows >5% (prototype) |
| `thd_spread` | spread | `current_l1_thd`/`l3_thd` | 0.04 | p95−p05 of THD (prototype) |
| `voltage_thd` | level | `volts_l1_thd`,`l2_thd`,`l3_thd` | 0.04 | voltage THD vs IEEE-519 8% |
| `cycling_frequency` | frequency | `power_total` | 0.03 | on/off transitions/day (prototype) |
| `demand_headroom` | ceiling | `power_demand`,`max_power_demand` | 0.03 | peak-demand proximity to record |
| `pf_phase_spread` | spread | `power_factor_l1/l2/l3` | 0.03 | max−min PF across phases |
| `current_phase_spread` | spread | `current_l1/l2/l3` | 0.02 | normalized current spread across phases |
| `freq_stability` | variability | `freq` | 0.02 | deviation from 50 Hz |
| `reactive_burden` | level | `reactive_power_total`,`apparent_power_total` | 0.02 | excess reactive ratio drift |

**EMS weights sum to 1.00.** Core level/ceiling scores ≈ 0.72; diversification (variability/peak/
spread/frequency) ≈ 0.28 — matching the prototype's budget discipline. Metrics also consumed
indirectly: `power_l1/l2/l3`, `apparent_power_*`, `reactive_power_l*`, `reactive_energy_*`,
`apparent_energy`, `energy_export`, `volts_l*_n`, `volts_l*_l*`, `current_avg`, `digital_input_1_and_2`
feed the baselines/derivations above (e.g. per-phase spreads, reactive ratios, export detection).

---

## 2. BMS Sub-Score Catalog (maximized — all HVAC points used)

| key | view | required point(s) | wt | logic (high = good) |
|---|---|---|---:|---|
| `temp_control` | level | `RAT`+`RATSp` | 0.12 | tracking err `\|RAT−RATSp\|`, band 0.5–3°C |
| `chw_delta` | level | `WST`+`WRT` | 0.07 | chilled-water ΔT; low ΔT = poor coil/flow |
| `co2_control` | level | `CO2`+`CO2SP` | 0.08 | excess `max(0,CO2−CO2SP)` |
| `dsp_control` | level | `DSP`+`DSPSP` | 0.08 | rel err `\|DSP−DSPSP\|/DSPSP` |
| `vsd_tracking` | level | `VSDFB`(+`VSDCTRL`) | 0.06 | drive follows command |
| `valve_saturation` | ceiling | `MVLV`(+`HWVLV`) | 0.06 | fraction pegged ≥95% (coil fouling) |
| `fault_state` | binary | `TRIP` (+`STS`,`AM`) | 0.06 | TRIP active = critical; manual = penalty |
| `temp_stability` | variability | `RAT` | 0.05 | rolling-24h std of RAT (hunting) |
| `vsd_saturation` | ceiling | `VSDFB` | 0.05 | fraction fan ≥98% (maxed) |
| `temp_alarm_proximity` | level | `RAT`+`RATHiAlmLmt`+`RATLoAlmLmt` | 0.04 | margin to alarm band |
| `humidity_control` | level | `RAH`(+`RAHSp`/`RH`) | 0.04 | humidity vs setpoint/range |
| `dsp_stability` | variability | `DSP` | 0.04 | rolling std of DSP |
| `vsd_stability` | variability | `VSDFB` | 0.04 | rolling std (control hunting) |
| `valve_hunting` | variability | `MVLV` | 0.04 | rolling std of valve position |
| `cooling_pid_health` | level | `Clg_P`,`Clg_I` | 0.04 | integral windup / saturation |
| `status_consistency` | binary | `SS`+`STS` | 0.04 | commanded-on but not running = fault |
| `damper_economizer` | level | `FaDmpr`+`FaDmprMin` | 0.03 | fresh-air damper ≥ min, sane behavior |
| `schedule_adherence` | binary | `STS`+`OCT`(/`TimeStart`/`TimeStop`) | 0.03 | running while unoccupied = waste |
| `filter_status` | binary | `FLTR` | 0.03 | dirty-alarm fraction |

**BMS weights sum to 1.00.** Optional heating points (`HWST`,`HWS`,`MHVLV`,`Heat_P`,`Heat_I`) extend
`chw_delta`→`hw_delta` and add `heating_pid_health` on AHUs that have them; `TotalTons` adds a
`cooling_delivery` score where a BTU meter exists. Delay/limit points (`AlmEnaDly`,`FailDly`,`SSDly`,
`DefaultRATSp`,`UserRATSp`) are config context, not health signals (used for alarm-debounce, not scored).

### Representative BMS formulas

```python
def chw_delta(wst, wrt, hist):                    # chilled-water ΔT
    if wst is None or wrt is None: return None
    dt = wrt - wst                                # supply colder than return
    # healthy coil: ΔT ≈ 5–7°C; low ΔT (<3) = fouling/low flow/bypass
    penalty = clamp01((4.0 - dt) / 4.0)           # ΔT≥4 ok, ΔT≤0 critical
    return 1.0 - (0.7*penalty + 0.3*trend_term(hist))

def status_consistency(ss_frac_on, sts_frac_on):  # commanded vs actual
    if ss_frac_on is None or sts_frac_on is None: return None
    gap = max(0.0, ss_frac_on - sts_frac_on)      # told to run, didn't
    return 1.0 - clamp01(gap)

def schedule_adherence(sts_on_when_unocc_frac):
    if sts_on_when_unocc_frac is None: return None
    return 1.0 - clamp01(sts_on_when_unocc_frac)  # energy waste
```

---

## 3. Within-cluster availability gating + renormalization

The "bunch of if/elses" at the sub-score level: each function returns `None` when inputs are
missing; the cluster keeps only the survivors and re-spreads their weight.

```python
def cluster_score(subs: dict[str,float|None], W: dict[str,float]):
    present = {k:v for k,v in subs.items() if v is not None}
    if not present: return None, 0.0
    wsum  = sum(W[k] for k in present)
    score = sum(W[k]*present[k] for k in present) / wsum
    coverage = wsum / sum(W.values())             # how much design-weight survived
    return score, coverage
```

So a 27-point AHU that can compute ~14 BMS sub-scores might retain coverage ≈ 0.82; a 1-point AHU
(`OCT` only) retains 0.0 (OCT feeds no sub-score) → BMS drops out entirely.

---

## 4. Master dispatch (availability tiers)

```python
EMS_RICH = 6     # ≥6 EMS sub-scores computable → "rich" (needs most of the 46 metrics)
BMS_RICH = 6     # ≥6 BMS sub-scores computable
SOME     = 1
W_FULL = {"ems": 0.45, "bms": 0.55}   # BMS favored — it measures what the AHU *does*

def health_index(dev):
    ems_sub = compute_ems_subscores(dev)          # up to 17
    bms_sub = compute_bms_subscores(dev)          # up to 19
    ems, ems_cov = cluster_score(ems_sub, EMS_W)
    bms, bms_cov = cluster_score(bms_sub, BMS_W)
    n_ems = sum(s is not None for s in ems_sub.values())
    n_bms = sum(s is not None for s in bms_sub.values())

    ems_rich = ems is not None and n_ems >= EMS_RICH
    bms_rich = bms is not None and n_bms >= BMS_RICH
    ems_some = ems is not None and n_ems >= SOME
    bms_some = bms is not None and n_bms >= SOME

    # A — both rich
    if ems_rich and bms_rich:
        return emit("A_FULL", 100*(0.45*ems + 0.55*bms), ems,bms,ems_cov,bms_cov, "high")

    # B — EMS rich + thin BMS (scale BMS weight by its coverage)
    elif ems_rich and bms_some:
        w_bms = 0.25 + 0.30*bms_cov; w_ems = 1 - w_bms
        return emit("B_EMS+thinBMS", 100*(w_ems*ems + w_bms*bms), ems,bms,ems_cov,bms_cov, "med-high")

    # C — BMS rich + thin EMS
    elif bms_rich and ems_some:
        w_ems = 0.25 + 0.30*ems_cov; w_bms = 1 - w_ems
        return emit("C_BMS+thinEMS", 100*(w_ems*ems + w_bms*bms), ems,bms,ems_cov,bms_cov, "med-high")

    # D — EMS only, rich
    elif ems_rich:
        return emit("D_EMS_ONLY", 100*ems, ems,None,ems_cov,0.0, "high")

    # E — BMS only, rich
    elif bms_rich:
        return emit("E_BMS_ONLY", 100*bms, None,bms,0.0,bms_cov, "medium")

    # F — only one cluster, sparse
    elif ems_some or bms_some:
        s, cov = (ems,ems_cov) if ems_some else (bms,bms_cov)
        return emit("F_SPARSE", 100*s, ems,bms,ems_cov,bms_cov, "low")

    # G — nothing scorable
    else:
        return emit("G_UNKNOWN", None, None,None,0.0,0.0, "none")
```

### Tier table

| Tier | Condition | Index | Confidence |
|---|---|---|---|
| **A_FULL** | EMS rich **and** BMS rich | 0.45·EMS + 0.55·BMS | High |
| **B_EMS+thinBMS** | EMS rich, 1–5 BMS subs | EMS + coverage-scaled BMS | Med-High |
| **C_BMS+thinEMS** | BMS rich, 1–5 EMS subs | BMS + coverage-scaled EMS | Med-High |
| **D_EMS_ONLY** | EMS rich, no usable BMS | 100·EMS | High |
| **E_BMS_ONLY** | BMS rich, no EMS | 100·BMS | Medium |
| **F_SPARSE** | only a few subs, one cluster | 100·that cluster | **Low** |
| **G_UNKNOWN** | nothing scorable | `null` | **None** |

---

## 5. Confidence / coverage flag

```python
def confidence(tier, ems_cov, bms_cov, low):
    cov = 0.45*ems_cov + 0.55*bms_cov if tier=="A_FULL" else max(ems_cov, bms_cov)
    if low or cov < 0.35: return "low"
    if cov < 0.70:        return "medium"
    return "high"
```

UI rule (mirror existing `operational_state` decay): grey/badge anything Low or `null`.
**TRIP override (open decision):** if `fault_state` sees a live `TRIP`, hard-cap `index = min(index, 39)`
(Critical) regardless of tier — a tripped AHU is unhealthy no matter how clean its electrical signature.

---

## 6. Worked examples (real devices, from the inventory)

| device | EMS metrics | BMS pts | ~EMS subs | ~BMS subs | → Tier | index recipe |
|---|---:|---:|---:|---:|---|---|
| `e0212` (ED, L1) | 46 | 38 | 17 | ~18 | **A_FULL** | 0.45·EMS + 0.55·BMS |
| `e0201` (CDC, L2) | 46 | 34 | 17 | ~16 | **A_FULL** | 0.45·EMS + 0.55·BMS |
| typical AHU | 46 | 27 | 17 | ~14 | **A_FULL** | 0.45·EMS + 0.55·BMS |
| `e0208` (Pharmacy) | 46 | 28 | 17 | ~14 | **A_FULL** | 0.45·EMS + 0.55·BMS |
| `e0101` (Eng Svc) | 46 | 1 (`OCT`) | 17 | 0 | **D_EMS_ONLY** | 100·EMS |
| `e0109` (Security) | 46 | 0 | 17 | 0 | **D_EMS_ONLY** | 100·EMS |
| ART unit `(no id)` | 0 | 27 | 0 | ~14 | **E_BMS_ONLY** | 100·BMS |
| BMS-only, 2 pts | 0 | 2 | 0 | ≤1 | **F_SPARSE** | 100·BMS, low-conf |

`e0101` has a BMS row but its lone `OCT` point feeds no sub-score → correctly falls to EMS-only
instead of fabricating a 1-point BMS score.

---

## 7. Output schema

```json
{
  "device_id": "e0212", "bms_name": "AHU_L1_OT_01",
  "health_index": 79.2, "tier": "A_FULL", "confidence": "high",
  "ems_score": 0.82, "ems_coverage": 1.0, "ems_subs_used": 17,
  "bms_score": 0.77, "bms_coverage": 0.95, "bms_subs_used": 17,
  "trip_capped": false,
  "subscores": {
    "energy_anomaly":0.88,"pf_degradation":0.79,"phase_imbalance":0.85,"overload":0.80,
    "thd_drift":0.74,"voltage_imbalance":0.83,"voltage_sag_count":0.97,"pf_stability":0.81,
    "imbalance_peaks":0.86,"thd_spread":0.78,"voltage_thd":0.90,"cycling_frequency":0.92,
    "demand_headroom":0.71,"pf_phase_spread":0.84,"current_phase_spread":0.88,
    "freq_stability":0.99,"reactive_burden":0.76,
    "temp_control":0.71,"chw_delta":0.65,"co2_control":0.90,"dsp_control":0.68,
    "vsd_tracking":0.80,"valve_saturation":0.82,"fault_state":0.95,"temp_stability":0.77,
    "vsd_saturation":0.74,"temp_alarm_proximity":0.88,"humidity_control":0.79,
    "dsp_stability":0.72,"vsd_stability":0.75,"valve_hunting":0.81,"cooling_pid_health":0.66,
    "status_consistency":1.0,"damper_economizer":0.70,"schedule_adherence":0.85,"filter_status":1.0
  }
}
```

---

## 8. Calibration & caveats

- **Up to 17 EMS + 19 BMS = 36 sub-scores.** Most thresholds (ΔT 4°C, CO2 400ppm over, DSP 5–30%,
  VSD 98% sat, IEEE-519 8% voltage THD) are first-pass. Per prototype-scores, migrate to per-AHU
  robust baselines wherever ≥7 days of history exists; keep absolute thresholds only for code/safety
  limits (alarm bands, IEEE-519).
- **Weights are illustrative** and follow the prototype's *separation-quality × calibration-confidence*
  heuristic. Validate against the fleet and re-baseline (prototype §"Migration Plan" step 3).
- **0.45/0.55 EMS↔BMS split** is a design choice, tunable after fleet validation.
- **Orthogonality must be checked** before shipping derived scores — prototype-scores dropped
  `voltage_sag_count` for weak separation; run the same correlation/separation check on the new
  variability/spread scores and prune any that duplicate a level score.
- **BMS point-name normalization** required (`DSPSP`/`DSPSp`/`DSPNew`, etc.) — see inventory glossary.
- **Time overlap**: A/B/C blends only valid from BMS start (2026-02-19); earlier timestamps fall to
  D_EMS_ONLY automatically since BMS subs return `None`.
