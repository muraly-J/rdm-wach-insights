# Spec B — RAG Knowledge Base Expansion

**Date:** 2026-03-30
**Status:** Approved
**Author:** WACH Insight Team

---

## Overview

Expand the WACH AI chatbot's `search_docs` tool from a single AHU directory file to a comprehensive domain knowledge base covering AHU components, electrical health, FAIR scoring, Malaysian hospital standards, maintenance procedures, and financial impact frameworks. Add a persona detection layer so responses are automatically pitched at the right level for general users, engineers, technicians, and financial managers.

The RAG infrastructure (ChromaDB, Qwen3 embedder, ingest pipeline, `search_docs` tool) is already fully implemented from Spec A. Spec B adds content and the persona layer on top of it.

---

## Goals

- The chatbot can answer "why" questions (why is PF low, what causes THD drift)
- The chatbot can answer "what to do" questions (what maintenance action for e0501)
- The chatbot can answer "how it works" questions (how is the FAIR score calculated)
- Responses are automatically adapted to the user's background (general, technical, technician, financial)
- Users can explicitly declare their role or have it auto-detected from their messages
- All domain knowledge reflects Malaysian hospital context (JKR/KKM standards, TNB tariffs, tropical climate)

---

## Section 1: Document Library

Ten markdown files written to `backend/data/rag_docs/`. The existing `ahu_directory.md` is retained unchanged.

### Documents

#### `ahu_components_overview.md`
Every physical component of a hospital-grade AHU:
- **Air filters**: pre-filter (G4), bag filter (F7/F9), HEPA (H13/H14) — purpose, replacement schedule, pressure drop indicators
- **Cooling coil**: chilled water or DX, heat transfer, fouling effects on energy
- **Heating coil**: hot water or electric, pre-heat applications in tropical Malaysia (rare but present in OT)
- **Fan/blower assembly**: forward-curved vs. backward-curved, SWSI vs. DWDI, static pressure, fan laws
- **Motor**: induction motor IE classes (IE1/IE2/IE3), nameplate readings, insulation class, service factor
- **Variable Frequency Drive (VFD)**: speed control, harmonic injection, energy savings, fault codes
- **Dampers**: fresh air, return air, exhaust, bypass, motorised actuators
- **Heat exchanger / heat recovery wheel**: enthalpy recovery in humid tropical climate
- **Humidifier/dehumidifier**: humidity control requirements by room class
- **Drain pan and condensate system**: Legionella risk, drain blockage faults
- **Sensors**: supply air temperature, return air temperature, relative humidity, static pressure differential, CO2/IAQ, current transducers
- **BMS interface**: control signals, alarms, trend logging
- **Belt and pulley system**: tension, alignment, wear indicators, vibration signatures
- **Access panels and casing**: air leakage effects, thermal bridging

#### `ahu_electrical_health.md`
Electrical health indicators monitored by WACH:
- **Power Factor (PF)**: definition (cos φ), unity vs. lagging/leading, inductive loads (motors) as primary cause, VFD correction, capacitor bank correction. Normal range: ≥ 0.90 for hospital AHUs. Below 0.85: TNB imposes penalty.
- **Total Harmonic Distortion (THD)**: voltage THD vs. current THD, harmonic orders (3rd, 5th, 7th), VFD as harmonic source, IEEE 519-2022 limits (THD-I < 5% at PCC), effects on motor heating and insulation
- **Phase Imbalance**: voltage unbalance vs. current unbalance, NEMA MG1 threshold (1% voltage → 6–10× current unbalance), motor derating, overheating, causes (unequal loads, loose connections, blown fuse)
- **Overload**: RMS current vs. nameplate FLA, service factor operation, thermal relay tripping, overload causes (filter blockage, coil fouling, belt slip, refrigerant undercharge)
- **Energy Anomaly**: deviation of real power consumption from rolling baseline, detection of fouled coils, clogged filters, mechanical friction, refrigerant leaks before they appear in direct measurements

#### `fair_scoring_methodology.md`
The FAIR health scoring system used by WACH:
- **What FAIR stands for**: Frequency Anomaly Index + Asset Integrity Rating (composite electrical health)
- **Five component scores**: energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload — each scored 0–100 (100 = perfect)
- **Weighting and composite**: weighted average into health_index (0–100)
- **Tiers**:
  - Healthy (≥ 80): normal operation, scheduled PM only
  - Monitor (50–79): watch closely, investigate trend, consider early intervention
  - Maintenance (30–49): action required within 1–2 weeks, book work order
  - Critical (< 30): immediate action required, risk of failure, escalate to facilities manager
- **Safety flags**: binary flags raised when a component breaches hard thresholds (e.g., THD_CHRONIC_HIGH, PF_CHRONIC_LOW, PHASE_IMBALANCE_HIGH, OVERLOAD_ACTIVE) — appear on dashboard as alert badges
- **Score interpretation**: a health_index of 65 with pf_degradation=20 means power factor is the dominant issue; address PF first
- **Temporal behaviour**: scores are computed hourly from the ETL pipeline; a single bad hour doesn't tank the score — chronic issues compound

#### `malaysian_hospital_hvac_context.md`
Malaysian regulatory and environmental context:
- **JKR Standard Specification 2025**: JKR Malaysia released the updated Standard Specification for Building Works in 2025 (replacing the 2020 edition), covering ACMV system requirements for government buildings including hospitals.
- **JKR Technical Specification for ACMV (Edition 2020, still current for technical detail)**: Specifies maintenance, testing per ANSI/ASHRAE 111, and control requirements for air conditioning and mechanical ventilation in government buildings.
- **KKM Hospital Support Services standards**: Ministry of Health Engineering Services specification for hospitals, HVAC requirements by department class, infection control requirements aligned with KKM guidelines.
- **KKM Ventilation Guidelines (2021, updated for airborne pathogen control)**: MOH guidelines on ventilation in healthcare settings to reduce respiratory pathogen transmission — specifies pressure relationships and ACH by risk zone.
- **MS 1525:2014**: Malaysian Standard — Code of practice on energy efficiency and use of renewable energy for non-residential buildings. OTTV ≤ 50 W/m², RTTV ≤ 25 W/m², chiller COP targets.
- **Infection control pressure relationships**: OT and clean rooms = positive pressure (+8 Pa); isolation rooms (infectious disease) = negative pressure (−8 Pa); corridors serve as buffer zones between pressure differentials.
- **ACH requirements by department** (JKR/KKM aligned): OT ≥ 25 ACH total (15 ACH fresh air), ICU/PICU/NICU ≥ 12 ACH, General Ward ≥ 6 ACH, Pharmacy cleanroom ISO 7/8 ≥ 20 ACH.
- **Tropical climate baseline**: Design outdoor conditions 33°C DBT / 28°C WBT (Kuala Lumpur). Indoor setpoints: wards 24°C / 55% RH, OT 21°C / 55% RH. High latent load fraction — dehumidification dominates cooling load year-round (no winter/summer seasonal variation unlike temperate climates).
- **Typical AHU energy intensity**: OT AHU 15–25 kW, Ward AHU 5–12 kW, Pharmacy FAU 3–8 kW (varies with supply air volume and room size).
- **ASHRAE 170-2025**: The current edition of the primary healthcare ventilation standard (updated from 2021). Applied in Malaysian hospitals alongside JKR/KKM standards. Key 2025 updates: natural ventilation provisions, updated imaging room requirements, revised behavioural health spaces, updated construction-phase ventilation requirements. OT requirement: ≥ 20 ACH total (ASHRAE); JKR specifies ≥ 25 ACH which is the more stringent local requirement hospitals follow.

#### `hospital_ahu_environments.md`
Room-by-room AHU application requirements:

| Department | Temp (°C) | RH (%) | ACH (total/fresh) | Pressure | Filter Class |
|---|---|---|---|---|---|
| Operating Theatre | 18–24 | 50–60 | 25 / 15 | Positive | F9 + H14 |
| ICU / PICU | 21–24 | 50–60 | 12 / 2 | Positive | F7 + F9 |
| Neonatal ICU | 24–26 | 50–60 | 12 / 2 | Positive | F7 + F9 |
| Isolation (infectious) | 21–24 | 50–60 | 12 / 2 | Negative | F7 + F9 |
| General Ward | 22–25 | 50–65 | 6 / 2 | Neutral | G4 + F7 |
| Emergency Dept | 22–25 | 50–65 | 10 / 2 | Neutral | G4 + F7 |
| Pharmacy Cleanroom | 20–22 | 40–60 | 20 / 5 | Positive | F9 + H13 |
| Sterile Supply Unit | 20–23 | 40–55 | 10 / 2 | Positive | F7 + F9 |
| Paediatric Ward | 23–25 | 50–65 | 6 / 2 | Neutral | G4 + F7 |

AHU failure implications differ by department: OT failure = surgical schedule cancellation (patient safety + revenue); PICU failure = life support risk; ward failure = patient discomfort and infection risk.

#### `tnb_tariff_financial_guide.md`
Malaysian TNB electricity tariff structure and penalty framework (RP4, effective 1 July 2025):

- **Tariff restructure (RP4)**: TNB overhauled tariff categories from 1 July 2025 under Regulatory Period 4 (2025–2027). The old single Maximum Demand (MD) charge is replaced by two separate charges: Capacity Charge + Network Charge. Base tariff increased ~14.2% from RP3.

- **Hospital tariff categories**: Most government hospitals are on Medium Voltage (MV) supply. The relevant categories are:
  - **MV General** (ex-Tariff C1/E1): flat energy rate, no TOU differentiation. Energy: RM 0.2983/kWh. Capacity + Network: RM 89.27/kW/month.
  - **MV TOU** (ex-Tariff C2/E2): time-of-use energy rates. Peak (Mon–Fri, 2 PM–10 PM): RM 0.3132/kWh. Off-peak (all other times incl. weekends/public holidays): RM 0.2723/kWh. Capacity + Network: RM 97.06/kW/month.
  - **HV General** (ex-Tariff C3/E3, 132kV and above, large hospitals): Energy RM 0.4303/kWh. Capacity + Network: RM 31.21/kW/month.

- **AFA (Automatic Fuel Adjustment)**: replaces the old ICPT mechanism. Adjusted monthly by the Energy Commission (ST) based on fuel prices and exchange rates. Jan 2026 AFA rate: −4.99 sen/kWh (a discount). Added to or subtracted from the base energy charge each month.

- **Power Factor penalty** (unchanged under RP4, applies to supplies ≤ 132kV):
  - Penalty threshold: monthly average PF < 0.85
  - For PF between 0.75 and 0.85: `[(0.85 − PF) / 0.01] × 1.5%` of the monthly bill
  - For PF below 0.75: `[(0.85 − 0.75) / 0.01 × 1.5%] + [(0.75 − PF) / 0.01 × 3%]` of the monthly bill
  - Example: PF = 0.82 → `[(0.85 − 0.82) / 0.01] × 1.5% = 3 × 1.5% = 4.5%` surcharge on total bill
  - Example: PF = 0.78 → `7 × 1.5% = 10.5%` surcharge
  - Example: PF = 0.72 → `10 × 1.5% + 3 × 3% = 15% + 9% = 24%` surcharge
  - For supplies ≥ 132kV (large hospitals): threshold is PF < 0.90

- **Capacity + Network charge impact of poor PF**: Capacity and Network charges are billed per kW of maximum demand. Poor PF means higher kVA for the same useful kW output — if the hospital's maximum demand measurement includes reactive component effects, the effective billing demand rises.

- **Cost of inaction example**: Across 121 AHUs on MV TOU tariff, if average fleet PF is 0.82, PF surcharge = 4.5% of monthly energy bill. At RM 0.30/kWh average and 200 kWh/day per AHU × 121 AHUs × 30 days = ~728,000 kWh/month → bill ~RM 218,000 → PF penalty ~RM 9,800/month = RM 117,600/year.

- **ROI of capacitor bank correction**: installation cost RM 2,000–5,000 per AHU; payback typically 6–18 months from PF penalty elimination alone, plus reduced capacity/network charges and improved motor life.

- **Energy anomaly cost**: 10% above-baseline energy on a 10 kW AHU = ~1 kW excess = at RM 0.30/kWh, ~RM 216/month wasted per AHU. Across 121 AHUs if 20% show energy anomaly: ~RM 5,200/month = ~RM 62,000/year.

- **TOU optimisation opportunity**: Hospitals on MV TOU can shift non-critical AHU pre-cooling to off-peak hours (before 2 PM or after 10 PM) to benefit from lower off-peak rates (RM 0.2723 vs RM 0.3132/kWh).

#### `fault_diagnosis_guide.md`
Decision trees for each WACH fault type:

**Low Power Factor (pf_degradation high)**
1. Is VFD installed? → Check VFD PF correction settings, check DC bus capacitors
2. No VFD → Check capacitor bank: test capacitance (should be within 5% of nameplate), check for open-circuited capacitors
3. Check motor: insulation resistance test (Megger), winding resistance balance
4. Check for added inductive loads on same circuit (other motors, transformers)
5. If PF < 0.75 and trending down → immediate intervention; TNB surcharge rate doubles to 3%/0.01 below 0.75 (on top of the 15% already accrued from 0.85→0.75 band) plus motor overheating risk

**High THD (thd_drift high)**
1. Is VFD installed? → Check VFD for line reactor, check if output filter fitted
2. Check for other non-linear loads on same feeder (UPS, lighting ballasts, variable speed pumps)
3. Measure THD at motor terminals vs. at MCC → localise source
4. If THD-V > 8% at PCC → notify electrical engineer, may need harmonic filter

**Phase Imbalance (phase_imbalance high)**
1. Check supply voltage at MCC: measure L1-L2, L2-L3, L1-L3 → should be within ±1%
2. Check contactor contacts: burning, pitting, unequal contact pressure
3. Check motor terminal connections: torque to spec, check for corrosion
4. Check for single-phase loads on one phase of same feeder
5. Current imbalance > 5% with balanced voltage → motor winding fault suspected

**Overload (overload high)**
1. Check air filters: if ΔP across filter > design → replace filter
2. Check cooling coil: visual inspection for fouling, check chilled water valve operation
3. Check belt tension: slack belt → motor works harder, check belt wear
4. Check ambient temperature: if plant room > 40°C → motor derating required
5. Check FLA on nameplate vs. measured current: if > 110% FLA → reduce load or upsize motor

**Energy Anomaly (energy_anomaly high)**
1. Compare with same AHU same time last week → trending up or sudden jump?
2. Sudden jump → check for mechanical fault (seized bearing, jammed damper)
3. Gradual drift → check filter pressure drop (fouled filters), check coil fouling (reduced ΔT), check refrigerant charge
4. Cross-reference with weather data → unusually hot day can explain anomaly without fault

#### `ahu_maintenance_guide.md`
Preventive maintenance schedules for hospital AHUs in Malaysia:

**Daily (BMS operator check)**
- Review health dashboard for Critical or Maintenance tier AHUs
- Check supply air temperature and humidity vs. setpoints
- Check BMS alarms

**Weekly**
- Visual inspection of filter condition (if accessible)
- Check condensate drain pan — no standing water
- Check belt tension by feel/sound (squealing = slipping)
- Log energy readings for trend comparison

**Monthly**
- Replace pre-filters (G4) — more frequent in dusty areas
- Check and record motor current (all 3 phases)
- Inspect VFD display for fault codes
- Check drain pan chemical dosing (Legionella prevention)

**Quarterly**
- Replace bag filters (F7/F9) or per pressure drop indication
- Full motor megger test (insulation resistance ≥ 1 MΩ, ideally > 10 MΩ)
- Check belt alignment with straight-edge
- Clean cooling coil fins (compressed air or low-pressure water)
- Test capacitor bank (capacitance measurement)
- Grease motor bearings per manufacturer schedule

**Annual**
- Replace HEPA filters (H13/H14) — per pressure drop or annual
- Full coil chemical wash (Alkali + acid clean)
- Motor winding resistance test
- VFD inspection and firmware check
- Full ductwork inspection for air leaks
- Damper actuator calibration
- Commission room pressurisation verification

**Safety (LOTO procedure)**
Before any mechanical work: Lockout-Tagout on MCC incomer, test for dead, permit-to-work from engineering department, notify infection control if work is in sensitive zone (OT, ICU).

#### `ahu_performance_benchmarks.md`
Normal operating ranges for Malaysian hospital AHUs (tropical climate):

| Parameter | Healthy Range | Monitor | Critical |
|---|---|---|---|
| Power Factor | ≥ 0.90 | 0.85–0.89 | < 0.85 |
| Current Unbalance | < 2% | 2–5% | > 5% |
| THD-I | < 5% | 5–8% | > 8% |
| Supply Air Temp (Ward) | 12–15°C off-coil | ±2°C drift | > 4°C drift |
| Filter ΔP (G4) | < 80 Pa | 80–120 Pa | > 120 Pa |
| Motor Temperature Rise | < 40°C above ambient | 40–60°C | > 60°C |
| Energy Index (Ward AHU, 7.5 kW) | 150–180 kWh/day | 180–210 | > 210 |

AHU age degrades benchmarks: expect 5–10% energy increase and 0.02–0.05 PF drop per 5 years without major servicing.

#### `wach_system_guide.md`
WACH monitoring system overview for users:
- **What WACH monitors**: 121 AHUs across 11 levels, hourly health scoring, real-time electrical readings (power, PF, THD, phase currents, voltages)
- **Health score meaning**: 0–100 composite score; 80+ = no concern; 50–79 = watch; 30–49 = schedule maintenance; below 30 = act now
- **Dashboard levels**: click a level tile to drill into individual AHUs; click an AHU card to see component score breakdown
- **What the AI can answer**: health status by level or AHU, root cause of poor scores, maintenance recommendations, financial impact of faults, explanations of any metric or fault type
- **What the AI cannot answer**: real-time maintenance team availability, spare parts stock, contractor quotes, clinical decisions
- **When to escalate**: Critical tier AHU in OT/ICU/PICU → immediate call to on-call engineer, do not wait for next shift
- **Trend questions**: ask "how has Level 5 been trending this week?" or "which AHUs have been consistently below 60 for 3 days?"

---

## Section 2: Persona Detection Layer

### `backend/llm/persona_detector.py`

Stateless function called once per chat turn. Returns one of four literals.

**Detection logic (priority order):**
1. `stated_persona` parameter (from frontend role selector or `/role` command) — overrides all
2. Explicit declaration in current message ("I am the biomedical engineer", "explain simply", "I'm a technician")
3. Keyword signals in current message (weighted scoring)
4. Rolling pattern across last 3 history messages
5. Default: `"general"`

**Keyword weights per persona:**

- `financial`: cost, RM, budget, penalty, ROI, savings, expenditure, tariff, TNB, payback, bill, money, financial, revenue
- `technician`: check, replace, inspect, clean, tighten, fault, repair, capacitor, belt, coil, filter, reading, measurement, Megger, LO/TO, bearing, winding, contactor, relay
- `technical`: THD, harmonic, power factor, phase imbalance, impedance, current, voltage, frequency, FAIR, algorithm, calculation, analysis, pf_degradation, energy_anomaly
- `general`: (default — fires when no other signals score above threshold)

Threshold: a persona wins if its keyword score is at least 2 points above any other. Ties → `technical` beats `technician`, `general` is last resort.

### System Prompt Persona Blocks (`backend/llm/prompts.py`)

Four `PERSONA_BLOCKS` entries appended to the base system prompt:

- **general**: "The user is not technical. Use plain language and everyday analogies. Avoid electrical jargon. Focus on what it means practically: is it serious, does someone need to come fix it, is it costing money. One clear action or conclusion per answer."
- **technical**: "The user is an engineer or technically fluent. Use precise terminology. Include numerical thresholds, component-level breakdowns, and scoring methodology where relevant. Reference standards (IEEE 519, ASHRAE 170, NEMA MG1) where appropriate."
- **technician**: "The user is a hands-on maintenance technician. Respond with step-by-step diagnostic and repair actions. Specify measurements to take (e.g., 'check L1-L2 voltage at MCC'), tools required, and LOTO safety steps. Keep language direct and procedural."
- **financial**: "The user has a financial mindset. Lead with RM cost and penalty figures. Frame health scores as financial risk and cost-of-inaction. Reference TNB penalty calculations and ROI of maintenance. Avoid electrical theory unless directly asked."

### Frontend Role Selector

Small gear/settings icon above `ChatInput`. On click, expands a row of 4 pill buttons: **General | Engineer | Technician | Financial**. Selected persona is stored in `ChatWindow` state, passed as `persona` field in `sendChatMessage`. Collapsed by default. Selecting a role shows a brief confirmation in the chat (bot message: "Got it — I'll explain things from a financial perspective.").

---

## Section 3: Architecture

### Files

| Action | File | Purpose |
|--------|------|---------|
| Create (×10) | `backend/data/rag_docs/*.md` | Domain knowledge documents |
| Create | `backend/llm/persona_detector.py` | Stateless persona detection |
| Modify | `backend/llm/prompts.py` | Add `PERSONA_BLOCKS`, `build_system_prompt(persona)` |
| Modify | `backend/routes/chat.py` | Call `detect_persona()`, inject persona block into prompt |
| Modify | `backend/models/schemas.py` | Add optional `persona: str` to `ChatRequest` |
| Modify | `frontend/src/api/client.ts` | Pass `persona` in request body |
| Modify | `frontend/src/components/chat/ChatInput.tsx` | Role selector UI |
| Modify | `frontend/src/components/chat/ChatWindow.tsx` | Persona state + pass to API |
| Create | `backend/scripts/ingest_all_docs.py` | Batch ingest all `data/rag_docs/*.md` |
| Create | `backend/tests/test_persona_detector.py` | Unit tests: all detection cases |

### Request Flow

```
User message (+ optional persona field from frontend)
        ↓
persona_detector.detect(message, history, stated_persona)  →  persona enum
        ↓
build_system_prompt(persona)  →  system prompt string
        ↓
QwenClient.generate_with_tools(messages, tools, system_prompt)
        ↓
  [tool loop — search_docs hits ChromaDB, ~150–200 chunks indexed]
        ↓
Final answer shaped to persona tone
        ↓
Frontend renders via ReactMarkdown + remark-gfm
```

### Ingest Pipeline

`python -m scripts.ingest_all_docs` from `backend/`:
- Iterates `data/rag_docs/*.md`
- Calls existing `rag.ingest.ingest()` for each file (chunk_size=800, overlap=100)
- Hash-based dedup already in `ingest.py` — safe to re-run
- Reports total chunks ingested
- Expected output: ~150–200 chunks across 11 files

---

## Out of Scope

- ChromaDB metadata filtering by audience (Option C — excluded by design)
- Multi-language support (Bahasa Malaysia)
- Document versioning or update workflows
- Real-time document sync from external sources

---

## Testing

- `test_persona_detector.py`: one test per persona, explicit override test, default fallback test, mixed-signal test
- Manual smoke test: ask "why is power factor important?" as default user, as `/role financial`, as `/role technician` — verify three distinct response styles
- Ingest smoke test: run `ingest_all_docs.py`, verify chunk count > 100, run `search_docs("power factor penalty")` → returns TNB-relevant chunks
