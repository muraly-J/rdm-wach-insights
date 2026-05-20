# Cyberview Health Index — Design

Mirror WACH pattern: **Raw Scores → Sub-Scores → Composite Health Index**, 0–100 (100 = healthy), grey state when data missing, device → room → floor → site rollup.

---

## 1. Per-AHU / Per-FCU scoring (primary unit)

Seven raw dimensions. All score 0–100. Each has a **confidence** field (0–1) for grey-state propagation.

### 1.1 Thermal Delivery Score (`S_thermal`) — weight 0.18

Question: is the unit hitting its temperature target?

Inputs: `Temperature_Return_Air` (rat), `Valve_Temperature_Setpoint` (rat_sp), `Temperature_Supply_Air` (sat), `Status_Start-Stop`, `Operation_State`.

Only score when unit is ON. If OFF → grey (not penalised, not credited).

```
err          = rat - rat_sp                            # positive = too warm
sat_drop     = rat - sat                               # positive = cooling delivered
rat_dev_pts  = clamp(100 - 40 * max(0, err - 0.5), 0, 100)   # 1°C over = 80, 2°C over = 40
delivery_pts = clamp(50 + 20 * sat_drop, 0, 100)             # >2.5°C drop saturates to 100
S_thermal    = 0.6 * rat_dev_pts + 0.4 * delivery_pts
```

Persistence guard: only flag below 60 when sustained ≥3 polls (~1.5 min).

### 1.2 Hydronic Performance Score (`S_hydro`) — weight 0.20

Question: is the chilled-water coil exchanging heat properly?

Inputs: `Temperature_CHWS` (wst), `Temperature_CHWR` (wrt), `Valve_Flow_Rate_SI` (m³/h), `Valve_Pressure_Differential`.

```
# Sanity gate — kills data integrity if violated
chws_ok = 4 <= wst <= 18
chwr_ok = 6 <= wrt <= 22
flow_ok = 0 <= flow <= 50

if not (chws_ok and chwr_ok): S_hydro = GREY, S_data_integrity -= heavy
else:
    dT       = wrt - wst                          # 5-7°C nominal
    dT_pts   = piecewise(dT):
                 dT < 1   → 10    # no exchange = scaling/airlock
                 1-3      → 30 + (dT-1)*15
                 3-7      → 70 + (dT-3)*7.5      # 7°C → 100
                 7-10     → 100 - (dT-7)*5      # too high = low flow
                 >10      → 75 - (dT-10)*10
    # valve-flow coherence
    flow_pts = 100 if (valve_fb > 5% and flow > 0.05) or (valve_fb < 5% and flow < 0.1)
               else 40        # commanded open but no flow OR closed but flowing
    S_hydro  = 0.7 * dT_pts + 0.3 * flow_pts
```

### 1.3 Air Path Score (`S_air`) — weight 0.15

Question: fan and duct delivering air at the right pressure?

Inputs: `VSD_Feedback` (or `VSD_Speed_Feedback`), `VSD_Command_Speed`, `Pressure_Supply_Air` (dsp), `Pressure_Supply_Air_High_Setpoint`, `_Low_Setpoint`.

```
vsd_err     = |vsd_fb - vsd_cmd|                   # Hz
vsd_pts     = clamp(100 - 20 * vsd_err, 0, 100)    # 5 Hz off = 0

dsp_band_mid = (dsp_high_sp + dsp_low_sp) / 2
dsp_dev      = |dsp - dsp_band_mid| / max(1, (dsp_high_sp - dsp_low_sp)/2)
dsp_pts      = clamp(100 - 50 * dsp_dev, 0, 100)

# rolling-std hunting penalty over last 5 polls (~2.5 min)
hunt_penalty = min(30, 5 * std(vsd_fb, n=5))
S_air        = 0.5 * vsd_pts + 0.4 * dsp_pts + 0.1 * (100 - hunt_penalty)
```

Unit-coercion guard: if payload unit differs across polls for same device → `S_data_integrity` penalty.

### 1.4 Valve Health Score (`S_valve`) — weight 0.14

Question: does the modulating valve actually do what it's told?

Inputs: `Valve_Command_Position`, `Valve_Feedback` / `Valve_Feedback_Position`, `Valve_Pressure_Differential`, `Valve_Alarm`, `Temperature_Return_Air`, `Valve_Temperature_Setpoint`.

```
trk_err   = |valve_cmd - valve_fb|                 # %
trk_pts   = clamp(100 - 5 * trk_err, 0, 100)       # 20% off = 0

# Saturation pathology: 100% open but still not cooling
sat_flag  = (valve_cmd >= 95) and (rat - rat_sp > 1.0) sustained 3 polls
sat_pts   = 30 if sat_flag else 100

# Always-closed pathology: 0% but rat well above sp (frozen/stuck closed)
stuck_flag = (valve_cmd <= 5) and (rat - rat_sp > 2.0) sustained 3 polls
stuck_pts  = 30 if stuck_flag else 100

alarm_pts = 0 if Valve_Alarm == 1 else 100

S_valve = 0.4*trk_pts + 0.25*sat_pts + 0.15*stuck_pts + 0.20*alarm_pts
```

### 1.5 Control Mode Score (`S_ctrl_mode`) — weight 0.08

Question: BMS in charge, or human override?

Inputs: `Operation_Mode` (AUTO/MANUAL), `AOM_Status` (AUTO/ON/OFF), `Valve_Operation_Mode`.

```
manual_dur = consecutive minutes Operation_Mode == "MANUAL"
mode_pts   = piecewise(manual_dur):
               <30 min   → 100
               30-120    → 80
               2-8 h     → 60
               8-24 h    → 30      # crosses Track-C threshold
               >24 h     → 0

valve_manual = Valve_Operation_Mode != "AUTO"
v_mode_pts   = 70 if valve_manual else 100

aom_pts      = 100 if AOM_State in {"AUTO","ON"} else 60

S_ctrl_mode = 0.5*mode_pts + 0.3*v_mode_pts + 0.2*aom_pts
```

### 1.6 Reliability Score (`S_reliab`) — weight 0.15

Question: alarms, trips, cycling.

Inputs: `Status_Trip`, `Filter_Alarm`, edge-detected `Status_Start-Stop` transitions, `Operation_State`.

```
trip_pts    = 0 if Status_Trip ON in last 24h else 100        # hard reset to 100 after 24h clear
filter_pts  = 30 if Filter_Alarm ON else 100

# cycling: count START transitions in 24h
starts_24h  = count_edges(Status_Start-Stop, 24h)
baseline    = per-device EWMA over 30 days, default 4
cyc_z       = (starts_24h - baseline) / max(1, sigma_baseline)
cyc_pts     = clamp(100 - 25 * max(0, cyc_z - 1), 0, 100)     # 2σ above = 75, 5σ = 0

# Scheduled-occupancy off
unplanned_off_pts = 40 if (Operation_State == OFF and oct == 1) else 100

S_reliab = 0.40*trip_pts + 0.20*filter_pts + 0.20*cyc_pts + 0.20*unplanned_off_pts
```

### 1.7 Data Integrity Score (`S_data`) — weight 0.10

Question: do we trust the inputs?

Inputs: bounds checks across all sensors, unit-drift detection, freshness.

```
n_sensors_checked = N
n_bad             = sensors out-of-range or stale > 3 poll intervals
n_unit_drift      = sensors where payload unit changed since last poll
freshness_pts     = clamp(100 - 10*minutes_since_last_msg, 0, 100)

bounds_pts = clamp(100 - 15 * n_bad, 0, 100)
unit_pts   = clamp(100 - 30 * n_unit_drift, 0, 100)

S_data = 0.4*freshness_pts + 0.4*bounds_pts + 0.2*unit_pts
```

`S_data` doubles as the **confidence** for the composite (low S_data → grey-state propagation).

---

## 2. Sub-Score grouping (mirrors WACH Score Derivation panels)

| Sub-Score | Components | Weight in composite |
|---|---|---|
| **Comfort & Delivery** | `S_thermal` | 0.18 |
| **Mechanical Plant** | `S_hydro` + `S_air` + `S_valve` | 0.49 |
| **Operational Discipline** | `S_ctrl_mode` + `S_reliab` | 0.23 |
| **Sensor Trust** | `S_data` | 0.10 |

---

## 3. Composite Health Index — per device

Weighted **geometric** mean (so any one near-zero pillar drags the whole score — matches WACH "any broken pillar = sick unit"):

```
H_device = ( S_thermal^0.18
           * S_hydro^0.20
           * S_air^0.15
           * S_valve^0.14
           * S_ctrl_mode^0.08
           * S_reliab^0.15
           * S_data^0.10 )

# replace any S = 0 with 1 to avoid total annihilation; cap floor at 5
```

Bands (same as WACH):

| Band | Range | UI |
|---|---|---|
| Healthy | 85–100 | green |
| Watch | 70–84 | yellow |
| Degraded | 50–69 | orange |
| Critical | <50 | red |
| Grey | `S_data` < 0.4 | grey-state wrapper |

---

## 4. Auxiliary device scorecards

Don't shoehorn pumps / plant / switchboards into the AHU schema. Separate, narrower indexes that roll into the same dashboard.

### 4.1 Pump Health Index (`H_chwp`) — for CHWP-N

Available signals: `VSD_Speed_Feedback`, `VSD_Command_Speed`, `Pressure_Discharge`, `Pressure_Suction`, `Pressure_Differential`, `VSD_Pressure_Setpoint`, `Status_Duty_VSD`, `Status_Trip`.

| Raw | Formula | Weight |
|---|---|---|
| `P_dp_track` | tracking error: dp vs `VSD_Pressure_Setpoint` | 0.30 |
| `P_vsd_track` | `|vsd_fb - vsd_cmd|` | 0.25 |
| `P_cavitation_risk` | flag if `Pressure_Suction < 0.5 bar` while running | 0.15 |
| `P_dead_head` | flag if `vsd_fb > 30 Hz` AND `dp ≈ 0` | 0.15 |
| `P_reliab` | `Status_Trip`, `Status_Duty_VSD` consistency | 0.15 |

Compose same way as AHU. **CHWP devices in the audit have full pump telemetry — this is the strongest auxiliary score the data supports.**

### 4.2 Plant Efficiency Index (`H_plant`) — for BTU-Primary-Header

Available: `Power_Active` (kW), `Energy_Cumulative` (MWh), `Cooling_Output` (TR), `Flow_Rate` (gpm), `Temperature_CHWS`/`CHWR`.

| Raw | Formula | Weight |
|---|---|---|
| `Plant_kW_per_TR` | rolling 1h `Power_Active` ÷ `Cooling_Output`; pts ↓ as kW/TR rises above 0.7 | 0.45 |
| `Plant_dT` | `CHWR - CHWS` band-fit (4–7°C ideal) | 0.25 |
| `Plant_load_factor` | `Cooling_Output` / nameplate TR | 0.15 |
| `Plant_data_health` | freshness + sanity | 0.15 |

Caveat: zero-value snapshot in audit. Wait for active-hours data before tuning thresholds.

### 4.3 Switchboard Reliability Index (`H_msb`) — for MSB / EMSB / DB

Only digital flags available. **Index is event-driven, not continuous.**

| Raw | Formula | Weight |
|---|---|---|
| `MSB_trip_24h` | count `*_Status_Trip` events in 24h; 0 → 100, any → 50, ≥2 → 0 | 0.50 |
| `MSB_ef_count` | `Earth_Fault_Relay_Status` activations | 0.25 |
| `MSB_ocr_count` | `Overcurrent_Relay_Status` activations | 0.25 |

Useful as **alert feed**, weak as a continuous health number. Surface as event log on dashboard, not gauge.

---

## 5. Roll-up hierarchy (matches WACH level/AHU pattern)

```
Site          (Cyberview23, CoPlace3)
 └─ Floor     (LGF, LB1, LRF, ...)        ← analogue of WACH "level"
     └─ Zone  (North, South_East, ...)
         └─ Area (Parking, Mechanical, ...)
             └─ Room (Hex_Room, AHU_Room_4, ...)
                 └─ Device (AHU-GF-4B, CHWP-1, ...)
```

Roll-up rule (matches WACH ranking endpoint):

```
H_room   = weighted_mean(H_device, weights = device_criticality)
H_floor  = weighted_mean(H_room,   weights = room_count)
H_site   = weighted_mean(H_floor,  weights = floor_device_count)
```

Criticality weights default to 1.0; bump for OT, ICU-equivalent zones once mapping known.

---

## 6. Dashboard surfaces (1:1 with WACH revamp)

| WACH panel | Cyberview analogue |
|---|---|
| `WelcomeHero` | Site selector (Cyberview23 / CoPlace3) + global H_site gauge |
| `DashboardGate` | Floor health heatmap |
| `LevelSelectorBar` (sticky) | Floor selector bar |
| `Dashboard / RankingChart` | Top-5 / Bottom-5 AHU by `H_device` for selected floor |
| `ScoreDerivation` panel | Per-device drilldown: 7 raw bars + 4 sub-score wedges + composite gauge |
| `RawScoreRelationChart` | Time series of raw scores over 24h/7d |
| `CombinedScoresChart` | `H_device` trend + overlay of `Cooling_Output` and `Power_Active` from plant |
| `Compare mode` | Side-by-side raw-score columns for 2–4 devices |
| `GreyStateWrapper` | Activated whenever `S_data < 0.4` — applies to whole device card |
| Pump cards | Separate `H_chwp` cards in a "Plant Room" tab |
| Plant card | Single `H_plant` hero on Plant tab |
| Switchboard alerts | Event log strip on Electrical tab (no gauge) |

---

## 7. Update cadence & storage

- Raw scores computed every **30 s** on ingest (matches MQTT publish rate).
- 1-min, 5-min, 1-h, 24-h rolling aggregates persisted (InfluxDB downsampling, mirrors WACH).
- Health bands change-events written to SQLite for alerting.
- Grey-state windows logged separately so the UI can show "we didn't know" honestly — same pattern as WACH `useGreyState`.

---

## 8. What this index does NOT include — and why

| Omitted | Reason |
|---|---|
| Per-AHU energy efficiency (kWh/TR) | No per-AHU kWh meter on broker. Plant only. |
| Power quality (PF, THD, V/A unbalance) | No power-meter telemetry. |
| Continuous filter trend | Only `Filter_Alarm` binary; no filter ΔP. |
| Controller-fight detection (PID error/integrator) | Only PID gains published, not state. |
| Outdoor-load normalisation | OAT/OAH/GHI absent until open-meteo wired. |
| CO2 / IAQ | Not published. |
| Runtime-based degradation | No cumulative runtime counter. |

These map directly to the prior gap analysis — add the sensor, the score slot is already reserved.

---

## 9. Implementation sequence (matches WACH revamp PR cadence)

1. ETL: subscribe to whitelisted param list, JSON-parse, unit-coerce, write to InfluxDB with `(site, floor, zone, area, room, device, channel, param)` tags.
2. Score engine (Python service in `backend/core/cyberview_scoring.py`): compute 7 raw scores per device per 30 s window.
3. Grey-state propagation + roll-up.
4. API: `/api/cv/health-index?site=...&floor=...`, `/api/cv/device/{id}/scores`, `/api/cv/ranking?floor=...`.
5. Frontend: clone WACH `ScoreDerivation`, swap data source, add Plant/Pump/Electrical tabs.
6. Calibration pass after 7 days of live data — tune piecewise thresholds per device class (AHU vs AHU-GF vs FCU-SME).

Bottom line: **7 raw scores + 4 sub-scores + 1 composite per device**, with auxiliary pump/plant/switchboard indexes. Every score is backed by a signal that actually appears in the audit; every score that *would* exist in a fuller WACH equivalent has a placeholder tied to a specific gap-closure item.
