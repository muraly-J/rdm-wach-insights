# AHU Fault Diagnosis Guide

Step-by-step decision trees for diagnosing the four primary WACH fault types. Use these procedures to systematically identify the root cause before ordering parts or scheduling corrective maintenance.

## Safety First

Before any physical inspection or measurement:
1. Inform shift supervisor and Infection Control (if in clinical zone)
2. Obtain Permit-to-Work from Engineering Department
3. Apply Lockout-Tagout (LOTO) if disconnecting power — lock the MCC incomer, hang personal padlock, test for dead with voltage tester
4. For running measurements (current, voltage): use appropriate PPE — insulated gloves, face shield, Category III rated test equipment

---

## Fault 1: Low Power Factor (pf_degradation score low)

WACH flags: `PF_CHRONIC_LOW`, or pf_degradation component score < 50

**Step 1: Confirm the reading**
- Check WACH dashboard trend: is PF consistently low, or a single-point anomaly?
- Single-point anomaly → likely sensor/reading issue; monitor for 24h
- Consistent low PF (> 24h below 0.85) → proceed

**Step 2: Check capacitor bank**
- Locate capacitor bank (usually mounted in MCC panel or separate PF correction panel)
- Visual check: bulging, leaking, burnt smell → failed capacitor → replace bank
- Use capacitance tester: measure each capacitor, should be within ±5% of nameplate kVAR
- One failed capacitor in a 3-stage bank can reduce total correction by 30–50%

**Step 3: Check VFD settings (if VFD installed)**
- Access VFD keypad → navigate to output PF or reactive power monitoring
- Check if VFD has built-in PF correction settings → enable if available
- Check for output filter installed (line reactor) — if not present, harmonic current can interact with capacitor bank

**Step 4: Check motor condition**
- Power down AHU (LOTO)
- Megger test motor windings (phase-to-phase, phase-to-earth): should read > 10 MΩ
- Low insulation resistance → winding fault → motor requires rewind or replacement
- Check motor terminal connections — tight, clean, no corrosion

**Step 5: Check for added loads**
- Review electrical panel drawings for this circuit
- Confirm no additional inductive loads (transformers, other motors) added to same feeder recently

**Action thresholds**:
- PF 0.84–0.87: service capacitor bank, book for next scheduled maintenance window
- PF < 0.83: urgent — book within 1 week, TNB penalty accumulating
- PF < 0.75: immediate intervention — double-rate penalty, motor heating risk

---

## Fault 2: High THD (thd_drift score low)

WACH flags: `THD_CHRONIC_HIGH`, or thd_drift component score < 50

**Step 1: Confirm THD source — localise**
- Measure THD-I at motor terminals (clamp meter with THD function, or power analyser)
- Measure THD-V at MCC busbar
- If THD at motor >> THD at MCC: problem is local (VFD, motor winding)
- If THD at MCC is already high: upstream source or multiple AHUs contributing

**Step 2: Check VFD harmonic mitigation**
- Is a line reactor (3–5% impedance) installed on VFD input? If not: install one
- Is an output dV/dt filter or sine filter installed? Check condition
- VFD output filters degrade over time — inspect for physical damage, overheating marks

**Step 3: Check for new loads on feeder**
- Review recent electrical work in the zone: new UPS installed? New LED driver panels? New medical imaging equipment?
- Imaging equipment (CT scanners, MRI) are major harmonic sources — confirm they are on separate feeders

**Step 4: Measure THD spectrum**
- Use power quality analyser to identify dominant harmonic orders
- 5th harmonic dominant → VFD source
- 3rd harmonic dominant → single-phase non-linear loads (lighting, computers)
- Multiple orders present → mixed sources

**Step 5: Remediation options**
- Line reactor (input): cheapest, reduces 5th/7th by 50–70%, suitable for most AHU VFDs
- Passive harmonic filter: tuned notch filter, higher cost, very effective for 5th/7th
- Active harmonic filter: expensive, suitable for large complex harmonic sources

**Action thresholds**:
- THD-I 5–8%: install/check line reactor; monitor
- THD-I > 8%: urgent — install line reactor immediately, consult electrical engineer for harmonic filter assessment

---

## Fault 3: Phase Imbalance (phase_imbalance score low)

WACH flags: `PHASE_IMBALANCE_HIGH`, or phase_imbalance component score < 50

**Step 1: Measure supply voltages at MCC incomer**
Using a calibrated multimeter:
- Measure L1–L2, L2–L3, L1–L3 (phase-to-phase)
- Calculate voltage unbalance: (max deviation from average) / average × 100%
- Voltage unbalance > 1%? → utility supply problem or major single-phase load on feeder → report to TNB / internal electrical team

**Step 2: Balanced voltages but high current imbalance → local problem**

**Step 3: Check motor terminals**
- Power down, LOTO
- Inspect L1, L2, L3 terminals at motor terminal box: tight? Corrosion? Carbon deposits?
- Retorque to motor nameplate spec
- Clean with contact cleaner

**Step 4: Check contactor**
- Power down, LOTO
- Open MCC contactor for this AHU
- Inspect each contactor contact pair: equal wear? Pitting on only one phase? Unequal contact force?
- Light pitting: file smooth
- Heavy pitting: replace contactor

**Step 5: Check for single-phase loads**
- Identify all single-phase loads tapped off the same three-phase feeder
- Measure L1, L2, L3 load individually with clamp meter
- Redistribute single-phase loads to balance phases

**Step 6: Motor winding test**
- Measure winding resistance per phase (Ohm setting, low resistance measurement)
- L1–L2, L2–L3, L1–L3 winding resistance: should match within ±5% of each other
- Significant variation → shorted turns or open winding → motor requires rewinding or replacement

**Action thresholds**:
- Current imbalance 3–5%: check terminals and contactor; book inspection within 2 weeks
- Current imbalance > 5%: urgent — NEMA MG1 motor derating threshold exceeded; book within 1 week
- One phase reading near zero: open circuit — do not run motor, immediate LOTO, investigate

---

## Fault 4: Overload (overload score low)

WACH flags: `OVERLOAD_ACTIVE`, or overload component score < 60

**Step 1: Measure actual motor current**
Clamp meter on each phase at MCC output. Compare to nameplate FLA.
- Is it uniformly high across all three phases? → mechanical overload (filter, coil, belt)
- Is it high on one phase? → combined overload + phase imbalance → check both fault trees

**Step 2: Check air filters**
- Locate pre-filter and bag filter differential pressure gauges (if installed)
- Manual check: hold torch against filter — no light penetrating = extremely blocked
- Replace filters if ΔP > threshold — this is the most common cause of AHU overload in hospitals

**Step 3: Check cooling coil condition**
- With AHU running, measure air temperature before and after cooling coil (using pocket probe thermometer at access panels)
- Normal ΔT: 8–14°C across coil
- Reduced ΔT with same chilled water valve position → fouled coil → reduced airflow → motor works harder
- Book chemical coil wash

**Step 4: Check belt and drive**
- With AHU stopped, LOTO: manually rotate fan shaft — should turn freely
- Check belt tension (deflection method: press belt midspan, should deflect ~1% of belt length under light pressure)
- Slack belt = slipping → motor draws more current to maintain speed → overload
- Check belt for cracking, glazing (shiny surface = slipping)

**Step 5: Check ambient temperature**
- Measure plant room temperature
- Motor nameplate is rated at 40°C ambient (standard)
- If plant room > 45°C: motor needs derating by ~5–10% → effectively reduces overload threshold
- Check plant room ventilation — blocked louvres, failed ventilation fan?

**Step 6: Check VFD frequency setting**
- If VFD installed: confirm set frequency matches design (e.g., 48 Hz for reduced speed)
- If VFD set to 60 Hz on a 50 Hz motor design: motor overspeeds → overload

**Action thresholds**:
- Current 100–110% FLA: inspect filters and belt; book maintenance within 2 weeks
- Current > 110% FLA: urgent — overload relay may trip; filters/belt check same day
- Thermal relay has tripped and reset: investigation required before re-energising

---

## Energy Anomaly (energy_anomaly score low)

Not a direct electrical fault but an early warning of mechanical or electrical degradation.

**Step 1: Is it a sudden spike or gradual drift?**
- Sudden spike: mechanical fault (seized damper, belt break, bearing seizure) → immediate inspection
- Gradual rise over days/weeks: filter blockage (most common), coil fouling, refrigerant undercharge → scheduled inspection

**Step 2: Compare timing**
- Does anomaly correlate with a specific time of day? → occupancy change, specific equipment turning on
- Always high regardless of time? → persistent mechanical issue
- High on certain days? → check for related building events (maintenance shutdown of chilled water, power outages)

**Step 3: Cross-check with other scores**
- Energy anomaly high + overload high: filter or coil problem (mechanical load increase)
- Energy anomaly high + PF degrading: capacitor bank issue (more reactive current drawn)
- Energy anomaly high alone: early mechanical issue — inspect AHU before other scores degrade
