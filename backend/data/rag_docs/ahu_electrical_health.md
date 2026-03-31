# AHU Electrical Health Indicators

WACH monitors five electrical health indicators for each AHU. Together they form the FAIR health score (0–100). This document explains each indicator: what it measures, what causes it to degrade, what the thresholds mean, and why it matters.

## 1. Power Factor (PF)

**What it is**: Power Factor = Active Power (kW) ÷ Apparent Power (kVA). Ranges 0–1 (or 0–100%). A PF of 1.0 means all electrical power drawn is being converted to useful work. A PF of 0.75 means 25% of the current drawn is reactive — it does no useful work but still flows through cables, transformers, and switchgear.

**Why it matters**: Low PF means:
- Higher current for the same useful power → cable heating → accelerated insulation aging
- Higher kVA demand → larger TNB capacity + network charges
- TNB PF penalty surcharge (below 0.85 for supplies ≤ 132kV)
- Motor operates less efficiently → more heat generated

**Target**: ≥ 0.90 for hospital AHUs

**TNB threshold**: < 0.85 = penalty. Penalty = [(0.85 − PF)/0.01] × 1.5% of bill (for PF 0.75–0.85). Below 0.75: doubles to 3%/0.01.

**What causes low PF**:
- Induction motors running at part load (most common in hospitals — AHUs often oversized or running at reduced speed)
- Missing or undersized capacitor bank
- VFD not set to PF correction mode
- Failed capacitor bank (open-circuited capacitors)
- Addition of uncompensated inductive loads on same feeder

**How to correct**:
1. Inspect capacitor bank — test capacitance (should be within 5% of nameplate kVAR)
2. Check VFD PF settings
3. Install additional capacitors (fixed or automatic PF correction panel)
4. Check for open-circuited capacitors (one blown capacitor in a bank significantly reduces total correction)

## 2. Total Harmonic Distortion (THD)

**What it is**: THD measures the presence of harmonic currents (integer multiples of the fundamental 50 Hz frequency) as a percentage of the fundamental. THD-I = current THD; THD-V = voltage THD.

Common harmonic orders in AHU circuits:
- 5th harmonic (250 Hz): dominant in VFD-driven motors
- 7th harmonic (350 Hz): secondary VFD harmonic
- 3rd harmonic (150 Hz): from single-phase non-linear loads (lighting, UPS) on the same feeder

**Why it matters**:
- Harmonic currents cause additional heating in motor windings (I²R losses at higher frequencies)
- Reduces transformer efficiency and can cause transformer overheating
- Causes neutral conductor overloading (3rd harmonic circulates in neutral)
- Contributes to capacitor bank overloading and failure
- Can cause nuisance tripping of protective relays
- Degrades motor insulation lifespan

**Limits**: IEEE 519-2022 specifies THD-I < 5% at the point of common coupling (PCC) for most hospital supply systems.

**What causes high THD**:
- VFD without line reactor or harmonic filter (most common cause in hospital AHUs)
- Multiple VFDs on the same feeder without harmonic mitigation
- UPS systems (often in hospitals near critical equipment)
- Electronic ballasts, LED driver power supplies on the same circuits

**How to address**:
1. Install 3–5% impedance line reactor on VFD input (inexpensive, effective for 5th/7th harmonics)
2. Install passive harmonic filter (tuned to 5th/7th) for more severe cases
3. Separate VFD circuits from sensitive loads where possible
4. Measure THD at motor terminals vs. at MCC — if much higher at MCC, source is upstream

## 3. Phase Imbalance (Current Unbalance)

**What it is**: In a balanced three-phase system, currents in L1, L2, L3 are equal and 120° apart. Phase imbalance (current unbalance) is the maximum deviation from the average, expressed as a percentage.

NEMA MG1 standard: a 1% voltage unbalance causes approximately 6–10% current unbalance. Current unbalance > 5% requires motor derating.

**Why it matters**:
- Unequal currents produce unequal heating in motor windings → hot spots → accelerated insulation failure
- Negative sequence currents produce a counter-rotating magnetic field → braking torque → motor heats up further, runs less efficiently
- Reduces motor life significantly (each 10°C rise in winding temperature halves insulation life — Arrhenius rule)
- Can cause premature bearing failure due to shaft currents

**Target**: < 2% current unbalance

**What causes phase imbalance**:
- Unequal single-phase loads on the same three-phase feeder (most common in hospitals — medical equipment, lighting, sockets on different phases)
- Loose terminal connections at motor, contactor, or MCC (introduces resistance asymmetry)
- Blown fuse or open contact on one phase
- Deteriorated contactor contacts (unequal contact resistance)
- Motor winding fault (shorted turns in one phase)

**How to diagnose**:
1. Measure line voltages at MCC input: L1–L2, L2–L3, L1–L3. Voltage unbalance > 1%? → utility or supply problem
2. Balanced voltages but unbalanced currents → motor terminal or winding issue
3. Check contactor contacts visually — pitting, arcing marks
4. Measure each phase current with clamp meter — identify which phase is high or low
5. If one phase reads near-zero → open circuit (fuse, contactor contact, cable break)

## 4. THD Drift (thd_drift score)

In WACH, the `thd_drift` score tracks how much the THD has increased from the AHU's own baseline (not just whether it exceeds a fixed limit). A gradual drift upward over days or weeks often indicates a failing capacitor bank, deteriorating VFD filter, or new harmonic sources being added to the circuit.

Sudden THD spikes suggest load changes or equipment faults. Chronic upward drift suggests systematic degradation.

## 5. Overload (Overcurrent)

**What it is**: Overload occurs when the motor draws current above its Full Load Amperes (FLA) nameplate rating. WACH tracks whether measured current exceeds a calculated threshold based on the motor's rated current.

**Why it matters**:
- Thermal damage to motor windings (overtemperature)
- Trips thermal overload relay → unexpected AHU shutdown
- In hospital zones, unplanned AHU shutdown risks patient safety (OT, ICU, NICU)
- Frequent overload trips → motor insulation degradation → shorter motor life

**Causes of overload**:
- Clogged air filters (increased system resistance → fan works harder → motor draws more current)
- Fouled cooling coil (reduced airflow through the AHU)
- Belt slipping or misaligned (fan speed drops, motor compensates)
- VFD set to incorrect frequency (overspeeding motor)
- High ambient temperature in plant room (reduces motor cooling efficiency)
- Mechanical fault (seized bearing, jammed damper)

**How to address**:
1. Check filter ΔP — high ΔP → replace filters immediately
2. Check coil condition (visual, ΔT across coil)
3. Check belt tension and alignment
4. Measure motor terminal voltage (undervoltage causes overcurrent)
5. Check plant room temperature

## Relationship Between Indicators

Poor PF → higher currents → more heating → may trigger overload relay
High THD → additional copper losses → contributes to apparent overload
Phase imbalance → hot winding → accelerated insulation degradation → eventual motor failure
Energy anomaly often precedes and correlates with all of the above — it is the earliest warning signal.

WACH's FAIR scoring weights these to prioritise the most financially significant indicators (PF and phase imbalance at 25% weight each).
