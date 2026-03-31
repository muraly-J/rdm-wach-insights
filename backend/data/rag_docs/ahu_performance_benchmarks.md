# AHU Performance Benchmarks — Malaysian Hospital Tropical Climate

These benchmarks define normal operating ranges for electrical health indicators in Malaysian hospital AHUs operating in a tropical climate (33°C / 85% RH outdoor conditions, continuous 24/7 operation). Use these to interpret WACH health scores.

## Electrical Health Benchmarks

| Parameter | Healthy | Monitor | Critical | Notes |
|---|---|---|---|---|
| Power Factor | ≥ 0.90 | 0.85–0.89 | < 0.85 | TNB penalty below 0.85 |
| Current Unbalance | < 2% | 2–5% | > 5% | NEMA MG1 action at 5% |
| THD-I (current) | < 5% | 5–8% | > 8% | IEEE 519 limit at 5% |
| Overload (vs FLA) | ≤ 100% | 100–110% | > 110% | Service factor 1.15 permits short-term 115% |

## Energy Intensity Benchmarks (by AHU class)

Operating Theatre AHU (15–25 kW motor):
- Normal daily energy: 280–420 kWh/day (running 24/7 at 70–80% load)
- Anomaly trigger: > 15% above rolling 7-day baseline

ICU/PICU AHU (7.5–15 kW motor):
- Normal daily energy: 130–240 kWh/day
- Anomaly trigger: > 15% above rolling 7-day baseline

General Ward AHU (5–11 kW motor):
- Normal daily energy: 90–180 kWh/day
- Anomaly trigger: > 20% above rolling 7-day baseline (wards have more occupancy variation)

## Motor Operating Temperature

| Condition | Temperature Rise | Status |
|---|---|---|
| Normal (IE2/IE3) | < 40°C above ambient | Healthy |
| Marginal | 40–60°C above ambient | Monitor |
| High — intervention needed | > 60°C above ambient | Critical |

Ambient in plant rooms: expect 30–40°C in Malaysian tropical climate. A motor with 60°C rise in a 38°C room = 98°C winding temperature — approaching insulation class F limit of 155°C but within safe range.

## Filter Pressure Drop Benchmarks

| Filter Type | Replace When ΔP > |
|---|---|
| Pre-filter G4 | 80–100 Pa |
| Bag filter F7 | 120–150 Pa |
| Bag filter F9 | 150–180 Pa |
| HEPA H13/H14 | 200–250 Pa (or per manufacturer) |

These are general guidelines. Actual replacement is triggered by either ΔP limit or time-based schedule (whichever comes first).

## Age-Based Degradation Expectations

AHU electrical health degrades with age even with regular maintenance:

- **0–5 years**: expect health_index 85–95 (well-maintained). PF 0.90+, THD < 5%.
- **5–10 years**: expect health_index 75–90. PF may drop to 0.87–0.89 if capacitor bank not serviced. THD slowly rises.
- **10–15 years**: expect health_index 60–80. PF degradation common. Phase imbalance events more frequent. Capacitor bank likely needs overhaul.
- **> 15 years**: variable. Motor rewinds may have been done with non-OEM wire → different resistance per phase → structural phase imbalance. WACH scores 50–75 expected even with good maintenance.

## Seasonal Variation

Malaysia has no distinct seasons, but:
- **Northeast monsoon (Nov–Feb)**: higher rainfall, slightly lower ambient temperatures (29–31°C) → minor improvement in AHU electrical health (motor runs cooler, lower latent load)
- **Dry periods (Jun–Sep)**: higher ambient temperatures (33–35°C) → higher motor temperature, slightly elevated overload risk
- **Post-Raya/holiday periods**: reduced building occupancy → AHUs may be operating well below design load → PF can temporarily improve (motors at light load with capacitor correction = risk of leading PF, but usually not severe)

## Benchmark Deviation Interpretation

**PF suddenly drops 0.05 in one reading**: likely capacitor bank fault or new inductive load added to feeder — investigate same day.

**THD gradually rises 2% over 2 weeks**: likely VFD output filter degradation or new harmonic source added — schedule inspection within 2 weeks.

**Phase imbalance spikes to 8% then returns to normal**: likely intermittent contactor contact or loose terminal — schedule inspection within 1 week.

**Energy anomaly +25% sustained for 3 days**: likely filter blockage (most common) or coil fouling — check filter ΔP immediately.

**All 5 component scores declining together**: systematic issue — check supply quality at MCC, check for building-wide load changes, check chilled water supply temperature (if CHW temp rises, AHU cooling output drops, motor works harder).
