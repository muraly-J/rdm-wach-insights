# WACH Data Inventory — One-Stop Reference

_Generated: 2026-05-29 03:18 UTC by `scripts/research/build_data_inventory.py`._

Single source of truth for **what data exists for WACH**, per device, across the two
disconnected systems: **EMS** (electrical power meters) and **BMS** (HVAC/BACnet controls).

## 1. Data Sources

| System | What | Host | Bucket | Measurement | Schema |
|---|---|---|---|---|---|
| **EMS** | Electrical power-meter telemetry (46 metrics) | `178.128.53.199:8086` (public) | `wach_bucket_3` | per-metric | wide |
| **BMS** | HVAC/BACnet control points | `172.17.84.201:8086` (private LAN) | `wach_temp` | `bacnet_points` | long (`item` tag + `value`) |

> EMS hot/processed layer lives locally in DuckDB (`backend/data/healthdb.duckdb` + archive `data/healthdb.duckdb`).
> BMS is queried live from Influx. The two systems use **different device-ID schemes** and **different time spans** — see §2 and the caveats in §6.

## 2. Coverage Summary

| | EMS (electrical) | BMS (HVAC) |
|---|---|---|
| Devices with data | 121 | 146 |
| Earliest timestamp | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC |
| Latest timestamp | 2026-05-25 08:00 UTC | 2026-05-29 03:16 UTC |
| Metrics per device | up to 46 (uniform) | varies (≈30–40, per AHU type) |

- TSV mapping rows: **171**  ·  unique device labels: **152**
- Devices matched **both** EMS and BMS (via label↔name join): **112**
- BMS AHU items that could not be parsed into device+point: **6**

## 3. Per-Device Inventory

Columns: device_id (EMS) · BMS device name · level/dept · EMS start · BMS start · #EMS metrics · #BMS points.
`—` = not present in that system. See §4/§5 for the metric/point lists.

| device_id | BMS name | Level | Dept | EMS start | BMS start | EMS metrics | BMS points |
|---|---|---|---|---|---|---:|---:|
| e0101 | AHU_L1_ES_01 | L01 | Enginering Services | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 1 |
| e0102 | AHU_L1_BES_01 | L01 | Biomedical Engineering Services Unit | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0103 | AHU_L1_MO_01 | L01 | Mortuary Services | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0104 | AHU_L1_HS_01 | L01 | Housekeeping Services | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0105 | AHU_L1_CA_02 | L01 | Catering & Dietitics Department | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0106 | AHU_L1_CA_01 | L01 | Catering & Dietitics Department | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0107 | AHU_L1_MS_02 | L01 | Medical Store | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 30 |
| e0108 | AHU_L1_MS_01 | L01 | Medical Store | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 30 |
| e0109 | — | L01 | Security Services | 2025-10-30 08:00 UTC | — | 46 | — |
| e0110 | AHU_L1_PAC_01 | L01 | Emergency Department | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0111 | AHU_AHU_L1_OSCC_01 | L01 | Emergency Department | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0112 | AHU_L1_ED_03 | L01 | Emergency Department | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0113 | AHU_L1_ED_04 | L01 | Emergency Department | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0114 | AHU_L1_ED_02 | L01 | Emergency Department | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0115 | AHU_L1_ID_04 | L01 | Imaging Department | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0116 | AHU_L1_ED_01 | L01 | Emergency Department | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0117 | AHU_L1_SF_01 | L01 | Shared Facilities 1 | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0118 | AHU_L1_ID_03 | L01 | Imaging Department | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0120 | AHU_L1_ID_02 | L01 | Imaging Department | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0121 | AHU_L1_ID_01 | L01 | Imaging Department | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 30 |
| e0201 | AHU_L2_CDC_03 | L02 | Child Development Centre | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 34 |
| e0202 | AHU_L2_CDC_01 | L02 | Child Development Centre | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 34 |
| e0203 | AHU_L2_CDC_04 | L02 | Child Development Centre | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 34 |
| e0204 | AHU_L2_CDC_02 | L02 | Child Development Centre | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 34 |
| e0205 | AHU_L2_CDC_05 | L02 | Child Development Centre | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 34 |
| e0206 | AHU_L2_CF_01 | L02 | Cafeteria | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0207 | AHU_L2_MSS_01 | L02 | Medical Social Services | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0208 | AHU_L2_OP_01 | L02 | Outpatient Pharmacy | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 28 |
| e0209 | AHU_L2_AR_01 | L02 | Admission Revenue | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0210 | AHU_L3_PGMC_02 | L03 | Post Graduate Medical Centre and Continuous Medical Education | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0211 | AHU_L3_PGMC_01 | L03 | Post Graduate Medical Centre and Continuous Medical Education | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0212 | AHU_L1_OT_01 | L01 | Emergency Department | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 38 |
| e0213 | AHU_L2_WHU_01 | L02 | Women Health Unit | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 29 |
| e0214 | AHU_L2_WHU_02 | L02 | Women Health Unit | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 29 |
| e0215 | AHU_L2_SPG_04 | L02 | O&G Specialist Clinic | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 31 |
| e0216 | AHU_L2_SPG_03 | L02 | O&G Specialist Clinic | 2025-11-05 06:00 UTC | 2026-02-19 07:13 UTC | 46 | 30 |
| e0217 | AHU_L2_SPG_02 | L02 | O&G Specialist Clinic | 2025-11-05 06:00 UTC | 2026-02-24 07:14 UTC | 46 | 24 |
| e0218 | AHU_L2_SPG_01 | L02 | O&G Specialist Clinic | 2025-11-05 06:00 UTC | 2026-02-24 07:14 UTC | 46 | 31 |
| e0301 | — | L03 | Pathology Department | 2025-11-05 06:00 UTC | — | 46 | — |
| e0303 | — | L03 | Pathology Department | 2025-11-05 06:00 UTC | — | 46 | — |
| e0304 | — | L03 | RQA Unit | 2025-11-10 07:00 UTC | — | 46 | — |
| e0306 | AHU_L3_SPD_02 | L03 | Dental Clinic | 2025-11-10 07:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0307 | AHU_L3_SF_01 | L03 | Shared Facilities 3 | 2025-11-10 07:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0308 | AHU_L3_SPP_03 | L03 | Paediatric Specialist Clinic | 2025-11-10 07:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0311 | AHU_L3_SPP_01 | L03 | Paediatric Specialist Clinic | 2025-11-10 07:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0312 | AHU_L3_SPP_02 | L03 | Paediatric Specialist Clinic | 2025-11-10 07:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0313 | AHU_L3_SPD_01 | L03 | Dental Clinic | 2025-11-10 07:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0314 | AHU_L3_CPC_01 | L03 | Paediatric Specialist Clinic | 2025-11-10 07:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0315 | AHU_L3_SPD_03 | L03 | Dental Clinic | 2025-11-10 07:00 UTC | 2026-02-19 07:13 UTC | 46 | 29 |
| e0401 | AHU_L3_PT_02 | L03 | Pathology Department | 2025-11-10 07:00 UTC | 2026-02-19 07:13 UTC | 46 | 30 |
| e0402 | AHU_L3_PT_01 | L03 | Pathology Department | 2025-11-10 07:00 UTC | 2026-02-19 07:13 UTC | 46 | 30 |
| e0403 | AHU_L4_MK_01 | L04 | Milk Preparation 1 | 2025-11-10 07:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0404 | AHU_L4_PD_01 | L04 | Inpatient Pharmacy Department | 2025-11-10 07:00 UTC | 2026-02-19 07:13 UTC | 46 | 30 |
| e0406 | — | L04 | Inpatient Pharmacy Department | 2025-12-31 01:00 UTC | — | 46 | — |
| e0406 | — | L04 | Inpatient Pharmacy Department | 2025-12-31 01:00 UTC | — | 46 | — |
| e0407 | AHU_L4_PD_02 | L04 | Inpatient Pharmacy Department | 2025-11-29 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 28 |
| e0408 | AHU_L4_SCT_03 | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | 2025-11-29 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0409 | AHU_L4_SCT_01 | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | 2025-11-29 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 21 |
| e0411 | — | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | 2025-11-29 08:00 UTC | — | 46 | — |
| e0412 | AHU_L4_OHR_01 | L04 | Obstetric High Risk Unit | 2025-11-29 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 31 |
| e0413 | AHU_L4_MOT_04 | L04 | Maternity OT | 2025-11-29 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 32 |
| e0414 | AHU_L4_MOT_02 | L04 | Maternity OT | 2025-12-31 01:00 UTC | 2026-02-19 07:13 UTC | 46 | 35 |
| e0415 | AHU_L4_MOT_03 | L04 | Maternity OT | 2025-12-31 01:00 UTC | 2026-02-19 07:13 UTC | 46 | 29 |
| e0416 | AHU_L4_MOT_01 | L04 | Maternity OT | 2025-12-31 01:00 UTC | 2026-02-19 07:13 UTC | 46 | 36 |
| e0419 | AHU_L4_SF_01 | L04 | Shared Facilities 4 | 2025-12-31 01:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0423 | AHU_L3_BL_01 | L03 | Biophysiological Department | 2025-12-31 01:00 UTC | 2026-02-19 07:13 UTC | 46 | 27 |
| e0501 | AHU_L5_PICU_02 | L05 | Paediatric Intensive Care Unit | 2025-11-29 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0502 | AHU_L5_PHDU_01 | L05 | Paediatric High Dependency Unit (DWP) | 2025-11-29 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0503 | AHU_L5_AD_01 | L05 | Anaesthesiology Department | 2025-11-29 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0504 | AHU_L5_RHU_01 | L05 | Respiratory and Haemodynamic Unit | 2025-11-29 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0505 | AHU_L5_AICU_02 | L05 | Adult Intensive Care Unit | 2025-11-29 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0506 | AHU_L5_AHDU_01 | L05 | Adult High Dependency Unit (DWA) | 2025-11-29 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0507 | — | L05 | Adult Intensive Care Unit | 2025-11-29 08:00 UTC | — | 46 | — |
| e0508 | — | L05 | Shared Facilities 5 | 2025-11-29 08:00 UTC | — | 46 | — |
| e0509 | AHU_L5_PBU_02 | L05 | Paediatric Burn Unit | 2025-11-29 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0510 | AHU_L5_PICU_01 | L05 | Paediatric Intensive Care Unit | 2025-11-29 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0511 | AHU_L5_PBU_01 | L05 | Paediatric Burn Unit | 2025-11-29 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 21 |
| e0602 | — | L06 | Library | 2025-10-30 09:00 UTC | — | 46 | — |
| e0603 | — | L06 | Administration Unit | 2025-10-30 09:00 UTC | — | 46 | — |
| e0604 | — | L06 | Administration Unit | 2025-10-30 09:00 UTC | — | 46 | — |
| e0605 | — | L06 | Central Sterile Supply Unit | 2025-10-30 09:00 UTC | — | 46 | — |
| e0606 | — | L06 | Central Sterile Supply Unit | 2025-10-30 08:00 UTC | — | 46 | — |
| e0607 | AHU_L6_SOC_01 | L06 | Specialist Office Complex | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 31 |
| e0611 | AHU_L6_IT_01 | L06 | Information Technology Department | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0622 | AHU_L5_OT_10 | L05 | Main Operation Theatre Complex | 2025-10-30 08:00 UTC | 2026-02-19 07:13 UTC | 46 | 26 |
| e0625 | — | L06 | Medical Record | 2025-10-30 08:00 UTC | — | 46 | — |
| e0626 | AHU_L6_SF_01 | L06 | Shared Facilities 6 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0627 | AHU_L6_SOC_02 | L06 | Specialist Office Complex | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 31 |
| e0628 | AHU_L6_CSSD_03 | L06 | Central Sterile Supply Unit | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0701 | AHU_L7_OB3_01 | L07 | Inpatient Wards - Obstetric 3 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 11 |
| e0702 | AHU_L7_OB4_01 | L07 | Inpatient Wards - Obstetric 4 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 29 |
| e0703 | AHU_L7_OB1_01 | L07 | Inpatient Wards - Obstetric 1 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 37 |
| e0704 | AHU_L7_OB2_01 | L07 | Inpatient Wards - Obstetric 2 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0801 | AHU_L8_CW_02 | L08 | 1st Class Ward | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 31 |
| e0802 | AHU_L8_CW_01 | L08 | 1st Class Ward | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 31 |
| e0803 | AHU_L8_OCC_01 | L08 | On Call Complex | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0804 | AHU_L8_GY1_01 | L08 | Inpatient Wards - Gynaecology 1 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0805 | AHU_L8_GY2_01 | L08 | Inpatient Wards - Gynaecology 2 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0901 | AHU_L9_NP_01 | L09 | Nephrology/ Dialysis Ward and Renal Treatment Centre | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0902 | AHU_L9_NP_02 | L09 | Nephrology/ Dialysis Ward and Renal Treatment Centre | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0903 | AHU_L9_PM5_01 | L09 | Inpatient Wards - Paediatric Medical Ward 5 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 25 |
| e0904 | AHU_L9_PM5_02 | L09 | Inpatient Wards - Paediatric Medical Ward 5 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 33 |
| e0905 | AHU_L9_NW1_01 | L09 | Neonatology Wards 1 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0906 | AHU_L9_NW1_02 | L09 | Neonatology Wards 1 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0907 | AHU_L9_NW2_02 | L09 | Neonatology Wards 2 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e0908 | AHU_L9_NW2_01 | L09 | Neonatology Wards 2 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e1001 | AHU_L10_PM1_02 | L10 | Inpatient Wards - Paediatric Medical Ward 1 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 35 |
| e1002 | AHU_L10_PM1_01 | L10 | Inpatient Wards - Paediatric Medical Ward 1 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 35 |
| e1003 | AHU_L10_PM3_01 | L10 | Inpatient Wards - Paediatric Medical Ward 3 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 31 |
| e1004 | AHU_L10_PM3_02 | L10 | Inpatient Wards - Paediatric Medical Ward 3 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 31 |
| e1005 | AHU_L10_PM4_02 | L10 | Inpatient Wards - Paediatric Medical Ward 4 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 35 |
| e1006 | AHU_L10_PM4_01 | L10 | Inpatient Wards - Paediatric Medical Ward 4 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 35 |
| e1007 | AHU_L10_PM2_01 | L10 | Inpatient Wards - Paediatric Medical Ward 2 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 31 |
| e1008 | AHU_L10_PM2_02 | L10 | Inpatient Wards - Paediatric Medical Ward 2 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 27 |
| e1101 | AHU_L11_PS1_02 | L11 | Inpatient Wards - Paediatric Surgical Ward 1 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 2 |
| e1102 | AHU_L11_PS1_01 | L11 | Inpatient Wards - Paediatric Surgical Ward 1 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 32 |
| e1103 | AHU_L11_PS2_01 | L11 | Inpatient Wards - Paediatric Surgical Ward 2 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 31 |
| e1104 | AHU_L11_PS2_02 | L11 | Inpatient Wards - Paediatric Surgical Ward 2 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 31 |
| e1105 | AHU_L11_PS4_02 | L11 | Inpatient Wards - Paediatric Surgical Ward 4 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 31 |
| e1106 | AHU_L11_PS4_01 | L11 | Inpatient Wards - Paediatric Surgical Ward 4 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 31 |
| e1107 | AHU_L11_PS3_01 | L11 | Inpatient Wards - Paediatric Surgical Ward 3 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 31 |
| e1108 | AHU_L11_PS3_02 | L11 | Inpatient Wards - Paediatric Surgical Ward 3 | 2025-10-30 08:00 UTC | 2026-02-24 07:14 UTC | 46 | 26 |
| **(no id)** | AHU_L1_CN_01 | L01 | Creche/ Nursery | — | 2026-02-19 07:13 UTC | — | 27 |
| **(no id)** | AHU_L1_SST_01 | — | — | — | 2026-02-19 07:13 UTC | — | 21 |
| **(no id)** | — | L02 | ART Centre | — | — | — | — |
| **(no id)** | — | L02 | ART Centre | — | — | — | — |
| **(no id)** | — | L02 | ART Centre | — | — | — | — |
| **(no id)** | — | L02 | ART Centre | — | — | — | — |
| **(no id)** | AHU_L2_ART_01 | — | — | — | 2026-02-19 07:13 UTC | — | 27 |
| **(no id)** | AHU_L2_ART_02 | — | — | — | 2026-02-19 07:13 UTC | — | 27 |
| **(no id)** | AHU_L2_ART_03 | — | — | — | 2026-02-19 07:13 UTC | — | 32 |
| **(no id)** | AHU_L2_OP_01_01 | — | — | — | 2026-02-19 07:13 UTC | — | 2 |
| **(no id)** | AHU_L3_EOA_01 | L03 | Paediatric Specialist Clinic | — | 2026-02-19 07:13 UTC | — | 27 |
| **(no id)** | AHU_L3_EOA_02 | L03 | Paediatric Specialist Clinic | — | 2026-02-19 07:13 UTC | — | 27 |
| **(no id)** | AHU_L3_GL_01 | L03 | Genetic Department | — | 2026-02-19 07:13 UTC | — | 30 |
| **(no id)** | AHU_L3_GL_02 | L03 | Genetic Department | — | 2026-02-19 07:13 UTC | — | 30 |
| **(no id)** | AHU_L3_PT_03 | — | — | — | 2026-02-19 07:13 UTC | — | 30 |
| **(no id)** | AHU_L3_PT_04 | — | — | — | 2026-02-19 07:13 UTC | — | 27 |
| **(no id)** | AHU_L3_RQAHEU_01 | — | — | — | 2026-02-19 07:13 UTC | — | 27 |
| **(no id)** | AHU_L4_CDR_01 | — | — | — | 2026-02-19 07:13 UTC | — | 25 |
| **(no id)** | AHU_L4_CDR_02 | — | — | — | 2026-02-19 07:13 UTC | — | 25 |
| **(no id)** | AHU_L4_LD_01 | — | — | — | 2026-02-19 07:13 UTC | — | 27 |
| **(no id)** | AHU_L4_LD_02 | — | — | — | 2026-02-19 07:13 UTC | — | 27 |
| **(no id)** | AHU_L4_LD_03 | — | — | — | 2026-02-19 07:13 UTC | — | 27 |
| **(no id)** | — | L04 | Labour and Delivery Unit | — | — | — | — |
| **(no id)** | — | L04 | Labour and Delivery Unit | — | — | — | — |
| **(no id)** | — | L04 | Labour and Delivery Unit | — | — | — | — |
| **(no id)** | — | L04 | Neonatal Intensive Care Unit | — | — | — | — |
| **(no id)** | — | L04 | Neonatal Intensive Care Unit | — | — | — | — |
| **(no id)** | AHU_L4_NICU_01 | — | — | — | 2026-02-19 07:13 UTC | — | 31 |
| **(no id)** | AHU_L4_NICU_02 | — | — | — | 2026-02-19 07:13 UTC | — | 31 |
| **(no id)** | AHU_L4_NONSTERILE_01 | — | — | — | 2026-02-19 07:13 UTC | — | 25 |
| **(no id)** | — | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | — | — | — | — |
| **(no id)** | — | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | — | — | — | — |
| **(no id)** | — | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | — | — | — | — |
| **(no id)** | — | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | — | — | — | — |
| **(no id)** | — | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | — | — | — | — |
| **(no id)** | — | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | — | — | — | — |
| **(no id)** | — | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | — | — | — | — |
| **(no id)** | — | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | — | — | — | — |
| **(no id)** | — | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | — | — | — | — |
| **(no id)** | — | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | — | — | — | — |
| **(no id)** | — | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | — | — | — | — |
| **(no id)** | — | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | — | — | — | — |
| **(no id)** | — | L04 | Bone Marrow Transplant Unit (Stem Cell Transplant) | — | — | — | — |
| **(no id)** | AHU_L4_TPN_01 | — | — | — | 2026-02-19 07:13 UTC | — | 25 |
| **(no id)** | AHU_L5_OT_01 | — | — | — | 2026-02-19 07:13 UTC | — | 26 |
| **(no id)** | AHU_L5_OT_02 | — | — | — | 2026-02-19 07:13 UTC | — | 26 |
| **(no id)** | AHU_L5_OT_03 | — | — | — | 2026-02-19 07:13 UTC | — | 67 |
| **(no id)** | AHU_L5_OT_04 | — | — | — | 2026-02-19 07:13 UTC | — | 67 |
| **(no id)** | AHU_L5_OT_05 | — | — | — | 2026-02-19 07:13 UTC | — | 67 |
| **(no id)** | AHU_L5_OT_06 | — | — | — | 2026-02-19 07:13 UTC | — | 67 |
| **(no id)** | AHU_L5_OT_07 | — | — | — | 2026-02-19 07:13 UTC | — | 66 |
| **(no id)** | AHU_L5_OT_08 | — | — | — | 2026-02-19 07:13 UTC | — | 67 |
| **(no id)** | AHU_L5_OT_09 | — | — | — | 2026-02-19 07:13 UTC | — | 67 |
| **(no id)** | AHU_L5_OT_11 | — | — | — | 2026-02-19 07:13 UTC | — | 26 |
| **(no id)** | AHU_L5_OT_12 | — | — | — | 2026-02-19 07:13 UTC | — | 26 |
| **(no id)** | AHU_L5_OT_13 | — | — | — | 2026-02-19 07:13 UTC | — | 67 |
| **(no id)** | AHU_L5_OT_15 | — | — | — | 2026-02-24 07:14 UTC | — | 27 |
| **(no id)** | AHU_L5_OT_16 | — | — | — | 2026-02-24 07:14 UTC | — | 27 |
| **(no id)** | AHU_L5_OT_17 | — | — | — | 2026-02-24 07:14 UTC | — | 27 |
| **(no id)** | AHU_L5_SF_01 | — | — | — | 2026-02-24 07:14 UTC | — | 27 |
| **(no id)** | — | L05 | Main Operation Theatre Complex | — | — | — | — |
| **(no id)** | AHU_L6_SOC_03 | — | — | — | 2026-02-24 07:14 UTC | — | 1 |
| **(no id)** | — | L04 | Inpatient Pharmacy Department | — | — | — | — |
| **(no id)** | — | L04 | Inpatient Pharmacy Department | — | — | — | — |

## 4. EMS Metric Catalog (46 electrical metrics)

Uniform across all EMS devices. Source bucket `wach_bucket_3`, hourly in the hot layer.

- `power_total`
- `power_l1`
- `power_l2`
- `power_l3`
- `power_demand`
- `max_power_demand`
- `apparent_power_total`
- `apparent_power_l1`
- `apparent_power_l2`
- `apparent_power_l3`
- `apparent_power_demand`
- `reactive_power_total`
- `reactive_power_l1`
- `reactive_power_l2`
- `reactive_power_l3`
- `reactive_power_demand`
- `energy_import`
- `energy_export`
- `reactive_energy_import`
- `reactive_energy_export`
- `apparent_energy`
- `current_avg`
- `current_l1`
- `current_l2`
- `current_l3`
- `current_l1_thd`
- `current_l3_thd`
- `volts_l_n_avg`
- `volts_l_l_avg`
- `volts_l1_n`
- `volts_l2_n`
- `volts_l3_n`
- `volts_l1_l2`
- `volts_l2_l3`
- `volts_l3_l1`
- `volts_l1_thd`
- `volts_l2_thd`
- `volts_l3_thd`
- `power_factor_avg`
- `power_factor_l1`
- `power_factor_l2`
- `power_factor_l3`
- `freq`
- `current_unbalance`
- `volts_unbalance`
- `digital_input_1_and_2`

> Derived/engineered columns also stored in the health layer (not raw EMS):
> `composite_thd`, `nema_voltage_imbalance`, `p95_current`, `hourly_delta`, `predicted_delta`, `energy_anomaly_raw`.

## 5. BMS Point Glossary (observed point-type suffixes)

| Point | Meaning | Observed in data |
|---|---|---|
| `AFR` | _(undocumented)_ | ✅ |
| `AM` | Auto/Manual selection status (binary) | ✅ |
| `AlmEnaDly` | Alarm enable delay (sec) | ✅ |
| `CO2` | CO2 level (ppm) | ✅ |
| `CO21` | _(undocumented)_ | ✅ |
| `CO2SP` | CO2 setpoint (ppm) | ✅ |
| `CO2SP1` | _(undocumented)_ | ✅ |
| `CO2Sp` | _(undocumented)_ | ✅ |
| `CO2_FaDmprMin` | _(undocumented)_ | ✅ |
| `CO2_I` | CO2 PID integral term | ✅ |
| `CO2_I1` | _(undocumented)_ | ✅ |
| `CO2_P` | CO2 PID proportional term | ✅ |
| `CO2_P1` | _(undocumented)_ | ✅ |
| `Clg_I` | Cooling PID integral term | ✅ |
| `Clg_P` | Cooling PID proportional term | ✅ |
| `DP` | Differential pressure (Pa) | ✅ |
| `DPDisplay` | _(undocumented)_ | ✅ |
| `DPOff` | _(undocumented)_ | ✅ |
| `DPSh` | _(undocumented)_ | ✅ |
| `DSP` | Duct static pressure (Pa) | ✅ |
| `DSPAV` | _(undocumented)_ | ✅ |
| `DSPNew` | Duct static pressure (alt point) (Pa) | ✅ |
| `DSPNewSh` | _(undocumented)_ | ✅ |
| `DSPSH` | _(undocumented)_ | ✅ |
| `DSPSP` | Duct static pressure setpoint (Pa) | ✅ |
| `DSPSp` | _(undocumented)_ | ✅ |
| `DefaultRATSp` | Default RAT setpoint (°C) | ✅ |
| `DefaultRATsp` | _(undocumented)_ | ✅ |
| `EFSS` | _(undocumented)_ | ✅ |
| `EFST` | _(undocumented)_ | ✅ |
| `EFTR` | _(undocumented)_ | ✅ |
| `FADMPR` | _(undocumented)_ | ✅ |
| `FADmprMin` | _(undocumented)_ | ✅ |
| `FAN1RunTime` | _(undocumented)_ | ✅ |
| `FAN1SS` | _(undocumented)_ | ✅ |
| `FAN1VSD` | _(undocumented)_ | ✅ |
| `FAN2RunTime` | _(undocumented)_ | ✅ |
| `FAN2SS` | _(undocumented)_ | ✅ |
| `FAN2ST` | _(undocumented)_ | ✅ |
| `FAN2TR` | _(undocumented)_ | ✅ |
| `FAN2VSD` | _(undocumented)_ | ✅ |
| `FLTR` | Air filter status/alarm (binary) | ✅ |
| `FaDmpr` | Fresh air damper position (%) | ✅ |
| `FaDmpr1` | _(undocumented)_ | ✅ |
| `FaDmprMin` | Fresh air damper minimum position (%) | ✅ |
| `FaDmprMin1` | _(undocumented)_ | ✅ |
| `FailDly` | Failure delay (sec) | ✅ |
| `HEATPerc` | _(undocumented)_ | ✅ |
| `HEATperc` | _(undocumented)_ | ✅ |
| `HICMD` | _(undocumented)_ | ✅ |
| `HRWSS` | _(undocumented)_ | ✅ |
| `HRWST` | _(undocumented)_ | ✅ |
| `HRWTR` | _(undocumented)_ | ✅ |
| `HWRTNEW` | _(undocumented)_ | ✅ |
| `HWS` | Hot water supply status/temp | ✅ |
| `HWST` | Hot water supply temperature (°C) | ✅ |
| `HWVLV` | Hot water valve position (%) | ✅ |
| `HeFD` | _(undocumented)_ | ✅ |
| `HeInLight` | _(undocumented)_ | ✅ |
| `Heat_I` | Heating PID integral term | ✅ |
| `Heat_P` | Heating PID proportional term | ✅ |
| `HumiditySh` | _(undocumented)_ | ✅ |
| `LOCMD` | _(undocumented)_ | ✅ |
| `MCVLV` | Mixing cooling valve position (%) | ✅ |
| `MDCMD` | _(undocumented)_ | ✅ |
| `MHVLV` | Mixing heating valve position (%) | ✅ |
| `MVLV` | Modulating valve position (%) | ✅ |
| `N_AM` | _(undocumented)_ | ✅ |
| `N_AlmEnaDly` | _(undocumented)_ | ✅ |
| `N_CO2` | _(undocumented)_ | ✅ |
| `N_CO2SP` | _(undocumented)_ | ✅ |
| `N_CO2_I` | _(undocumented)_ | ✅ |
| `N_CO2_P` | _(undocumented)_ | ✅ |
| `N_Clg_I` | _(undocumented)_ | ✅ |
| `N_Clg_P` | _(undocumented)_ | ✅ |
| `N_DSP` | _(undocumented)_ | ✅ |
| `N_FLTR` | _(undocumented)_ | ✅ |
| `N_FaDmpr` | _(undocumented)_ | ✅ |
| `N_FaDmprMin` | _(undocumented)_ | ✅ |
| `N_FailDly` | _(undocumented)_ | ✅ |
| `N_MVLV` | _(undocumented)_ | ✅ |
| `N_OCT` | _(undocumented)_ | ✅ |
| `N_RAH` | _(undocumented)_ | ✅ |
| `N_RAT` | _(undocumented)_ | ✅ |
| `N_RATHiAlmLmt` | _(undocumented)_ | ✅ |
| `N_RATLoAlmLmt` | _(undocumented)_ | ✅ |
| `N_RATSp` | _(undocumented)_ | ✅ |
| `N_RunTime` | _(undocumented)_ | ✅ |
| `N_SS` | _(undocumented)_ | ✅ |
| `N_SSDly` | _(undocumented)_ | ✅ |
| `N_STS` | _(undocumented)_ | ✅ |
| `N_TRIP` | _(undocumented)_ | ✅ |
| `N_WRT` | _(undocumented)_ | ✅ |
| `N_WST` | _(undocumented)_ | ✅ |
| `OCT` | Occupancy status (binary) | ✅ |
| `RAH` | Return air humidity (%RH) | ✅ |
| `RAHSP` | _(undocumented)_ | ✅ |
| `RAHSp` | Return air humidity setpoint (%RH) | ✅ |
| `RAT` | Return air temperature (°C) | ✅ |
| `RATHiAlmLmt` | Return air temp high alarm limit (°C) | ✅ |
| `RATLoAlmLmt` | Return air temp low alarm limit (°C) | ✅ |
| `RATNEW` | _(undocumented)_ | ✅ |
| `RATSh` | _(undocumented)_ | ✅ |
| `RATSp` | Return air temperature setpoint (°C) | ✅ |
| `RCO2` | _(undocumented)_ | ✅ |
| `RCO2SH` | _(undocumented)_ | ✅ |
| `RH` | Relative humidity (%RH) | ✅ |
| `RHDisplay` | _(undocumented)_ | ✅ |
| `RHNEW` | _(undocumented)_ | ✅ |
| `RHSH` | _(undocumented)_ | ✅ |
| `RHSp` | _(undocumented)_ | ✅ |
| `RT` | _(undocumented)_ | ✅ |
| `RTSH` | _(undocumented)_ | ✅ |
| `RunTime` | Accumulated run time (hours) | ✅ |
| `SAT` | _(undocumented)_ | ✅ |
| `SS` | Start/Stop command (binary) | ✅ |
| `SSDly` | Start/Stop delay (sec) | ✅ |
| `STS` | Operational status (binary) | ✅ |
| `TRIP` | Trip alarm status (binary) | ✅ |
| `TempDisplay` | _(undocumented)_ | ✅ |
| `TempSh` | _(undocumented)_ | ✅ |
| `TimeStart` | Scheduled start time | ✅ |
| `TimeStop` | Scheduled stop time | ✅ |
| `TotalTons` | Total cooling load (Tons) | — |
| `UserRATSp` | User RAT setpoint (°C) | ✅ |
| `VSD` | Variable speed drive speed (%) | ✅ |
| `VSDCTRL` | VSD control signal (%) | ✅ |
| `VSDFB` | VSD feedback (%) | ✅ |
| `VSD_I` | _(undocumented)_ | ✅ |
| `VSD_Max` | _(undocumented)_ | ✅ |
| `VSD_Min` | _(undocumented)_ | ✅ |
| `VSD_P` | _(undocumented)_ | ✅ |
| `WRT` | Chilled water return temperature (°C) | ✅ |
| `WST` | Chilled water supply temperature (°C) | ✅ |

## 6. Caveats / Known Gaps

- **Device-ID schemes differ.** EMS uses `e0101`; BMS uses `AHU_L10_PM1_01`. Join is via the
  TSV `AHU Label` normalized to a key (strip leading `AHU` + separators). Some TSV rows have
  no `device_id` (see §3 rows marked `(no id)`); some BMS devices have no TSV match.
- **Time spans differ.** EMS history reaches back further than BMS; joined rows only exist
  from the later BMS start. See §2.
- **BMS point sets vary per AHU** (cooling-only AHUs lack hot-water/heating points; only
  AHUs with a BTU meter expose `TotalTons`).
- **6 BMS items unparsed** (did not match `<device>_<NN>_<point>`):
  ```
  AHU_L11_PS1_DP
  AHU_L11_PS1_DPAI
  AHU_L11_PS4_DP
  AHU_L11_PS4_DPAI
  AHU_L5_OT07_TempSh
  AHU_Total_Tons
  ```
- **EMS token rejected** for the public bucket during this run; EMS facts come from the local
  DuckDB layers, which may lag the live electrical bucket.

## 7. Per-Device Detail

### e0101 · AHU_L1_ES_01

- **Level / Dept:** L01 / Enginering Services
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 1 points
- **BMS points:** OCT

### e0102 · AHU_L1_BES_01

- **Level / Dept:** L01 / Biomedical Engineering Services Unit
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0103 · AHU_L1_MO_01

- **Level / Dept:** L01 / Mortuary Services
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0104 · AHU_L1_HS_01

- **Level / Dept:** L01 / Housekeeping Services
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0105 · AHU_L1_CA_02

- **Level / Dept:** L01 / Catering & Dietitics Department
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0106 · AHU_L1_CA_01

- **Level / Dept:** L01 / Catering & Dietitics Department
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0107 · AHU_L1_MS_02

- **Level / Dept:** L01 / Medical Store
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 30 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, HWS, HWVLV, MVLV, OCT, RAH, RAHSP, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0108 · AHU_L1_MS_01

- **Level / Dept:** L01 / Medical Store
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 30 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, HWS, HWVLV, MVLV, OCT, RAH, RAHSP, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0109 · —

- **Level / Dept:** L01 / Security Services
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0110 · AHU_L1_PAC_01

- **Level / Dept:** L01 / Emergency Department
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** N_AM, N_AlmEnaDly, N_CO2, N_CO2SP, N_CO2_I, N_CO2_P, N_Clg_I, N_Clg_P, N_DSP, N_FLTR, N_FaDmpr, N_FaDmprMin, N_FailDly, N_MVLV, N_OCT, N_RAH, N_RAT, N_RATHiAlmLmt, N_RATLoAlmLmt, N_RATSp, N_RunTime, N_SS, N_SSDly, N_STS, N_TRIP, N_WRT, N_WST

### e0111 · AHU_AHU_L1_OSCC_01

- **Level / Dept:** L01 / Emergency Department
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS name variants:** AHU_AHU_L1_OSCC_01, AHU_L1_OSCC_01
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0112 · AHU_L1_ED_03

- **Level / Dept:** L01 / Emergency Department
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_FaDmprMin, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0113 · AHU_L1_ED_04

- **Level / Dept:** L01 / Emergency Department
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0114 · AHU_L1_ED_02

- **Level / Dept:** L01 / Emergency Department
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0115 · AHU_L1_ID_04

- **Level / Dept:** L01 / Imaging Department
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0116 · AHU_L1_ED_01

- **Level / Dept:** L01 / Emergency Department
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0117 · AHU_L1_SF_01

- **Level / Dept:** L01 / Shared Facilities 1
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0118 · AHU_L1_ID_03

- **Level / Dept:** L01 / Imaging Department
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0120 · AHU_L1_ID_02

- **Level / Dept:** L01 / Imaging Department
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0121 · AHU_L1_ID_01

- **Level / Dept:** L01 / Imaging Department
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 30 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, HWS, HWVLV, MVLV, OCT, RAH, RAHSP, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0201 · AHU_L2_CDC_03

- **Level / Dept:** L02 / Child Development Centre
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 34 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPAV, DSPSp, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSD, VSD_I, VSD_Max, VSD_Min, VSD_P, WRT, WST

### e0202 · AHU_L2_CDC_01

- **Level / Dept:** L02 / Child Development Centre
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 34 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPAV, DSPSp, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSD, VSD_I, VSD_Max, VSD_Min, VSD_P, WRT, WST

### e0203 · AHU_L2_CDC_04

- **Level / Dept:** L02 / Child Development Centre
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 34 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPAV, DSPSp, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSD, VSD_I, VSD_Max, VSD_Min, VSD_P, WRT, WST

### e0204 · AHU_L2_CDC_02

- **Level / Dept:** L02 / Child Development Centre
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 34 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPAV, DSPSp, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSD, VSD_I, VSD_Max, VSD_Min, VSD_P, WRT, WST

### e0205 · AHU_L2_CDC_05

- **Level / Dept:** L02 / Child Development Centre
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 34 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPAV, DSPSp, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSD, VSD_I, VSD_Max, VSD_Min, VSD_P, WRT, WST

### e0206 · AHU_L2_CF_01

- **Level / Dept:** L02 / Cafeteria
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0207 · AHU_L2_MSS_01

- **Level / Dept:** L02 / Medical Social Services
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0208 · AHU_L2_OP_01

- **Level / Dept:** L02 / Outpatient Pharmacy
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 28 points
- **BMS points:** AM, AlmEnaDly, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmprMin, FailDly, HWS, HWVLV, MVLV, OCT, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0209 · AHU_L2_AR_01

- **Level / Dept:** L02 / Admission Revenue
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0210 · AHU_L3_PGMC_02

- **Level / Dept:** L03 / Post Graduate Medical Centre and Continuous Medical Education
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0211 · AHU_L3_PGMC_01

- **Level / Dept:** L03 / Post Graduate Medical Centre and Continuous Medical Education
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0212 · AHU_L1_OT_01

- **Level / Dept:** L01 / Emergency Department
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 38 points
- **BMS points:** AFR, AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DP, DSP, FADMPR, FADmprMin, FLTR, FailDly, HWST, HeFD, HeInLight, Heat_I, Heat_P, MCVLV, MHVLV, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RH, RT, RunTime, SAT, SS, SSDly, STS, TRIP, WRT, WST

### e0213 · AHU_L2_WHU_01

- **Level / Dept:** L02 / Women Health Unit
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 29 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, HEATPerc, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RHSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0214 · AHU_L2_WHU_02

- **Level / Dept:** L02 / Women Health Unit
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 29 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, HEATPerc, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RHSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0215 · AHU_L2_SPG_04

- **Level / Dept:** L02 / O&G Specialist Clinic
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e0216 · AHU_L2_SPG_03

- **Level / Dept:** L02 / O&G Specialist Clinic
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 30 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e0217 · AHU_L2_SPG_02

- **Level / Dept:** L02 / O&G Specialist Clinic
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 24 points
- **BMS points:** AM, AlmEnaDly, Clg_I, Clg_P, DSPNew, DSPSP, FLTR, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e0218 · AHU_L2_SPG_01

- **Level / Dept:** L02 / O&G Specialist Clinic
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e0301 · —

- **Level / Dept:** L03 / Pathology Department
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0303 · —

- **Level / Dept:** L03 / Pathology Department
- **EMS:** start 2025-11-05 06:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0304 · —

- **Level / Dept:** L03 / RQA Unit
- **EMS:** start 2025-11-10 07:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0306 · AHU_L3_SPD_02

- **Level / Dept:** L03 / Dental Clinic
- **EMS:** start 2025-11-10 07:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0307 · AHU_L3_SF_01

- **Level / Dept:** L03 / Shared Facilities 3
- **EMS:** start 2025-11-10 07:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0308 · AHU_L3_SPP_03

- **Level / Dept:** L03 / Paediatric Specialist Clinic
- **EMS:** start 2025-11-10 07:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0311 · AHU_L3_SPP_01

- **Level / Dept:** L03 / Paediatric Specialist Clinic
- **EMS:** start 2025-11-10 07:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0312 · AHU_L3_SPP_02

- **Level / Dept:** L03 / Paediatric Specialist Clinic
- **EMS:** start 2025-11-10 07:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0313 · AHU_L3_SPD_01

- **Level / Dept:** L03 / Dental Clinic
- **EMS:** start 2025-11-10 07:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0314 · AHU_L3_CPC_01

- **Level / Dept:** L03 / Paediatric Specialist Clinic
- **EMS:** start 2025-11-10 07:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0315 · AHU_L3_SPD_03

- **Level / Dept:** L03 / Dental Clinic
- **EMS:** start 2025-11-10 07:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 29 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FADmprMin, FLTR, FaDmpr, FailDly, HWVLV, MVLV, OCT, RAH, RAHSP, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0401 · AHU_L3_PT_02

- **Level / Dept:** L03 / Pathology Department
- **EMS:** start 2025-11-10 07:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 30 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FADMPR, FADmprMin, FLTR, FailDly, HWS, HWVLV, MVLV, OCT, RAH, RAHSP, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0402 · AHU_L3_PT_01

- **Level / Dept:** L03 / Pathology Department
- **EMS:** start 2025-11-10 07:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 30 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FADMPR, FADmprMin, FLTR, FailDly, HWS, HWVLV, MVLV, OCT, RAH, RAHSP, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0403 · AHU_L4_MK_01

- **Level / Dept:** L04 / Milk Preparation 1
- **EMS:** start 2025-11-10 07:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0404 · AHU_L4_PD_01

- **Level / Dept:** L04 / Inpatient Pharmacy Department
- **EMS:** start 2025-11-10 07:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 30 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, HWS, HWVLV, MVLV, OCT, RAH, RAHSP, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0406 · —

- **Level / Dept:** L04 / Inpatient Pharmacy Department
- **EMS:** start 2025-12-31 01:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0406 · —

- **Level / Dept:** L04 / Inpatient Pharmacy Department
- **EMS:** start 2025-12-31 01:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0407 · AHU_L4_PD_02

- **Level / Dept:** L04 / Inpatient Pharmacy Department
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-04-06 04:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 28 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSh, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0408 · AHU_L4_SCT_03

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-04-06 04:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0409 · AHU_L4_SCT_01

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-04-06 04:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 21 points
- **BMS points:** AM, AlmEnaDly, Clg_I, Clg_P, DSP, FLTR, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0411 · —

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-04-06 04:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0412 · AHU_L4_OHR_01

- **Level / Dept:** L04 / Obstetric High Risk Unit
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-04-06 04:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO21, CO2SP1, CO2_I1, CO2_P1, Clg_I, Clg_P, DSP, DefaultRATsp, FLTR, FaDmpr1, FaDmprMin1, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, TimeStart, TimeStop, UserRATSp, WRT, WST

### e0413 · AHU_L4_MOT_04

- **Level / Dept:** L04 / Maternity OT
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 32 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FADMPR, FADmprMin, FLTR, FailDly, HWS, Heat_I, Heat_P, MCVLV, MHVLV, OCT, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0414 · AHU_L4_MOT_02

- **Level / Dept:** L04 / Maternity OT
- **EMS:** start 2025-12-31 01:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 35 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DP, DSP, FADMPR, FADmprMin, FLTR, FailDly, HeFD, Heat_I, Heat_P, MCVLV, MHVLV, OCT, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RH, RT, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0415 · AHU_L4_MOT_03

- **Level / Dept:** L04 / Maternity OT
- **EMS:** start 2025-12-31 01:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 29 points
- **BMS points:** AFR, AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SAT, SS, SSDly, STS, TRIP, WRT, WST

### e0416 · AHU_L4_MOT_01

- **Level / Dept:** L04 / Maternity OT
- **EMS:** start 2025-12-31 01:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 36 points
- **BMS points:** AFR, AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DP, DSP, FADMPR, FADmprMin, FLTR, FailDly, HWST, HWVLV, HeFD, MVLV, OCT, RAH, RAHSP, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RH, RT, RunTime, SAT, SS, SSDly, STS, TRIP, WRT, WST

### e0419 · AHU_L4_SF_01

- **Level / Dept:** L04 / Shared Facilities 4
- **EMS:** start 2025-12-31 01:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0423 · AHU_L3_BL_01

- **Level / Dept:** L03 / Biophysiological Department
- **EMS:** start 2025-12-31 01:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0501 · AHU_L5_PICU_02

- **Level / Dept:** L05 / Paediatric Intensive Care Unit
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0502 · AHU_L5_PHDU_01

- **Level / Dept:** L05 / Paediatric High Dependency Unit (DWP)
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0503 · AHU_L5_AD_01

- **Level / Dept:** L05 / Anaesthesiology Department
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0504 · AHU_L5_RHU_01

- **Level / Dept:** L05 / Respiratory and Haemodynamic Unit
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0505 · AHU_L5_AICU_02

- **Level / Dept:** L05 / Adult Intensive Care Unit
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0506 · AHU_L5_AHDU_01

- **Level / Dept:** L05 / Adult High Dependency Unit (DWA)
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0507 · —

- **Level / Dept:** L05 / Adult Intensive Care Unit
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0508 · —

- **Level / Dept:** L05 / Shared Facilities 5
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0509 · AHU_L5_PBU_02

- **Level / Dept:** L05 / Paediatric Burn Unit
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0510 · AHU_L5_PICU_01

- **Level / Dept:** L05 / Paediatric Intensive Care Unit
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0511 · AHU_L5_PBU_01

- **Level / Dept:** L05 / Paediatric Burn Unit
- **EMS:** start 2025-11-29 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 21 points
- **BMS points:** AM, AlmEnaDly, Clg_I, Clg_P, DSP, FLTR, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0602 · —

- **Level / Dept:** L06 / Library
- **EMS:** start 2025-10-30 09:00 UTC, end 2026-05-18 11:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0603 · —

- **Level / Dept:** L06 / Administration Unit
- **EMS:** start 2025-10-30 09:00 UTC, end 2026-05-18 10:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0604 · —

- **Level / Dept:** L06 / Administration Unit
- **EMS:** start 2025-10-30 09:00 UTC, end 2026-05-18 10:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0605 · —

- **Level / Dept:** L06 / Central Sterile Supply Unit
- **EMS:** start 2025-10-30 09:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0606 · —

- **Level / Dept:** L06 / Central Sterile Supply Unit
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0607 · AHU_L6_SOC_01

- **Level / Dept:** L06 / Specialist Office Complex
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e0611 · AHU_L6_IT_01

- **Level / Dept:** L06 / Information Technology Department
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0622 · AHU_L5_OT_10

- **Level / Dept:** L05 / Main Operation Theatre Complex
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 26 points
- **BMS points:** DPDisplay, DPSh, DSPSH, DSPSP, EFSS, EFST, EFTR, FAN1RunTime, FAN1SS, FAN1VSD, FAN2RunTime, FAN2SS, FAN2ST, FAN2TR, FAN2VSD, HRWSS, HRWST, HRWTR, HWRTNEW, HumiditySh, RATNEW, RCO2, RHDisplay, RHNEW, TempDisplay, TempSh

### e0625 · —

- **Level / Dept:** L06 / Medical Record
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** **none** (not in BMS bucket)

### e0626 · AHU_L6_SF_01

- **Level / Dept:** L06 / Shared Facilities 6
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0627 · AHU_L6_SOC_02

- **Level / Dept:** L06 / Specialist Office Complex
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e0628 · AHU_L6_CSSD_03

- **Level / Dept:** L06 / Central Sterile Supply Unit
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FADMPR, FADmprMin, FLTR, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0701 · AHU_L7_OB3_01

- **Level / Dept:** L07 / Inpatient Wards - Obstetric 3
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 11 points
- **BMS points:** CO2, CO2SP, CO2_I, CO2_P, DSPNewSh, DSPSP, FaDmpr, FaDmprMin, OCT, VSDCTRL, VSDFB

### e0702 · AHU_L7_OB4_01

- **Level / Dept:** L07 / Inpatient Wards - Obstetric 4
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 29 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, HEATPerc, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RHSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0703 · AHU_L7_OB1_01

- **Level / Dept:** L07 / Inpatient Wards - Obstetric 1
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 37 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPNewSh, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, HEATPerc, HICMD, LOCMD, MDCMD, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RHSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e0704 · AHU_L7_OB2_01

- **Level / Dept:** L07 / Inpatient Wards - Obstetric 2
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, Clg_I, Clg_P, DSP, DSPNew, DSPSP, FLTR, FailDly, HEATperc, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RHSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e0801 · AHU_L8_CW_02

- **Level / Dept:** L08 / 1st Class Ward
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e0802 · AHU_L8_CW_01

- **Level / Dept:** L08 / 1st Class Ward
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e0803 · AHU_L8_OCC_01

- **Level / Dept:** L08 / On Call Complex
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0804 · AHU_L8_GY1_01

- **Level / Dept:** L08 / Inpatient Wards - Gynaecology 1
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0805 · AHU_L8_GY2_01

- **Level / Dept:** L08 / Inpatient Wards - Gynaecology 2
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0901 · AHU_L9_NP_01

- **Level / Dept:** L09 / Nephrology/ Dialysis Ward and Renal Treatment Centre
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0902 · AHU_L9_NP_02

- **Level / Dept:** L09 / Nephrology/ Dialysis Ward and Renal Treatment Centre
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0903 · AHU_L9_PM5_01

- **Level / Dept:** L09 / Inpatient Wards - Paediatric Medical Ward 5
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 25 points
- **BMS points:** AM, AlmEnaDly, Clg_I, Clg_P, DSP, DefaultRATSp, FLTR, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, TimeStart, TimeStop, UserRATSp, WRT, WST

### e0904 · AHU_L9_PM5_02

- **Level / Dept:** L09 / Inpatient Wards - Paediatric Medical Ward 5
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 33 points
- **BMS points:** AM, AlmEnaDly, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DefaultRATSp, FADMPR, FADmprMin, FLTR, FailDly, HWS, HWVLV, MVLV, OCT, RAH, RAHSP, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, TimeStart, TimeStop, UserRATSp, WRT, WST

### e0905 · AHU_L9_NW1_01

- **Level / Dept:** L09 / Neonatology Wards 1
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0906 · AHU_L9_NW1_02

- **Level / Dept:** L09 / Neonatology Wards 1
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0907 · AHU_L9_NW2_02

- **Level / Dept:** L09 / Neonatology Wards 2
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e0908 · AHU_L9_NW2_01

- **Level / Dept:** L09 / Neonatology Wards 2
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e1001 · AHU_L10_PM1_02

- **Level / Dept:** L10 / Inpatient Wards - Paediatric Medical Ward 1
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 35 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, DefaultRATSp, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, TimeStart, TimeStop, UserRATSp, VSDCTRL, VSDFB, WRT, WST

### e1002 · AHU_L10_PM1_01

- **Level / Dept:** L10 / Inpatient Wards - Paediatric Medical Ward 1
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 35 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, DefaultRATSp, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, TimeStart, TimeStop, UserRATSp, VSDCTRL, VSDFB, WRT, WST

### e1003 · AHU_L10_PM3_01

- **Level / Dept:** L10 / Inpatient Wards - Paediatric Medical Ward 3
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e1004 · AHU_L10_PM3_02

- **Level / Dept:** L10 / Inpatient Wards - Paediatric Medical Ward 3
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e1005 · AHU_L10_PM4_02

- **Level / Dept:** L10 / Inpatient Wards - Paediatric Medical Ward 4
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 35 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, DefaultRATSp, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, TimeStart, TimeStop, UserRATSp, VSDCTRL, VSDFB, WRT, WST

### e1006 · AHU_L10_PM4_01

- **Level / Dept:** L10 / Inpatient Wards - Paediatric Medical Ward 4
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 35 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, DefaultRATSp, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, TimeStart, TimeStop, UserRATSp, VSDCTRL, VSDFB, WRT, WST

### e1007 · AHU_L10_PM2_01

- **Level / Dept:** L10 / Inpatient Wards - Paediatric Medical Ward 2
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e1008 · AHU_L10_PM2_02

- **Level / Dept:** L10 / Inpatient Wards - Paediatric Medical Ward 2
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### e1101 · AHU_L11_PS1_02

- **Level / Dept:** L11 / Inpatient Wards - Paediatric Surgical Ward 1
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 2 points
- **BMS points:** DP, DPOff

### e1102 · AHU_L11_PS1_01

- **Level / Dept:** L11 / Inpatient Wards - Paediatric Surgical Ward 1
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 32 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DP, DPOff, DSP, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDFB, WRT, WST

### e1103 · AHU_L11_PS2_01

- **Level / Dept:** L11 / Inpatient Wards - Paediatric Surgical Ward 2
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e1104 · AHU_L11_PS2_02

- **Level / Dept:** L11 / Inpatient Wards - Paediatric Surgical Ward 2
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e1105 · AHU_L11_PS4_02

- **Level / Dept:** L11 / Inpatient Wards - Paediatric Surgical Ward 4
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e1106 · AHU_L11_PS4_01

- **Level / Dept:** L11 / Inpatient Wards - Paediatric Surgical Ward 4
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e1107 · AHU_L11_PS3_01

- **Level / Dept:** L11 / Inpatient Wards - Paediatric Surgical Ward 3
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DSPNew, DSPNewSh, DSPSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, VSDCTRL, VSDFB, WRT, WST

### e1108 · AHU_L11_PS3_02

- **Level / Dept:** L11 / Inpatient Wards - Paediatric Surgical Ward 3
- **EMS:** start 2025-10-30 08:00 UTC, end 2026-05-25 08:00 UTC, 46 metrics
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 26 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L1_CN_01

- **Level / Dept:** L01 / Creche/ Nursery
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L1_SST_01

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 21 points
- **BMS points:** AM, AlmEnaDly, Clg_I, Clg_P, DSP, FLTR, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · —

- **Level / Dept:** L02 / ART Centre
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L02 / ART Centre
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L02 / ART Centre
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L02 / ART Centre
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · AHU_L2_ART_01

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L2_ART_02

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L2_ART_03

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 32 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FADMPR, FADmprMin, FLTR, FailDly, HeFD, Heat_I, Heat_P, MCVLV, MHVLV, OCT, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L2_OP_01_01

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 2 points
- **BMS points:** CO2, FaDmpr

### **(no id)** · AHU_L3_EOA_01

- **Level / Dept:** L03 / Paediatric Specialist Clinic
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L3_EOA_02

- **Level / Dept:** L03 / Paediatric Specialist Clinic
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L3_GL_01

- **Level / Dept:** L03 / Genetic Department
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 30 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FADMPR, FADmprMin, FLTR, FailDly, HWS, HWVLV, MVLV, OCT, RAH, RAHSP, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L3_GL_02

- **Level / Dept:** L03 / Genetic Department
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 30 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FADMPR, FADmprMin, FLTR, FailDly, HWS, HWVLV, MVLV, OCT, RAH, RAHSP, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L3_PT_03

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 30 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FADMPR, FADmprMin, FLTR, FailDly, HWS, HWVLV, MVLV, OCT, RAH, RAHSP, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L3_PT_04

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L3_RQAHEU_01

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L4_CDR_01

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 25 points
- **BMS points:** AM, AlmEnaDly, Clg_I, Clg_P, FLTR, FailDly, Heat_I, Heat_P, MCVLV, MHVLV, OCT, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SAT, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L4_CDR_02

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 25 points
- **BMS points:** AM, AlmEnaDly, Clg_I, Clg_P, FLTR, FailDly, Heat_I, Heat_P, MCVLV, MHVLV, OCT, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SAT, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L4_LD_01

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L4_LD_02

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L4_LD_03

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · —

- **Level / Dept:** L04 / Labour and Delivery Unit
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Labour and Delivery Unit
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Labour and Delivery Unit
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Neonatal Intensive Care Unit
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Neonatal Intensive Care Unit
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · AHU_L4_NICU_01

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DefaultRATSp, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, TimeStart, TimeStop, UserRATSp, WRT, WST

### **(no id)** · AHU_L4_NICU_02

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 31 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, DefaultRATSp, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, TimeStart, TimeStop, UserRATSp, WRT, WST

### **(no id)** · AHU_L4_NONSTERILE_01

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 25 points
- **BMS points:** AM, AlmEnaDly, Clg_I, Clg_P, FLTR, FailDly, Heat_I, Heat_P, MCVLV, MHVLV, OCT, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SAT, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · —

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Bone Marrow Transplant Unit (Stem Cell Transplant)
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · AHU_L4_TPN_01

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 25 points
- **BMS points:** AM, AlmEnaDly, Clg_I, Clg_P, FLTR, FailDly, Heat_I, Heat_P, MCVLV, MHVLV, OCT, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SAT, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L5_OT_01

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 26 points
- **BMS points:** DPDisplay, DPSh, DSPSH, DSPSP, EFSS, EFST, EFTR, FAN1RunTime, FAN1SS, FAN1VSD, FAN2RunTime, FAN2SS, FAN2ST, FAN2TR, FAN2VSD, HRWSS, HRWST, HRWTR, HWRTNEW, HumiditySh, RATNEW, RCO2, RHDisplay, RHNEW, TempDisplay, TempSh

### **(no id)** · AHU_L5_OT_02

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 26 points
- **BMS points:** DPDisplay, DPSh, DSPSH, DSPSP, EFSS, EFST, EFTR, FAN1RunTime, FAN1SS, FAN1VSD, FAN2RunTime, FAN2SS, FAN2ST, FAN2TR, FAN2VSD, HRWSS, HRWST, HRWTR, HWRTNEW, HumiditySh, RATNEW, RCO2, RHDisplay, RHNEW, TempDisplay, TempSh

### **(no id)** · AHU_L5_OT_03

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 67 points
- **BMS points:** AFR, AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DP, DPDisplay, DPSh, DSP, DSPSH, DSPSP, EFSS, EFST, EFTR, FADMPR, FADmprMin, FAN1RunTime, FAN1SS, FAN1VSD, FAN2RunTime, FAN2SS, FAN2ST, FAN2TR, FAN2VSD, FLTR, FailDly, HRWSS, HRWST, HRWTR, HWRTNEW, HWST, HeFD, HeInLight, Heat_I, Heat_P, HumiditySh, MCVLV, MHVLV, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATNEW, RATSp, RCO2, RCO2SH, RH, RHDisplay, RHNEW, RHSH, RT, RTSH, RunTime, SAT, SS, SSDly, STS, TRIP, TempDisplay, TempSh, WRT, WST

### **(no id)** · AHU_L5_OT_04

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 67 points
- **BMS points:** AFR, AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DP, DPDisplay, DPSh, DSP, DSPSH, DSPSP, EFSS, EFST, EFTR, FADMPR, FADmprMin, FAN1RunTime, FAN1SS, FAN1VSD, FAN2RunTime, FAN2SS, FAN2ST, FAN2TR, FAN2VSD, FLTR, FailDly, HRWSS, HRWST, HRWTR, HWRTNEW, HWST, HeFD, HeInLight, Heat_I, Heat_P, HumiditySh, MCVLV, MHVLV, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATNEW, RATSp, RCO2, RCO2SH, RH, RHDisplay, RHNEW, RHSH, RT, RTSH, RunTime, SAT, SS, SSDly, STS, TRIP, TempDisplay, TempSh, WRT, WST

### **(no id)** · AHU_L5_OT_05

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 67 points
- **BMS points:** AFR, AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DP, DPDisplay, DPSh, DSP, DSPSH, DSPSP, EFSS, EFST, EFTR, FADMPR, FADmprMin, FAN1RunTime, FAN1SS, FAN1VSD, FAN2RunTime, FAN2SS, FAN2ST, FAN2TR, FAN2VSD, FLTR, FailDly, HRWSS, HRWST, HRWTR, HWRTNEW, HWST, HeFD, HeInLight, Heat_I, Heat_P, HumiditySh, MCVLV, MHVLV, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATNEW, RATSp, RCO2, RCO2SH, RH, RHDisplay, RHNEW, RHSH, RT, RTSH, RunTime, SAT, SS, SSDly, STS, TRIP, TempDisplay, TempSh, WRT, WST

### **(no id)** · AHU_L5_OT_06

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 67 points
- **BMS points:** AFR, AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DP, DPDisplay, DPSh, DSP, DSPSH, DSPSP, EFSS, EFST, EFTR, FADMPR, FADmprMin, FAN1RunTime, FAN1SS, FAN1VSD, FAN2RunTime, FAN2SS, FAN2ST, FAN2TR, FAN2VSD, FLTR, FailDly, HRWSS, HRWST, HRWTR, HWRTNEW, HWST, HeFD, HeInLight, Heat_I, Heat_P, HumiditySh, MCVLV, MHVLV, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATNEW, RATSp, RCO2, RCO2SH, RH, RHDisplay, RHNEW, RHSH, RT, RTSH, RunTime, SAT, SS, SSDly, STS, TRIP, TempDisplay, TempSh, WRT, WST

### **(no id)** · AHU_L5_OT_07

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 66 points
- **BMS points:** AFR, AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DP, DPDisplay, DPSh, DSP, DSPSH, DSPSP, EFSS, EFST, EFTR, FADMPR, FADmprMin, FAN1RunTime, FAN1SS, FAN1VSD, FAN2RunTime, FAN2SS, FAN2ST, FAN2TR, FAN2VSD, FLTR, FailDly, HRWSS, HRWST, HRWTR, HWRTNEW, HWST, HeFD, HeInLight, Heat_I, Heat_P, HumiditySh, MCVLV, MHVLV, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATNEW, RATSp, RCO2, RCO2SH, RH, RHDisplay, RHNEW, RHSH, RT, RTSH, RunTime, SAT, SS, SSDly, STS, TRIP, TempDisplay, WRT, WST

### **(no id)** · AHU_L5_OT_08

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 67 points
- **BMS points:** AFR, AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DP, DPDisplay, DPSh, DSP, DSPSH, DSPSP, EFSS, EFST, EFTR, FADMPR, FADmprMin, FAN1RunTime, FAN1SS, FAN1VSD, FAN2RunTime, FAN2SS, FAN2ST, FAN2TR, FAN2VSD, FLTR, FailDly, HRWSS, HRWST, HRWTR, HWRTNEW, HWST, HeFD, HeInLight, Heat_I, Heat_P, HumiditySh, MCVLV, MHVLV, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATNEW, RATSp, RCO2, RCO2SH, RH, RHDisplay, RHNEW, RHSH, RT, RTSH, RunTime, SAT, SS, SSDly, STS, TRIP, TempDisplay, TempSh, WRT, WST

### **(no id)** · AHU_L5_OT_09

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 67 points
- **BMS points:** AFR, AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DP, DPDisplay, DPSh, DSP, DSPSH, DSPSP, EFSS, EFST, EFTR, FADMPR, FADmprMin, FAN1RunTime, FAN1SS, FAN1VSD, FAN2RunTime, FAN2SS, FAN2ST, FAN2TR, FAN2VSD, FLTR, FailDly, HRWSS, HRWST, HRWTR, HWRTNEW, HWST, HeFD, HeInLight, Heat_I, Heat_P, HumiditySh, MCVLV, MHVLV, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATNEW, RATSp, RCO2, RCO2SH, RH, RHDisplay, RHNEW, RHSH, RT, RTSH, RunTime, SAT, SS, SSDly, STS, TRIP, TempDisplay, TempSh, WRT, WST

### **(no id)** · AHU_L5_OT_11

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 26 points
- **BMS points:** DPDisplay, DPSh, DSPSH, DSPSP, EFSS, EFST, EFTR, FAN1RunTime, FAN1SS, FAN1VSD, FAN2RunTime, FAN2SS, FAN2ST, FAN2TR, FAN2VSD, HRWSS, HRWST, HRWTR, HWRTNEW, HumiditySh, RATNEW, RCO2, RHDisplay, RHNEW, TempDisplay, TempSh

### **(no id)** · AHU_L5_OT_12

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 26 points
- **BMS points:** DPDisplay, DPSh, DSPSH, DSPSP, EFSS, EFST, EFTR, FAN1RunTime, FAN1SS, FAN1VSD, FAN2RunTime, FAN2SS, FAN2ST, FAN2TR, FAN2VSD, HRWSS, HRWST, HRWTR, HWRTNEW, HumiditySh, RATNEW, RCO2, RHDisplay, RHNEW, TempDisplay, TempSh

### **(no id)** · AHU_L5_OT_13

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-19 07:13 UTC, end 2026-05-29 03:16 UTC, 67 points
- **BMS points:** AFR, AM, AlmEnaDly, CO2, CO2Sp, CO2_I, CO2_P, Clg_I, Clg_P, DP, DPDisplay, DPSh, DSP, DSPSH, DSPSP, EFSS, EFST, EFTR, FADMPR, FADmprMin, FAN1RunTime, FAN1SS, FAN1VSD, FAN2RunTime, FAN2SS, FAN2ST, FAN2TR, FAN2VSD, FLTR, FailDly, HRWSS, HRWST, HRWTR, HWRTNEW, HWST, HeFD, HeInLight, Heat_I, Heat_P, HumiditySh, MCVLV, MHVLV, RAH, RAHSp, RAT, RATHiAlmLmt, RATLoAlmLmt, RATNEW, RATSp, RCO2, RCO2SH, RH, RHDisplay, RHNEW, RHSH, RT, RTSH, RunTime, SAT, SS, SSDly, STS, TRIP, TempDisplay, TempSh, WRT, WST

### **(no id)** · AHU_L5_OT_15

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L5_OT_16

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L5_OT_17

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · AHU_L5_SF_01

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 27 points
- **BMS points:** AM, AlmEnaDly, CO2, CO2SP, CO2_I, CO2_P, Clg_I, Clg_P, DSP, FLTR, FaDmpr, FaDmprMin, FailDly, MVLV, OCT, RAH, RAT, RATHiAlmLmt, RATLoAlmLmt, RATSp, RunTime, SS, SSDly, STS, TRIP, WRT, WST

### **(no id)** · —

- **Level / Dept:** L05 / Main Operation Theatre Complex
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · AHU_L6_SOC_03

- **Level / Dept:** — / —
- **EMS:** **none** (not in electrical bucket)
- **BMS:** start 2026-02-24 07:14 UTC, end 2026-05-29 03:16 UTC, 1 points
- **BMS points:** DSP

### **(no id)** · —

- **Level / Dept:** L04 / Inpatient Pharmacy Department
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**

### **(no id)** · —

- **Level / Dept:** L04 / Inpatient Pharmacy Department
- **EMS:** **none** (not in electrical bucket)
- **BMS:** **none** (not in BMS bucket)
- ⚠️ **No EMS and no BMS data for this device.**
