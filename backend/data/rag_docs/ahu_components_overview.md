# AHU Components Overview — Hospital Grade

## What is an Air Handling Unit?

An Air Handling Unit (AHU) conditions and distributes air throughout a building zone. In a hospital, AHUs control temperature, humidity, air changes per hour, filtration grade, and room pressure — all critical for infection control and patient safety.

## Air Filtration System

**Pre-filter (G4 / EU4)**
Coarse filter capturing large dust particles. First line of defence. High pressure drop indicates blockage — replace when ΔP across filter > 80–120 Pa. Typical replacement: monthly in hospital environments.

**Bag/Pocket Filter (F7 / EU7 or F9 / EU9)**
Medium efficiency filter. F7 captures particles ≥ 1 µm (70–80% efficiency). F9 captures particles ≥ 0.4 µm (95% efficiency). Used in wards and ICU. Replace when ΔP > design value or quarterly.

**HEPA Filter (H13 / H14)**
High Efficiency Particulate Air filter. H13: ≥ 99.95% efficiency at 0.3 µm. H14: ≥ 99.995%. Used in Operating Theatres, NICU, Pharmacy cleanrooms, Bone Marrow Transplant Unit. Replace annually or per pressure drop indication. Never clean — replace only.

**Filter pressure drop monitoring**: Rising ΔP = filter loading. Blocked filters force the fan to work harder, increasing motor current and energy consumption, and can contribute to belt slip and overload faults.

## Cooling and Heating Coils

**Cooling coil (chilled water or DX)**
Removes heat and dehumidifies supply air. In Malaysian hospitals, chilled water coils are most common (connected to central chiller plant). Fouling with dust, mould, or scale reduces heat transfer — causes supply air temperature to rise, increasing energy consumption and degrading indoor conditions.

Signs of coil fouling: rising supply air temperature at same chilled water valve position, increased energy anomaly score, visible dirt/scale on fin surfaces.

Maintenance: chemical wash (alkaline degreaser + acid rinse) annually or bi-annually depending on fouling rate.

**Heating coil (hot water or electric)**
Rarely used in Malaysian hospitals for re-heating (post-dehumidification). Present in Operating Theatre AHUs for precise temperature control. Failure mode: stuck valve (overheating or no heating), open circuit element.

## Fan and Motor Assembly

**Centrifugal fan / blower**
Moves air through the AHU. Types:
- Forward-curved blades: lower efficiency, common in smaller AHUs, sensitive to system resistance changes
- Backward-curved / backward-inclined: higher efficiency, used in larger units, more stable operating curve
- SWSI (Single Width Single Inlet): one side intake
- DWDI (Double Width Double Inlet): both sides intake, higher airflow

**Fan laws**: Airflow ∝ speed; static pressure ∝ speed²; power ∝ speed³. A 10% speed reduction via VFD = ~27% power reduction.

**Motor (induction motor)**
IE (International Efficiency) classes: IE1 (standard), IE2 (high), IE3 (premium), IE4 (super premium). Hospital AHUs should be IE2 minimum; IE3 preferred for continuous-duty motors. Nameplate data: kW, voltage (V), current (A = FLA), frequency (Hz), RPM, insulation class (F = 155°C, H = 180°C), service factor (SF 1.15 = can run 15% above nameplate continuously).

Motor failure modes: winding insulation failure (thermal aging, moisture), bearing failure (lack of lubrication, misalignment), rotor bar cracking (repeated starts, overload).

**Insulation resistance test (Megger test)**:
- Good: > 10 MΩ
- Marginal: 1–10 MΩ — monitor closely
- Poor: < 1 MΩ — motor winding suspect, investigate
- Critical: < 0.5 MΩ — do not energise, wind or replace

## Variable Frequency Drive (VFD)

Controls motor speed by varying supply frequency. Benefits: energy savings at part load, soft start (reduces inrush current), PF correction capability. Drawbacks: generates harmonic currents (3rd, 5th, 7th order) that increase THD — requires line reactor or output filter to mitigate.

VFD parameters relevant to WACH monitoring:
- Output frequency (Hz): corresponds to airflow
- Output current (A): motor loading
- DC bus voltage: check when VFD trips on overvoltage
- Fault codes: OC (overcurrent), OV (overvoltage), OH (overheating), PF (power failure)

Always install line reactor (3–5% impedance) on VFD input to reduce harmonic injection and improve input PF.

## Dampers and Actuators

**Fresh Air Damper (OAD)**: controls outdoor air intake. If jammed closed — CO2 rises, indoor air quality degrades. If jammed open — excessive load in tropical climate (high humidity ingress).

**Return Air Damper (RAD)**: controls recirculated air. Must be coordinated with OAD to maintain total airflow.

**Exhaust/Relief Damper**: releases excess building pressure.

**Bypass Damper**: diverts air around cooling coil in mild weather (rarely used in tropical Malaysia).

Actuator failures: seized (thermal bonding), loss of 24V signal, control board fault. Check actuator with manual override lever; measure control signal (0–10V or 4–20mA).

## Heat Recovery and Humidity Control

**Heat recovery wheel (enthalpy wheel)**: transfers heat AND moisture from exhaust to supply air. Reduces cooling load in tropical climates. Must be cleaned annually — blocked honeycomb reduces recovery efficiency. Failure: seized bearing, torn media.

**Humidifier**: rarely needed in Malaysian hospital supply air (tropical = high ambient humidity). Present in some Pharmacy cleanrooms or Sterile Supply Units that require tight RH control.

**Drain pan**: collects condensate from cooling coil. Must slope to drain connection. Standing water = Legionella risk. Chemical dosing (biocide) required. Check monthly.

## Belt, Pulley, and Bearing System

**V-belt drive**: transfers motor torque to fan shaft. Belt tension must be checked regularly — loose belt = slipping (motor runs hot, fan speed drops, vibration). Overtight belt = premature bearing failure.

Belt alignment: checked with straight-edge along pulley faces. Misalignment causes lateral belt wear, vibration, noise.

**Bearings**: motor front and rear bearings + fan shaft bearings. Lubricate per manufacturer schedule (typically quarterly for grease-nipple type). Over-greasing is as harmful as under-greasing. Signs of bearing failure: vibration, noise (rattling, grinding), heat.

## Sensors and BMS Integration

- **Supply air temperature sensor**: should read 12–15°C off-coil for hospital AHUs in Malaysia
- **Return air temperature sensor**: confirms space temperature
- **Relative humidity sensor**: for RH-controlled zones (OT, pharmacy)
- **Differential pressure sensor across filter**: monitors filter condition
- **Duct static pressure sensor**: used for VAV systems
- **CO2 / IAQ sensor**: demand-controlled ventilation
- **Current transducers (CT)**: non-invasive motor current monitoring — used by WACH FAIR scoring

BMS (Building Management System) provides remote start/stop, setpoint control, alarm monitoring, and trend logging. WACH reads electrical data from energy meters; BMS handles mechanical controls.

## Access Panels and Casing

Leaking access panel seals cause air bypass, reducing effective airflow to the space. Thermal bridging through casing raises condensation risk. Inspect panel gaskets during quarterly PM.
