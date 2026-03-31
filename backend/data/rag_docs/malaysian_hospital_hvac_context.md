# Malaysian Hospital HVAC Context

## Regulatory Framework

### JKR (Jabatan Kerja Raya) Standards
JKR Standard Specification for Building Works 2025 (updated from 2020 edition) governs HVAC design and installation in Malaysian government buildings including public hospitals.

Key ACMV (Air Conditioning and Mechanical Ventilation) requirements:
- System maintenance, control, and monitoring per ANSI/ASHRAE Standard 111
- Redundancy requirements for critical zones (N+1 for OT, ICU, NICU AHUs)
- Energy efficiency targets aligned with MS 1525

### Ministry of Health (KKM) Standards
KKM Hospital Support Services Engineering specification sets HVAC requirements for each hospital department based on clinical risk classification.

KKM Ventilation Guidelines (2021, updated for airborne pathogen control) specifies:
- Minimum ACH rates by risk zone
- Pressure relationships between clinical zones
- Filter efficiency requirements by department
- Commissioning and maintenance verification requirements

### MS 1525:2014
Malaysian Standard — Code of Practice on Energy Efficiency and Use of Renewable Energy for Non-Residential Buildings.
- OTTV (Overall Thermal Transfer Value): ≤ 50 W/m² for building envelope
- RTTV (Roof Thermal Transfer Value): ≤ 25 W/m²
- Chiller plant COP targets: ≥ 4.5 for central chilled water systems
- Drives energy efficiency investments in hospital HVAC

### ASHRAE 170-2025
American Society of Heating, Refrigerating and Air-Conditioning Engineers Standard 170-2025 (Ventilation of Health Care Facilities) is the primary international reference applied in Malaysian hospitals alongside JKR/KKM requirements. Where JKR/KKM is more stringent (e.g., OT ACH), the local standard takes precedence.

Key 2025 updates over 170-2021: natural ventilation provisions, updated imaging room requirements, revised behavioural health spaces, updated construction-phase ventilation requirements.

## Tropical Climate Baseline

Malaysian hospitals (Peninsula Malaysia) design to:
- **Outdoor design conditions**: 33°C dry-bulb temperature (DBT) / 28°C wet-bulb temperature (WBT) — equivalent to approximately 85% relative humidity at peak conditions
- **Indoor setpoints (wards)**: 24°C / 55% RH
- **Indoor setpoints (OT)**: 18–24°C / 50–60% RH

**Critical implication**: Malaysia has no winter. AHUs run at near-full load year-round. There is no seasonal low-demand period that can be used for major overhauls without disrupting clinical operations. This makes condition monitoring (WACH scoring) especially important — you cannot rely on seasonal downtime to catch problems.

**High latent load**: tropical climate means dehumidification dominates the cooling load. Typically 40–50% of total cooling load is latent (moisture removal). A fouled cooling coil or reduced chilled water flow affects dehumidification before it visibly affects sensible temperature — RH rises, which increases infection risk in surgical environments.

**No-load period risk**: AHUs left off for >24 hours in tropical climate accumulate condensation, mould, and biological growth rapidly. WACH Critical tier AHUs in non-clinical zones should not simply be switched off — they require a controlled approach.

## Infection Control Pressure Relationships

Pressure relationships are maintained by carefully balancing supply and exhaust/return air volumes:

- **Positive pressure zones** (supply > exhaust): OT, clean rooms, ICU, NICU, Bone Marrow Transplant Unit, Pharmacy sterile manufacturing. Prevents contamination ingress from adjacent corridors.
- **Negative pressure zones** (exhaust > supply): Isolation rooms (airborne infections — TB, COVID, measles), airborne infection isolation rooms. Prevents contaminated air from escaping to corridor.
- **Neutral zones**: General wards, corridors, offices.

**Pressure cascade**: OT → Scrub → Sub-sterile → Corridor → Outside. Each zone must be positive relative to the next outward zone.

**AHU failure impact on pressure**: if an OT supply AHU trips, positive pressure is lost within minutes. Contamination risk is immediate. This is why OT AHUs require N+1 redundancy and WACH Critical alerts for OT-serving AHUs warrant immediate escalation.

## ACH Requirements by Department (JKR/KKM Malaysia)

| Department | Total ACH | Fresh Air ACH | Pressure |
|---|---|---|---|
| Operating Theatre | ≥ 25 | ≥ 15 | Positive |
| ICU / PICU / NICU | ≥ 12 | ≥ 2 | Positive |
| Airborne Infection Isolation | ≥ 12 | ≥ 2 | Negative |
| General Ward | ≥ 6 | ≥ 2 | Neutral |
| Emergency Department | ≥ 10 | ≥ 2 | Neutral |
| Pharmacy Cleanroom | ≥ 20 | ≥ 5 | Positive |
| Central Sterile Supply | ≥ 10 | ≥ 2 | Positive |
| Mortuary | ≥ 10 | 100% OA | Negative |

## Energy Intensity Context

Typical installed AHU motor sizes in Malaysian hospitals:
- Operating Theatre AHU: 15–25 kW (large volume, HEPA filtration, precise humidity control)
- ICU / PICU AHU: 7.5–15 kW
- General Ward AHU: 5–11 kW
- Pharmacy FAU: 3–7.5 kW
- Corridor / Common AHU: 2.2–5.5 kW

Hospitals are major electricity consumers. A 500-bed hospital in Malaysia typically consumes 8–15 GWh/year. HVAC accounts for approximately 50–60% of that — making AHU efficiency a primary energy management target.
