# Hospital AHU Environments — Room-by-Room Requirements

Each hospital department has specific AHU requirements driven by clinical function, infection control, and patient vulnerability. This document maps department types to their HVAC requirements and explains the consequences of AHU failure in each zone.

## Operating Theatre (OT)

**Temperature**: 18–24°C (surgeons often prefer 20–21°C; neonatal OT 26–28°C)
**Humidity**: 50–60% RH
**ACH**: ≥ 25 total (≥ 15 fresh air)
**Pressure**: Positive (+8 Pa minimum relative to scrub corridor)
**Filtration**: Pre-filter G4 → Bag filter F9 → HEPA H14 at supply terminal

Consequence of AHU failure: positive pressure lost → contamination risk → surgical site infection risk → must suspend operations. Requires N+1 redundant AHU. WACH Critical tier OT AHU = immediate escalation, do not wait for next shift.

AHU type: typically dedicated fresh air unit (FAU) + recirculation unit (ACU). The FAU handles OA conditioning; ACU handles filtration and fine temperature control. Both are monitored by WACH.

## Paediatric Intensive Care Unit (PICU) / Adult ICU / NICU

**Temperature**: 21–24°C (NICU: 24–26°C with incubator supplement)
**Humidity**: 50–60% RH
**ACH**: ≥ 12 total (≥ 2 fresh air)
**Pressure**: Positive
**Filtration**: G4 → F7 → F9

Consequence of failure: life-critical patients on ventilators and monitoring. Positive pressure loss risks healthcare-associated infection (HAI). WACH Critical in ICU/PICU/NICU = immediate call to on-call engineer.

## General Inpatient Ward (Levels 7–11 in WACH building)

**Temperature**: 22–25°C
**Humidity**: 50–65% RH
**ACH**: ≥ 6 total (≥ 2 fresh air)
**Pressure**: Neutral
**Filtration**: G4 → F7

Consequence of failure: patient discomfort, elevated infection risk, complaints. Not immediately life-threatening in most ward types, but paediatric patients are more vulnerable. WACH Maintenance tier = schedule work order within 1–2 weeks.

## Emergency Department

**Temperature**: 22–25°C
**Humidity**: 50–65% RH
**ACH**: ≥ 10 total (≥ 2 fresh air)
**Pressure**: Neutral (sub-waiting areas may be negative for respiratory triage)
**Filtration**: G4 → F7

High footfall, variable occupancy, long operating hours. Emergency AHU is exposed to outdoor air contaminants more than ward AHUs (patient entry/exit). Filter replacement frequency should be higher.

## Pharmacy Cleanroom / Sterile Compounding

**Temperature**: 20–22°C
**Humidity**: 40–60% RH (strict RH control for drug stability)
**ACH**: ≥ 20 total (≥ 5 fresh air)
**Pressure**: Positive (ISO Class 7 or 8)
**Filtration**: G4 → F9 → H13 (or H14 for ISO 5 critical zones)

Consequence of failure: sterile compounding products contaminated → batch rejection → drug supply disruption. Very high cost of failure.

## Central Sterile Supply Unit (CSSU)

**Temperature**: 20–23°C
**Humidity**: 40–55% RH
**ACH**: ≥ 10 total
**Pressure**: Positive (clean side), Negative (dirty/decontam side)
**Filtration**: G4 → F7 → F9

CSSU has two pressure zones: decontamination (negative) and clean packing/storage (positive). WACH monitors all AHUs serving this department. Failure in clean zone = reprocessed instruments contaminated.

## Bone Marrow Transplant Unit (BMTU) / Oncology

**Temperature**: 22–24°C
**Humidity**: 40–60% RH
**ACH**: ≥ 12 total
**Pressure**: Positive (+12 Pa or higher, more stringent than standard ICU)
**Filtration**: G4 → F9 → H14

Immuno-compromised patients. Aspergillus contamination (from construction dust, mould) can be fatal. HEPA filtration mandatory. WACH Critical = stop non-essential work in vicinity, check HEPA filter integrity.

## Airborne Infection Isolation Room

**Temperature**: 21–24°C
**Humidity**: 50–60% RH
**ACH**: ≥ 12 total
**Pressure**: Negative (−8 Pa relative to corridor)
**Filtration**: G4 → F9 (exhaust HEPA required before discharge to outside)

Used for TB, measles, COVID, other airborne-transmissible diseases. Negative pressure maintained by having slightly more exhaust than supply. WACH monitoring of these AHUs must flag any positive pressure reversal immediately.

## Level-Specific Zones in WACH Building

Based on the WACH building AHU mapping:
- **Level 1**: Emergency Department (e0110–e0117), Imaging (e0118, e0120, e0121), support services
- **Level 2**: Outpatient clinics, Child Development Centre, Pharmacy
- **Level 3**: Pathology, Dental, Paediatric Specialist Clinic
- **Level 4**: Inpatient Pharmacy, Bone Marrow Transplant, Maternity OT (e0413–e0416)
- **Level 5**: PICU (e0501, e0510), Adult ICU (e0505, e0507), HDU, OT complex (e0622)
- **Level 6**: Administration, CSSU (e0605, e0606, e0628), Library
- **Levels 7–11**: Inpatient wards (Obstetric, Gynaecology, Paediatric Medical, Neonatology, Paediatric Surgical)

AHU failure impact is highest in Level 5 (ICU/OT) and Level 4 (BMT/OT). Levels 7–11 are ward AHUs — lower immediate clinical risk but high patient volume.
