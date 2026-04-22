/**
 * Maps raw AHU device IDs (e.g. "e0101") to human-readable display names.
 * Format: AHU-L{level}-{dept_abbr}-{nn} — {Department Name}
 */

const DEVICE_MAP: Record<string, [string, string]> = {
  // Level 1
  e0101: ['ES', 'Engineering Services'],
  e0102: ['BES', 'Biomedical Engineering Services Unit'],
  e0103: ['MOR', 'Mortuary Services'],
  e0104: ['HSK', 'Housekeeping Services'],
  e0105: ['CAD', 'Catering & Dietetics Department'],
  e0106: ['CAD', 'Catering & Dietetics Department'],
  e0107: ['MDS', 'Medical Store'],
  e0108: ['MDS', 'Medical Store'],
  e0109: ['SEC', 'Security Services'],
  e0110: ['EMG', 'Emergency Department'],
  e0111: ['EMG', 'Emergency Department'],
  e0112: ['EMG', 'Emergency Department'],
  e0113: ['EMG', 'Emergency Department'],
  e0114: ['EMG', 'Emergency Department'],
  e0115: ['EMG', 'Emergency Department'],
  e0116: ['EMG', 'Emergency Department'],
  e0117: ['EMG', 'Emergency Department'],
  e0118: ['IMG', 'Imaging Department'],
  e0120: ['IMG', 'Imaging Department'],
  e0121: ['IMG', 'Imaging Department'],
  // Level 2
  e0201: ['CDC', 'Child Development Centre'],
  e0202: ['CDC', 'Child Development Centre'],
  e0203: ['CDC', 'Child Development Centre'],
  e0204: ['CDC', 'Child Development Centre'],
  e0205: ['CDC', 'Child Development Centre'],
  e0206: ['CAF', 'Cafeteria'],
  e0207: ['MSS', 'Medical Social Services'],
  e0208: ['OPH', 'Outpatient Pharmacy'],
  e0209: ['ADM', 'Admission & Revenue'],
  e0210: ['PGM', 'Post Graduate Medical Centre'],
  e0211: ['PGM', 'Post Graduate Medical Centre'],
  e0213: ['WHU', 'Women Health Unit'],
  e0214: ['WHU', 'Women Health Unit'],
  e0215: ['OGS', 'O&G Specialist Clinic'],
  e0216: ['OGS', 'O&G Specialist Clinic'],
  e0217: ['OGS', 'O&G Specialist Clinic'],
  e0218: ['OGS', 'O&G Specialist Clinic'],
  // Level 3
  e0301: ['PATH', 'Pathology Department'],
  e0303: ['PATH', 'Pathology Department'],
  e0304: ['RQA', 'RQA Unit'],
  e0306: ['DEN', 'Dental Clinic'],
  e0307: ['SF3', 'Shared Facilities 3'],
  e0308: ['PSC', 'Paediatric Specialist Clinic'],
  e0311: ['PSC', 'Paediatric Specialist Clinic'],
  e0312: ['PSC', 'Paediatric Specialist Clinic'],
  e0313: ['DEN', 'Dental Clinic'],
  e0314: ['PSC', 'Paediatric Specialist Clinic'],
  e0315: ['DEN', 'Dental Clinic'],
  e0323: ['BIO', 'Biophysiological Department'],
  // Level 4
  e0401: ['PATH', 'Pathology Department'],
  e0402: ['PATH', 'Pathology Department'],
  e0404: ['IPH', 'Inpatient Pharmacy Department'],
  e0406: ['IPH', 'Inpatient Pharmacy Department'],
  e0407: ['IPH', 'Inpatient Pharmacy Department'],
  e0408: ['BMT', 'Bone Marrow Transplant Unit'],
  e0409: ['BMT', 'Bone Marrow Transplant Unit'],
  e0411: ['BMT', 'Bone Marrow Transplant Unit'],
  e0412: ['OHR', 'Obstetric High Risk Unit'],
  e0413: ['MOT', 'Maternity OT'],
  e0414: ['MOT', 'Maternity OT'],
  e0415: ['MOT', 'Maternity OT'],
  e0416: ['MOT', 'Maternity OT'],
  e0419: ['SF4', 'Shared Facilities 4'],
  // Level 5
  e0501: ['PICU', 'Paediatric Intensive Care Unit'],
  e0502: ['PHDU', 'Paediatric High Dependency Unit'],
  e0503: ['ANS', 'Anaesthesiology Department'],
  e0504: ['RHU', 'Respiratory & Haemodynamic Unit'],
  e0505: ['AICU', 'Adult Intensive Care Unit'],
  e0506: ['AHDU', 'Adult High Dependency Unit'],
  e0507: ['AICU', 'Adult Intensive Care Unit'],
  e0508: ['SF5', 'Shared Facilities 5'],
  e0509: ['PBU', 'Paediatric Burn Unit'],
  e0510: ['PICU', 'Paediatric Intensive Care Unit'],
  e0511: ['PBU', 'Paediatric Burn Unit'],
  // Level 6
  e0602: ['LIB', 'Library'],
  e0603: ['ADM', 'Administration Unit'],
  e0604: ['ADM', 'Administration Unit'],
  e0605: ['CSSU', 'Central Sterile Supply Unit'],
  e0606: ['CSSU', 'Central Sterile Supply Unit'],
  e0607: ['SOC', 'Specialist Office Complex'],
  e0611: ['IT', 'Information Technology Department'],
  e0622: ['MOTC', 'Main Operation Theatre Complex'],
  e0625: ['MR', 'Medical Record'],
  e0626: ['SF6', 'Shared Facilities 6'],
  e0627: ['SOC', 'Specialist Office Complex'],
  e0628: ['CSSU', 'Central Sterile Supply Unit'],
  // Level 7
  e0701: ['OBW', 'Obstetric Ward'],
  e0702: ['OBW', 'Obstetric Ward'],
  e0703: ['OBW', 'Obstetric Ward'],
  e0704: ['OBW', 'Obstetric Ward'],
  // Level 8
  e0801: ['1CW', '1st Class Ward'],
  e0802: ['1CW', '1st Class Ward'],
  e0803: ['OCC', 'On Call Complex'],
  e0804: ['GYN', 'Gynaecology Ward'],
  e0805: ['GYN', 'Gynaecology Ward'],
  // Level 9
  e0901: ['NDW', 'Nephrology/Dialysis Ward'],
  e0902: ['NDW', 'Nephrology/Dialysis Ward'],
  e0903: ['PMW', 'Paediatric Medical Ward'],
  e0904: ['PMW', 'Paediatric Medical Ward'],
  e0905: ['NEO', 'Neonatology Wards'],
  e0906: ['NEO', 'Neonatology Wards'],
  e0907: ['NEO', 'Neonatology Wards'],
  e0908: ['NEO', 'Neonatology Wards'],
  // Level 10
  e1001: ['PMW', 'Paediatric Medical Ward'],
  e1002: ['PMW', 'Paediatric Medical Ward'],
  e1003: ['PMW', 'Paediatric Medical Ward'],
  e1004: ['PMW', 'Paediatric Medical Ward'],
  e1005: ['PMW', 'Paediatric Medical Ward'],
  e1006: ['PMW', 'Paediatric Medical Ward'],
  e1007: ['PMW', 'Paediatric Medical Ward'],
  e1008: ['PMW', 'Paediatric Medical Ward'],
  // Level 11
  e1101: ['PSW', 'Paediatric Surgical Ward'],
  e1102: ['PSW', 'Paediatric Surgical Ward'],
  e1103: ['PSW', 'Paediatric Surgical Ward'],
  e1104: ['PSW', 'Paediatric Surgical Ward'],
  e1105: ['PSW', 'Paediatric Surgical Ward'],
  e1106: ['PSW', 'Paediatric Surgical Ward'],
  e1107: ['PSW', 'Paediatric Surgical Ward'],
  e1108: ['PSW', 'Paediatric Surgical Ward'],
};

/**
 * Authoritative label overrides sourced from backend/data/rag_docs/ahu_directory.md.
 * Covers all devices whose label cannot be derived from the formula (abbr + last-2-digits),
 * which is the majority of AHUs. Format: 'AHU-L{n}-{abbr}-{nn} — {Department}'.
 */
const LABEL_OVERRIDE: Record<string, string> = {
  // Level 1
  e0102: 'AHU-L1-BES-01 — Biomedical Engineering Services Unit',
  e0103: 'AHU-L1-MO-01 — Mortuary Services',
  e0104: 'AHU-L1-HS-01 — Housekeeping Services',
  e0105: 'AHU-L1-CA-02 — Catering & Dietetics Department',
  e0106: 'AHU-L1-CA-01 — Catering & Dietetics Department',
  e0107: 'AHU-L1-MS-02 — Medical Store',
  e0108: 'AHU-L1-MS-01 — Medical Store',
  e0109: 'AHU-L1-SS/T-01 — Security Services',
  e0110: 'AHU-L1-PAC-01 — Emergency Department',
  e0111: 'AHU-L1-OSCC-01 — Emergency Department',
  e0112: 'AHU-L1-ED-03 — Emergency Department',
  e0113: 'AHU-L1-ED-04 — Emergency Department',
  e0114: 'AHU-L1-ED-02 — Emergency Department',
  e0115: 'AHU-L1-ID-04 — Imaging Department',
  e0116: 'AHU-L1-ED-01 — Emergency Department',
  e0117: 'AHU-L1-SF-01 — Shared Facilities 1',
  e0118: 'AHU-L1-ID-03 — Imaging Department',
  e0120: 'AHU-L1-ID-02 — Imaging Department',
  e0121: 'AHU-L1-ID-01 — Imaging Department',
  // Level 1 cross-level — e0212 has "02" prefix but belongs to Level 1
  e0212: 'AHU-L1-OT-01 — Emergency Department (Paediatric)',
  // Level 2
  e0201: 'AHU-L2-CDC-03 — Child Development Centre',
  e0202: 'AHU-L2-CDC-01 — Child Development Centre',
  e0203: 'AHU-L2-CDC-04 — Child Development Centre',
  e0204: 'AHU-L2-CDC-02 — Child Development Centre',
  e0206: 'AHU-L2-CF-01 — Cafeteria',
  e0207: 'AHU-L2-MSS-01 — Medical Social Services',
  e0208: 'AHU-L2-OP-01 — Outpatient Pharmacy',
  e0209: 'AHU-L2-AR-01 — Admission & Revenue',
  e0213: 'AHU-L2-WHU-01 — Women Health Unit',
  e0214: 'AHU-L2-WHU-02 — Women Health Unit',
  e0215: 'AHU-L2-SPG-04 — O&G Specialist Clinic',
  e0216: 'AHU-L2-SPG-03 — O&G Specialist Clinic',
  e0217: 'AHU-L2-SPG-02 — O&G Specialist Clinic',
  e0218: 'AHU-L2-SPG-01 — O&G Specialist Clinic',
  // Level 3 cross-level — e0210/e0211 have "02" prefix
  e0210: 'AHU-L3-PGMC-02 — Post Graduate Medical Centre',
  e0211: 'AHU-L3-PGMC-01 — Post Graduate Medical Centre',
  // Level 3 native
  e0301: 'AHU-L3-PT-04 — Pathology Department',
  e0303: 'AHU-L3-PT-03 — Pathology Department',
  e0304: 'AHU-L3-RQA/HEU-01 — RQA Unit',
  e0306: 'AHU-L3-SPD-02 — Dental Clinic',
  e0307: 'AHU-L3-SF-01 — Shared Facilities 3',
  e0308: 'AHU-L3-SPP-03 — Paediatric Specialist Clinic',
  e0311: 'AHU-L3-SPP-01 — Paediatric Specialist Clinic',
  e0312: 'AHU-L3-SPP-02 — Paediatric Specialist Clinic',
  e0313: 'AHU-L3-SPD-01 — Dental Clinic',
  e0314: 'AHU-L3-CPC-01 — Paediatric Specialist Clinic',
  e0315: 'AHU-L3-SPD-03 — Dental Clinic',
  // Level 3 cross-level — e0401/e0402/e0423 have "04" prefix
  e0401: 'AHU-L3-PT-02 — Pathology Department',
  e0402: 'AHU-L3-PT-01 — Pathology Department',
  e0423: 'AHU-L3-BL-01 — Biophysiological Department',
  // Level 4
  e0403: 'AHU-L4-MK-01 — Shared Facilities 4',
  e0404: 'AHU-L4-PD-01 — Inpatient Pharmacy Department',
  e0406: 'AHU-CDR-01 — Inpatient Pharmacy Department',
  e0407: 'AHU-L4-PD-02 — Inpatient Pharmacy Department',
  e0408: 'AHU-L4-SCT-03 — Bone Marrow Transplant Unit',
  e0409: 'AHU-L4-SCT-01 — Bone Marrow Transplant Unit',
  e0411: 'AHU-L4-SCT-02 — Bone Marrow Transplant Unit',
  e0412: 'AHU-L4-OHR-01 — Obstetric High Risk Unit',
  e0413: 'AHU-L4-MOT-04 — Maternity OT',
  e0414: 'AHU-L4-MOT-02 — Maternity OT',
  e0415: 'AHU-L4-MOT-03 — Maternity OT',
  e0416: 'AHU-L4-MOT-01 — Maternity OT',
  e0419: 'AHU-L4-SF-01 — Shared Facilities 4',
  // Level 5 cross-level — e0622 has "06" prefix but belongs to Level 5
  e0622: 'AHU-L5-OT-10 — Main Operation Theatre Complex',
  // Level 5 native
  e0501: 'AHU-L5-PICU-02 — Paediatric Intensive Care Unit',
  e0502: 'AHU-L5-PHDU-01 — Paediatric High Dependency Unit',
  e0503: 'AHU-L5-AD-01 — Anaesthesiology Department',
  e0504: 'AHU-L5-RHU-01 — Respiratory & Haemodynamic Unit',
  e0505: 'AHU-L5-AICU-02 — Adult Intensive Care Unit',
  e0506: 'AHU-L5-AHDU-01 — Adult High Dependency Unit',
  e0507: 'AHU-L5-AICU-01 — Adult Intensive Care Unit',
  e0508: 'AHU-L5-SF-09 — Shared Facilities 5',
  e0509: 'AHU-L5-PBU-02 — Paediatric Burn Unit',
  e0510: 'AHU-L5-PICU-01 — Paediatric Intensive Care Unit',
  e0511: 'AHU-L5-PBU-01 — Paediatric Burn Unit',
  // Level 6
  e0602: 'AHU-L6-LIB-01 — Library',
  e0603: 'AHU-L6-AU-01 — Administration Unit',
  e0604: 'AHU-L6-AU-02 — Administration Unit',
  e0605: 'AHU-L6-CSSD-02 — Central Sterile Supply Unit',
  e0606: 'AHU-L6-CSSD-01 — Central Sterile Supply Unit',
  e0607: 'AHU-L6-SOC-01 — Specialist Office Complex',
  e0611: 'AHU-L6-IT-01 — Information Technology Department',
  e0625: 'AHU-L6-MR-01 — Medical Record',
  e0626: 'AHU-L6-SF-01 — Shared Facilities 6',
  e0627: 'AHU-L6-SOC-02 — Specialist Office Complex',
  e0628: 'AHU-L6-CSSD-03 — Central Sterile Supply Unit',
  // Level 7 — sub-ward abbreviations (OB1–OB4) with unit numbers from directory
  e0701: 'AHU-L7-OB3-01 — Obstetric Ward',
  e0702: 'AHU-L7-OB4-01 — Obstetric Ward',
  e0703: 'AHU-L7-OB1-01 — Obstetric Ward',
  e0704: 'AHU-L7-OB2-01 — Obstetric Ward',
  // Level 8 — sub-ward abbreviations and non-sequential unit numbers
  e0801: 'AHU-L8-CW-02 — 1st Class Ward',
  e0802: 'AHU-L8-CW-01 — 1st Class Ward',
  e0803: 'AHU-L8-OCC-01 — On Call Complex',
  e0804: 'AHU-L8-GY1-01 — Gynaecology Ward',
  e0805: 'AHU-L8-GY2-01 — Gynaecology Ward',
  // Level 9 — sub-ward abbreviations (NP, PM5, NW1, NW2) with directory unit numbers
  e0901: 'AHU-L9-NP-01 — Nephrology/Dialysis Ward',
  e0902: 'AHU-L9-NP-02 — Nephrology/Dialysis Ward',
  e0903: 'AHU-L9-PM5-01 — Paediatric Medical Ward',
  e0904: 'AHU-L9-PM5-02 — Paediatric Medical Ward',
  e0905: 'AHU-L9-NW1-01 — Neonatology Wards',
  e0906: 'AHU-L9-NW1-02 — Neonatology Wards',
  e0907: 'AHU-L9-NW2-02 — Neonatology Wards',
  e0908: 'AHU-L9-NW2-01 — Neonatology Wards',
  // Level 10 — sub-ward abbreviations (PM1–PM4) with directory unit numbers
  e1001: 'AHU-L10-PM1-02 — Paediatric Medical Ward',
  e1002: 'AHU-L10-PM1-01 — Paediatric Medical Ward',
  e1003: 'AHU-L10-PM3-01 — Paediatric Medical Ward',
  e1004: 'AHU-L10-PM3-02 — Paediatric Medical Ward',
  e1005: 'AHU-L10-PM4-02 — Paediatric Medical Ward',
  e1006: 'AHU-L10-PM4-01 — Paediatric Medical Ward',
  e1007: 'AHU-L10-PM2-01 — Paediatric Medical Ward',
  e1008: 'AHU-L10-PM2-02 — Paediatric Medical Ward',
  // Level 11 — sub-ward abbreviations (PS1–PS4) with directory unit numbers
  e1101: 'AHU-L11-PS1-02 — Paediatric Surgical Ward',
  e1102: 'AHU-L11-PS1-01 — Paediatric Surgical Ward',
  e1103: 'AHU-L11-PS2-01 — Paediatric Surgical Ward',
  e1104: 'AHU-L11-PS2-02 — Paediatric Surgical Ward',
  e1105: 'AHU-L11-PS4-02 — Paediatric Surgical Ward',
  e1106: 'AHU-L11-PS4-01 — Paediatric Surgical Ward',
  e1107: 'AHU-L11-PS3-01 — Paediatric Surgical Ward',
  e1108: 'AHU-L11-PS3-02 — Paediatric Surgical Ward',
};

/**
 * Convert a raw device ID like "e0101" to "AHU-L1-ES-01 — Engineering Services".
 * Falls back to "AHU-L{level}-{nn}" for unmapped devices.
 */
export function deviceIdToDisplay(deviceId?: string | null): string {
  if (!deviceId || typeof deviceId !== 'string') {
    return 'Unknown AHU';
  }

  // Cross-level AHUs: ID prefix doesn't match actual level — use authoritative label
  if (LABEL_OVERRIDE[deviceId]) return LABEL_OVERRIDE[deviceId];

  const entry = DEVICE_MAP[deviceId];
  const match = deviceId.match(/^e(\d{2})(\d{2})$/);
  if (!match) return deviceId;
  const level = parseInt(match[1], 10);
  const nn = match[2];
  if (!entry) return `AHU-L${level}-${nn}`;
  const [abbr, dept] = entry;
  return `AHU-L${level}-${abbr}-${nn} — ${dept}`;
}

/**
 * Replace all raw device IDs in a text string with human-readable display names.
 * The optional "AHU " prefix before a device ID is consumed to prevent "AHU AHU-L…"
 * double-prefix when LLM writes "AHU e0101" in its response.
 * Used for rendering bot message content.
 */
export function replaceDeviceIds(text?: string | null): string {
  if (!text || typeof text !== 'string') {
    return '';
  }

  return text.replace(/(?:AHU\s+)?(e\d{4})\b/g, (_, deviceId) => deviceIdToDisplay(deviceId));
}
