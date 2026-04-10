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
  e0215: ['OGS', "O&G Specialist Clinic"],
  e0216: ['OGS', "O&G Specialist Clinic"],
  e0217: ['OGS', "O&G Specialist Clinic"],
  e0218: ['OGS', "O&G Specialist Clinic"],
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

const DEVICE_RE = /\be(\d{2})(\d{2})\b/g;

/**
 * Convert a raw device ID like "e0101" to "AHU-L1-ES-01 — Engineering Services".
 * Falls back to "AHU-L{level}-{nn}" for unmapped devices.
 */
export function deviceIdToDisplay(deviceId: string): string {
  const entry = DEVICE_MAP[deviceId];
  const match = deviceId.match(/^e(\d{2})(\d{2})$/);
  if (!match) return deviceId;
  const level = parseInt(match[1], 10);
  const nn = match[2];
  if (!entry) return `AHU-L${level}-${nn}`;
  const [abbr, dept] = entry;
  return `AHU-L${level}-${abbr}-${nn} \u2014 ${dept}`;
}

/**
 * Replace all raw device IDs in a text string with human-readable display names.
 * Used for rendering bot message content.
 */
export function replaceDeviceIds(text: string): string {
  return text.replace(DEVICE_RE, (match) => deviceIdToDisplay(match));
}
