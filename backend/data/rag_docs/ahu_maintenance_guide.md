# AHU Maintenance Guide — Malaysian Hospital Standards

Preventive maintenance (PM) schedules and corrective procedures for hospital-grade AHUs in Malaysia. Based on JKR Standard Specification 2025, KKM Hospital Support Services guidelines, and manufacturer recommendations for tropical climate continuous-duty operation.

## Permit-to-Work and LOTO Procedure

Before ANY physical maintenance involving the AHU:
1. Submit Permit-to-Work (PTW) request to Engineering Department, minimum 24 hours notice for planned work
2. For clinical zones (OT, ICU, NICU): inform Ward Manager and Infection Control Officer — obtain their clearance
3. At the MCC: identify the correct incomer for the AHU. Confirm with single-line diagram.
4. Switch off MCCB/switch, then apply personal padlock to lockout device
5. Hang warning tag: "DO NOT ENERGISE — Maintenance in Progress — [Name] [Date]"
6. Use voltage tester to confirm dead on all three phases at motor terminal or panel output
7. Mechanical lockout: for belt drives, apply shaft lock or insert wooden block to prevent fan rotation

Reinstatement: reverse order. Remove all tools and personnel from AHU casing before energising. Do a no-load test (brief run) before handing back to operations.

## Preventive Maintenance Schedule

### Daily (BMS Operator / Dashboard Check — 5 minutes)
- Review WACH dashboard: any AHU in Critical tier? Any new safety flags?
- Check supply air temperature and humidity setpoints for critical zones (OT, ICU) on BMS
- Check BMS for active alarms — filter pressure alarms, supply temperature alarms
- Log any unusual readings

### Weekly (Mechanical Round — 30 minutes per zone)
- Visual inspection of pre-filter condition (through inspection window if available)
- Check condensate drain pan: no standing water, drain clear, no odour
- Check belt by touch/sound with AHU running (squealing = slipping; unusual vibration = alignment)
- Record motor current (clamp meter on each phase at MCC) and compare to last week
- Check plant room temperature; ensure louvres open and plant room exhaust fan running

### Monthly (30–60 minutes per AHU)
**Filters:**
- Replace pre-filter (G4) — in high-dust or high-occupancy zones, may need bi-weekly
- Clean filter frame housing (dry cloth, remove accumulated dust)

**Electrical:**
- Record three-phase currents (L1, L2, L3) with clamp meter
- Record power factor (if portable PF meter available)
- Inspect MCC panel for hot spots, discolouration, unusual odours (use thermal camera if available)

**Mechanical:**
- Check condensate drain pan and clean if necessary
- Inspect belt visually for cracking, glazing, fraying
- Check drain pump operation (if installed)
- Chemical dosing of drain pan (biocide per water treatment contractor schedule)

### Quarterly (2–4 hours per AHU) — Book with PTW
**Filters:**
- Replace bag filter (F7 or F9)
- Inspect filter frame for bypass gaps, torn seals — seal with filter tape if found
- Record pre/post filter pressure drop

**Motor:**
- Megger test: measure insulation resistance phase-to-phase and phase-to-earth
  - Test voltage: 500V DC for motors ≤ 1 kV
  - Minimum acceptable: 1 MΩ (warrants monitoring); > 10 MΩ is healthy
- Measure and record winding resistance per phase (Ω) — compare to baseline
- Lubricate bearings per manufacturer schedule (grease type and quantity as specified — do not over-grease)
- Check motor mounting bolts for tightness

**Drive:**
- Check belt tension (deflection method)
- Check pulley alignment with straight-edge
- Inspect pulleys for wear, groove damage
- Check all fasteners on fan bearing housing

**Coil:**
- Clean cooling coil fins with low-pressure compressed air (< 30 psi), blow from clean to dirty side
- Check coil fins for fin collapse (use fin comb to straighten if needed)
- Inspect coil drain pan for scale, algae — treat with biocide if present

**Capacitor bank:**
- Check for bulging, leaking, heat discolouration
- Measure capacitance of each unit (should be within ±5% of nameplate kVAR)

**Dampers:**
- Manually operate fresh air and return air damper actuators through full range
- Check actuator feedback signal matches BMS position reading
- Inspect damper blades for corrosion, damage

### Annual (4–8 hours per AHU) — Major Service, Book with PTW + Infection Control
**Filters:**
- Replace HEPA filter (H13/H14) in OT, ICU, Pharmacy, BMTU AHUs
- For HEPA replacement: wear full PPE (N95, gloves, coverall), double-bag used filters before disposal
- Conduct pressure test after HEPA installation to verify no bypass

**Coil chemical wash:**
- Chemical wash procedure:
  1. Isolate chilled water valve (closed), drain coil (open vent at top, drain at bottom)
  2. Apply alkaline degreaser (pH 10–12) to coil — spray from discharge face, let dwell 15 minutes
  3. Rinse with low-pressure water, collect runoff in drain pan
  4. Apply mild acid descaler (pH 3–5) if scale present — dwell 10 minutes
  5. Thorough rinse with clean water until neutral pH
  6. Blow dry with compressed air
  7. Open chilled water valve and check for leaks
- Note: do not use high-pressure wash (> 40 psi) — damages fins

**Electrical annual service:**
- Full VFD inspection: clean interior with dry compressed air, check terminal torque, record fault log, check/update firmware with manufacturer
- Replace motor thermal protection device per manufacturer schedule
- Motor winding resistance test (IR + winding resistance)

**Ductwork inspection:**
- Open access hatches in duct sections
- Inspect for cracks, disconnected joints (air leakage), microbial growth
- Report findings to Engineering Manager

**Commissioning verification:**
- Measure room pressure differential (for clinical zones)
- Measure actual ACH (using flow hood at supply diffusers and return grilles)
- Compare to design ACH — if > 15% short, investigate: blocked duct, incorrect fan speed, system leakage

## Triggering Corrective Maintenance from WACH Scores

| WACH Tier | Response Time | Action |
|---|---|---|
| Healthy (80–100) | Next scheduled PM | No corrective action needed |
| Monitor (60–79) | Within 2 weeks | Book inspection, identify root cause |
| Maintenance (40–59) | Within 1 week | Book corrective work order |
| Critical (0–39) — ward AHU | Within 24–48 hours | Prioritise above routine PM |
| Critical — OT/ICU/NICU AHU | Immediate | Call on-call engineer, do not wait for shift change |

## Post-Maintenance Verification

After any corrective maintenance, before handing back to operations:
1. Run AHU for minimum 15 minutes — check for unusual sounds, vibration
2. Measure and record three-phase currents → confirm within FLA
3. Note power factor reading if meter available
4. Check BMS confirms normal operation (temperatures, pressures normal)
5. Update maintenance log with: work done, parts replaced, before/after readings
6. If in clinical zone: inform Ward Manager that AHU is back in service, record in maintenance logbook
