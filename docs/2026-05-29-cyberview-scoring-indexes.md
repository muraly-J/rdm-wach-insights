# Cyberview Scoring Indexes — assuming historical data access

_Draft — 2026-05-29. Companions: `scripts/research/cyberview_health_index_design.md` (the_
_current **live-only** design), `docs/superpowers/specs/2026-05-28-cyberview-mqtt-adr.md` (topic/metric_
_schema), `docs/2026-05-29-availability-aware-scoring-index.md` (the WACH availability framework this mirrors)._

> Premise: Cyberview ops grants the historian DB behind their Grafana/Laravel stack (ADR outcome **A**).
> Today the broker is **live-only** — 56 retained config flags, zero usable time series. Everything below
> is contingent on that backfill landing.

---

## 1. Minimum historical window

Cyberview publishes at **~30 s native cadence** (change-of-value for digital, periodic for analog). So
sample *count* is never the constraint — even 24 h ≈ 2,880 samples/topic. The real driver is **how many
operational cycles** the window captures, plus the lag structure of the history-dependent scores.

| Window | What it unlocks | Why this length | Verdict |
|---|---|---|---|
| **72 h** (3 d) | crude per-device median; short OLS trend | enough to seed a robust median+MAD and a 3-day slope | floor only — **not** production |
| **7 d** (168 h) | trend terms on every analog score; one full daily/occupancy cycle | matches the FAIR 7-day trend window; existing design's "calibrate after 7 d" | **provisional** index OK |
| **14 d** (336 h) | energy/efficiency anomaly vs own baseline; two weekend cycles | the WACH energy model averages lags at t−24h, t−168h, **t−336h** → 14 d is the hard floor for that style | **minimum viable** for the full index |
| **30 d** | stable robust baselines (MAD converges), real cycling EWMA, kW/TR efficiency baseline across a load range | the live design already *assumes* a 30-day cycling EWMA — 30 d makes the design self-consistent | **recommended for production** |
| **90 d – 12 mo** | P2 energy optimization (load × weather regression), P3 ML predictive maintenance, seasonal/monsoon normalization | regression + ML need load variety across weather; tropical seasonality is mild but monsoon/dry still shifts load | required for P2/P3 |

**Bottom line:** **14 days is the hard minimum** to stand up the full health index (it's the energy-anomaly
lag floor); **30 days is the recommended launch baseline** (and is what the existing cycling-EWMA design
already presumes). Anything below 7 days = level-only scoring with neutral trends — usable for a demo, not
for maintenance decisions. P2/P3 need **≥90 days, ideally a year**.

Caveat specific to Cyberview: because publishing is **change-of-value**, a quiet topic is *held*, not
missing — backfill must forward-fill last-known value, and window depth is measured in **wall-clock**, not
message count.

---

## 2. What history changes vs the live-only design

The current design leans on **absolute piecewise thresholds** (e.g. "1°C over setpoint = 80 pts") because it
has no per-device baseline. History lets Cyberview adopt the WACH **FAIR** method:

| Live-only (today) | History-enabled (this draft) |
|---|---|
| Absolute thresholds per metric | **Per-device robust baseline** (median + 1.4826·MAD); score = deviation in own σ |
| Rolling std over last 5 polls (~2.5 min) | **24 h rolling** variability vs own 30-day baseline |
| Cycling baseline = hard-coded default 4 | **Real per-device EWMA** of starts/day over 30 d |
| No drift detection | **7-day OLS trend term** (30%) on every analog score — "getting worse?" |
| No efficiency tracking | **kW/TR drift**, coil-ΔT degradation over weeks (history-only) |
| No load normalization | Baselines conditioned on hour-of-day / occupancy / load bin |

Same score *names* as the live design — the math underneath gets the level(70%)+trend(30%) + robust-baseline
treatment, exactly like WACH `fair_health_scoring.py`.

---

## 3. Cyberview sub-score catalog (availability-aware, history-upgraded)

Cyberview has **no power-meter telemetry per AHU** (no PF/THD/V-A unbalance — see live design §8), so its two
clusters differ from WACH. `[HIST]` = newly enabled or materially upgraded by history.

### 3A. Process cluster — per AHU / FCU (the primary unit)

| key | view | required topics | wt | logic (high = good) |
|---|---|---|---:|---|
| `thermal_control` | level | `Temperature_Return_Air`+`Valve_Temperature_Setpoint` | 0.16 | RAT vs setpoint, **z vs own baseline** [HIST] |
| `thermal_trend` | trend | RAT history | 0.04 | [HIST] sustained drift off setpoint over 7 d |
| `hydronic_dT` | level | `CHWS_Temperature`+`CHWR_Temperature` | 0.14 | coil ΔT (5–7°C ideal); **baseline-relative** [HIST] |
| `hydronic_dT_drift` | trend | ΔT history | 0.05 | [HIST] coil fouling = ΔT falling over weeks |
| `air_path` | level | `VSD_Feedback`+`VSD_Command`+`Pressure_Supply_Air`(±SP) | 0.12 | VSD tracking + DSP band fit |
| `vsd_hunting` | variability | `VSD_Feedback` | 0.05 | [HIST] 24 h std vs own baseline (control instability) |
| `valve_tracking` | level | `Valve_Command_Position`+`Valve_Feedback` | 0.10 | command vs feedback error |
| `valve_saturation` | ceiling | `Valve_Command`+RAT err | 0.05 | pegged-open but not cooling (sustained) |
| `control_mode` | binary | `Operation_Mode`/`AOM_Status` | 0.06 | [HIST] manual-override **duration** (needs history) |
| `reliability` | binary | `Status_Trip`,`Filter_Alarm`,`Status_Start-Stop` | 0.10 | trips + filter + **cycling vs 30 d EWMA** [HIST] |
| `data_integrity` | meta | all sensors | 0.07 | freshness + bounds + unit-drift (→ confidence) |

### 3B. Plant / Electrical cluster — plant headers, pumps, switchboards

These attach to plant/LV-room devices, **not** individual AHUs. History is what makes the efficiency scores possible at all.

| key | applies to | required topics | wt | logic |
|---|---|---|---:|---|
| `plant_kw_per_tr` | BTU header | `Power_Active`+`Cooling_Output` | 0.45 | [HIST] kW/TR drift up = chiller/plant degradation |
| `plant_dT` | BTU header | `CHWS`/`CHWR` | 0.25 | header ΔT band-fit |
| `plant_load_factor` | BTU header | `Cooling_Output` | 0.15 | vs nameplate, **baseline-normalized** [HIST] |
| `plant_data_health` | BTU header | all | 0.15 | freshness + sanity |
| `pump_dp_track` | CHWP | `Pressure_Differential`+`VSD_Pressure_Setpoint` | 0.30 | dp vs setpoint |
| `pump_vsd_track` | CHWP | `VSD_Feedback`+`VSD_Command` | 0.25 | drive tracking |
| `pump_cavitation` | CHWP | `Pressure_Suction` | 0.15 | low suction while running |
| `pump_dead_head` | CHWP | `VSD_Feedback`+`Pressure_Differential` | 0.15 | running but no flow |
| `pump_reliability` | CHWP | `Status_Trip`,`Status_Duty_VSD` | 0.15 | [HIST] trip history + duty consistency |
| `msb_events` | MSB/EMSB/DB | `*_Status_Trip`,`Earth_Fault`,`Overcurrent` | n/a | **event-driven**, not a continuous gauge |

---

## 4. Availability tiers (the if/else dispatch)

Cyberview routes on **device class × sensor coverage**, not EMS/BMS like WACH. Each cluster renormalizes
weights over available sub-scores (identical `cluster_score()` helper from the WACH doc §3).

```python
PROC_RICH = 5    # ≥5 process sub-scores computable
def cyberview_index(dev):
    proc, proc_cov = cluster_score(process_subs(dev), PROC_W)
    n_proc = count_present(process_subs(dev))
    has_hydro = dev.has("CHWS_Temperature","CHWR_Temperature")

    # ── CV-A — full AHU: thermal + hydronic + air + valve ───────────────
    if dev.klass in ("AHU","AHU-GF") and n_proc >= PROC_RICH and has_hydro:
        return emit("CV-A_AHU_FULL", 100*proc, proc_cov, "high")

    # ── CV-B — AHU without hydronic sensors (air-side only) ──────────────
    elif dev.klass in ("AHU","AHU-GF") and n_proc >= 3:
        return emit("CV-B_AHU_AIRSIDE", 100*proc, proc_cov, "medium")

    # ── CV-C — FCU / minimal (temp + status only) ───────────────────────
    elif dev.klass == "FCU" or n_proc in (1,2):
        return emit("CV-C_FCU_THIN", 100*proc, proc_cov, "low")

    # ── CV-D — BTU/plant header → plant efficiency index ────────────────
    elif dev.klass == "PLANT":
        plant,_ = cluster_score(plant_subs(dev), PLANT_W)
        return emit("CV-D_PLANT", 100*plant, ..., "high")   # needs ≥30d for kW/TR

    # ── CV-E — CHW pump → pump index ────────────────────────────────────
    elif dev.klass == "CHWP":
        pump,_ = cluster_score(pump_subs(dev), PUMP_W)
        return emit("CV-E_PUMP", 100*pump, ..., "high")

    # ── CV-F — switchboard → event index (alert feed, not gauge) ────────
    elif dev.klass in ("MSB","EMSB","DB"):
        return emit("CV-F_SWITCHBOARD", msb_event_score(dev), ..., "event")

    # ── CV-G — nothing scorable / data stale ────────────────────────────
    else:
        return emit("CV-G_GREY", None, 0.0, "none")
```

### Tier table

| Tier | Device class + coverage | Index | Confidence |
|---|---|---|---|
| **CV-A_AHU_FULL** | AHU with thermal+hydronic+air+valve | 100·process (geometric mean, §6) | High |
| **CV-B_AHU_AIRSIDE** | AHU, no CHW sensors (air-side only) | 100·process (hydro dropped, renormalized) | Medium |
| **CV-C_FCU_THIN** | FCU / only temp+status | 100·process (1–2 subs) | **Low** |
| **CV-D_PLANT** | BTU/plant header | 100·plant (kW/TR needs ≥30 d) | High* |
| **CV-E_PUMP** | CHW pump | 100·pump | High |
| **CV-F_SWITCHBOARD** | MSB/EMSB/DB | event score (0/50/100 on trip count) | Event-only |
| **CV-G_GREY** | nothing scorable / `data_integrity`<0.4 | `null` | None |

\*CV-D is "high" only once ≥30 days of history exist; below that the efficiency scores fall back to band-fit.

---

## 5. Scores that **only** exist with history (the payoff)

These are impossible in the live-only design — they're the reason to chase the backfill:

1. **`hydronic_dT_drift`** — coil fouling shows as ΔT slowly falling over weeks. Needs ≥14 d, clearer at 30 d.
2. **`plant_kw_per_tr` trend** — the single highest-value efficiency signal; chiller/plant degradation. ≥30 d.
3. **Real cycling baseline** — starts/day vs per-device 30-day EWMA (live design hard-codes a default of 4).
4. **`control_mode` duration** — "manual override >24 h" requires remembering when manual started.
5. **Baseline-relative everything** — every analog score becomes a robust z vs the device's own normal,
   replacing one-size-fits-all thresholds (the same fairness win WACH got from FAIR).
6. **Anomaly trend (7-day OLS)** — the 30% "getting worse?" term on each score.

---

## 6. Composite + bands (reuse the existing design)

Keep the live design's **weighted geometric mean** so any one near-zero pillar drags the device down
(matches WACH "any broken pillar = sick unit"):

```
H_device = Π Sᵢ^wᵢ        # over the available sub-scores, weights renormalized
# replace Sᵢ=0 with 1 to avoid annihilation; floor at 5
```

Bands unchanged: Healthy 85–100 · Watch 70–84 · Degraded 50–69 · Critical <50 · Grey (`data_integrity`<0.4).

Roll-up unchanged: Device → Room → Zone → Floor → Site (Floor = WACH "level").

---

## 7. Calibration & caveats

- **Don't ship CV-D/efficiency scores until ≥30 d of history** — kW/TR with <2 weeks is noise. Below the
  threshold, auto-degrade to band-fit and flag medium confidence.
- **Thresholds → baselines on a schedule:** start with the live design's absolute piecewise values as a
  cold-start prior, then swap each metric to per-device robust z once it has ≥14 d (≥30 d preferred). Same
  cold-start→baseline migration WACH did.
- **No power quality per AHU** — Cyberview can't replicate WACH's PF/THD/imbalance scores; those slots stay
  empty at the AHU level and live only in the plant/switchboard cluster. Don't fabricate them.
- **Tropical seasonality is mild but real** — monsoon vs dry shifts cooling load; condition baselines on
  load bin / hour-of-day, and revisit after a full ≥90-day cycle before trusting P2 optimization.
- **Change-of-value gaps ≠ missing data** — forward-fill held values in backfill; otherwise variability and
  freshness scores will misfire.
- **`val` type stability** — some topics flip numeric/string; the transform layer must coerce before scoring
  (already an ADR open item), else `data_integrity` craters.
