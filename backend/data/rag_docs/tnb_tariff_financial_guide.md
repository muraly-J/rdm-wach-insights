# TNB Tariff and Financial Impact Guide

## TNB Tariff Structure — RP4 (Effective 1 July 2025)

Tenaga Nasional Berhad (TNB) overhauled its tariff structure under Regulatory Period 4 (RP4, 2025–2027). The key structural change: the old single Maximum Demand (MD) charge is replaced by two separate charges — Capacity Charge + Network Charge.

### Tariff Categories for Hospitals

Malaysian government hospitals are typically on Medium Voltage (MV) supply. Relevant tariffs:

**MV General Tariff (ex-Tariff C1 / E1)**
- Energy charge: RM 0.2983/kWh
- Capacity + Network charge: RM 89.27/kW/month
- No peak/off-peak differentiation
- Most common for hospitals without TOU metering

**MV Time-of-Use (TOU) Tariff (ex-Tariff C2 / E2)**
- Peak energy (Mon–Fri, 2 PM–10 PM): RM 0.3132/kWh
- Off-peak energy (all other times + weekends + public holidays): RM 0.2723/kWh
- Capacity + Network charge: RM 97.06/kW/month
- Available for hospitals with smart metering — allows energy shifting strategies

**High Voltage (HV) Tariff (ex-Tariff C3 / E3, 132kV and above)**
- Energy charge: RM 0.4303/kWh
- Capacity + Network charge: RM 31.21/kW/month
- Applies to very large hospital complexes with their own substation

### AFA (Automatic Fuel Adjustment)
Replaced ICPT from July 2025. Adjusted monthly by Energy Commission (ST) based on fuel prices and exchange rates. Added to or subtracted from energy charge.
- January 2026 AFA: −4.99 sen/kWh (discount)
- AFA adjusts monthly — check current month's AFA for exact billing calculations.

## Power Factor Penalty

TNB imposes a surcharge when monthly average PF falls below the minimum threshold.

**Threshold (for supplies ≤ 132kV)**: PF < 0.85
**Threshold (for supplies ≥ 132kV)**: PF < 0.90

### Penalty Formula

For PF between 0.75 and 0.85:
```
Penalty = [(0.85 − PF) / 0.01] × 1.5% × Monthly Bill
```

For PF below 0.75 (tiered — higher rate applies below 0.75):
```
Penalty = {[(0.85 − 0.75) / 0.01 × 1.5%] + [(0.75 − PF) / 0.01 × 3%]} × Monthly Bill
```

### Penalty Examples

| Monthly Average PF | Penalty Rate | On a RM 100,000 Bill |
|---|---|---|
| 0.88 | 0% | RM 0 |
| 0.85 | 0% | RM 0 (at threshold) |
| 0.84 | 1.5% | RM 1,500 |
| 0.82 | 4.5% | RM 4,500 |
| 0.78 | 10.5% | RM 10,500 |
| 0.75 | 15.0% | RM 15,000 |
| 0.72 | 24.0% | RM 24,000 |

### Fleet-Level Penalty Exposure Example

121 AHUs, MV TOU tariff (RM 0.30/kWh average), 200 kWh/day per AHU:
- Monthly fleet energy: ~726,000 kWh → bill ~RM 218,000
- If fleet average PF = 0.82 → penalty = 4.5% × RM 218,000 = **RM 9,810/month = RM 117,720/year**
- Fixing PF across 30 worst AHUs to ≥ 0.90 → eliminates this penalty

## Capacity + Network Charge Impact

The RM 89.27/kW charge (MV General) is applied to the maximum recorded demand in the billing month. Poor PF raises the apparent power (kVA) for the same useful power (kW), potentially increasing the peak demand recorded and thus the Capacity + Network charges.

Example: An AHU drawing 8 kW at PF 0.78 draws 8/0.78 = 10.26 kVA. At PF 0.92 it would draw 8.7 kVA. The difference in apparent power contributes to peak demand — particularly when many AHUs have poor PF simultaneously.

## ROI of Maintenance Actions

### Capacitor Bank Replacement (targets PF improvement)
- Typical cost per AHU: RM 2,000–5,000
- PF improvement: 0.78 → 0.90 (eliminates 10.5% penalty)
- On a RM 1,800/month bill per AHU: saves RM 189/month
- Payback: 11–27 months (from penalty savings alone, not counting reduced capacity charges and motor life extension)

### Filter Replacement (targets energy anomaly)
- G4 filter set: RM 30–80
- Bag filter set: RM 150–400
- Energy saving: 5–15% reduction in motor current if heavily blocked
- At RM 0.30/kWh and 10 kW AHU running 720 hr/month: RM 2,160/month energy cost; 10% saving = RM 216/month
- Payback: immediate (filter cost < 1 month savings)

### Coil Chemical Wash (targets energy anomaly + capacity)
- Cost: RM 500–1,500 per AHU
- Energy saving: 8–20% reduction (fouled coil forces motor to compensate)
- Payback: 1–6 months

### Motor Rewind or Replacement (targets phase imbalance + overload)
- Cost: RM 3,000–15,000 depending on kW
- Benefits: reduced phase imbalance, normal overload margin restored, often improved IE class
- Payback: 12–36 months (energy + penalty savings)

## Financial Framing of FAIR Tiers

| FAIR Tier | Score | Estimated Monthly Cost of Inaction (per AHU) |
|---|---|---|
| Healthy | 80–100 | RM 0–200 above optimal |
| Monitor | 60–79 | RM 200–800 (early PF penalty + energy drift) |
| Maintenance | 40–59 | RM 800–2,500 (PF penalty + energy + increased breakdown risk) |
| Critical | 0–39 | RM 2,500+ (full penalty + high breakdown risk + operational disruption cost) |

Note: figures are approximate per-AHU monthly estimates. A Critical AHU in OT that causes a surgical schedule cancellation adds tens of thousands in operational cost beyond the energy/penalty figures.
