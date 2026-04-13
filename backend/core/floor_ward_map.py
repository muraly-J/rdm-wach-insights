"""
core/floor_ward_map.py
──────────────────────
Floor and ward grouping for WACH Insight.

Maps floor names (Level 1-11) and ward/dept names to device IDs.
Used to translate natural language queries like "Level 3" or "O&G Specialist Clinic"
into device_id lists for InfluxDB queries.
"""

import re

# Floor to device ID mapping
FLOOR_MAP = {
    'L01': ['e0101', 'e0102', 'e0103', 'e0104', 'e0105', 'e0106', 'e0107', 'e0108',
            'e0109', 'e0110', 'e0111', 'e0112', 'e0113', 'e0114', 'e0115', 'e0116',
            'e0117', 'e0118', 'e0120', 'e0121'],
    'L02': ['e0201', 'e0202', 'e0203', 'e0204', 'e0205', 'e0206', 'e0207', 'e0208',
            'e0209', 'e0212', 'e0213', 'e0214', 'e0215', 'e0216', 'e0217', 'e0218'],
    'L03': ['e0210', 'e0211', 'e0301', 'e0303', 'e0304', 'e0306', 'e0307', 'e0308',
            'e0311', 'e0312', 'e0313', 'e0314', 'e0315', 'e0401', 'e0402', 'e0403'],
    'L04': ['e0403', 'e0404', 'e0406', 'e0407', 'e0408', 'e0409', 'e0411', 'e0412',
            'e0413', 'e0414', 'e0415', 'e0416', 'e0419'],
    'L05': ['e0501', 'e0502', 'e0503', 'e0504', 'e0505', 'e0506', 'e0507', 'e0508',
            'e0509', 'e0510', 'e0511'],
    'L06': ['e0602', 'e0603', 'e0604', 'e0605', 'e0606', 'e0607', 'e0611', 'e0622',
            'e0625', 'e0626', 'e0627', 'e0628'],
    'L07': ['e0701', 'e702', 'e0703', 'e0704'],
    'L08': ['e0801', 'e0802', 'e0803', 'e0804', 'e0805'],
    'L09': ['e0901', 'e0902', 'e0903', 'e0904', 'e0905', 'e0906', 'e0907', 'e0908'],
    'L10': ['e1001', 'e1002', 'e1003', 'e1004', 'e1005', 'e1006', 'e1007', 'e1008'],
    'L11': ['e1101', 'e1102', 'e1103', 'e1104', 'e1105', 'e1106', 'e1107', 'e1108'],
}

# Ward/Department to device ID mapping
WARD_MAP = {
    'Engineering Services': ['e0101'],
    'Biomedical Engineering Services Unit': ['e0102'],
    'Mortuary Services': ['e0103'],
    'Housekeeping Services': ['e0104'],
    'Catering & Dietetics Department': ['e0105', 'e0106'],
    'Medical Store': ['e0107', 'e0108'],
    'Security Services': ['e0109'],
    'Emergency Department': ['e0110', 'e0111', 'e0112', 'e0113', 'e0114', 'e0115', 'e0116', 'e0117'],
    'Imaging Department': ['e0115', 'e0116', 'e0118', 'e0120', 'e0121'],
    'Child Development Centre': ['e0201', 'e0202', 'e0203', 'e0204', 'e0205'],
    'Cafeteria': ['e0206'],
    'Medical Social Services': ['e0207'],
    'Outpatient Pharmacy': ['e0208'],
    'Admission & Revenue': ['e0209'],
    'Post Graduate Medical Centre': ['e0210', 'e0211'],
    'Women Health Unit': ['e0213', 'e0214'],
    'O&G Specialist Clinic': ['e0215', 'e0216', 'e0217', 'e0218'],
    'Pathology Department': ['e0301', 'e0303', 'e0304', 'e0401', 'e0402'],
    'RQA Unit': ['e0304'],
    'Dental Clinic': ['e0306', 'e0313', 'e0315'],
    'Shared Facilities 3': ['e0307'],
    'Paediatric Specialist Clinic': ['e0308', 'e0311', 'e0312', 'e0314'],
    'Biophysiological Department': ['e0323'],  # Note: e0323 may not exist
    'Inpatient Pharmacy Department': ['e0404', 'e0406', 'e0407'],
    'Bone Marrow Transplant Unit': ['e0408', 'e0409', 'e0411'],
    'Obstetric High Risk Unit': ['e0412'],
    'Maternity OT': ['e0413', 'e0414', 'e0415', 'e0416'],
    'Shared Facilities 4': ['e0419'],
    'Paediatric Intensive Care Unit': ['e0501', 'e0510'],
    'Paediatric High Dependency Unit': ['e0502'],
    'Anaesthesiology Department': ['e0503'],
    'Respiratory & Haemodynamic Unit': ['e0504'],
    'Adult Intensive Care Unit': ['e0505', 'e0507'],
    'Adult High Dependency Unit': ['e0506'],
    'Paediatric Burn Unit': ['e0509', 'e0511'],
    'Shared Facilities 5': ['e0508'],
    'Main Operation Theatre Complex': ['e0622'],
    'Library': ['e0602'],
    'Administration Unit': ['e0603', 'e0604'],
    'Central Sterile Supply Unit': ['e0605', 'e0606', 'e0628'],
    'Specialist Office Complex': ['e0607', 'e0627'],
    'Information Technology Department': ['e0611'],
    'Medical Record': ['e0625'],
    'Shared Facilities 6': ['e0626'],
    'Inpatient Wards': [
        'e0701', 'e0702', 'e0703', 'e0704',
        'e0801', 'e0802', 'e0803', 'e0804', 'e0805',
        'e0901', 'e0902', 'e0903', 'e0904',
        'e0905', 'e0906', 'e0907', 'e0908',
        'e1001', 'e1002', 'e1003', 'e1004',
        'e1005', 'e1006', 'e1007', 'e1008',
        'e1101', 'e1102', 'e1103', 'e1104',
        'e1105', 'e1106', 'e1107', 'e1108',
    ],
    '1st Class Ward': ['e0801', 'e0802'],
    'On Call Complex': ['e0803'],
    'Gynaecology Ward': ['e0804', 'e0805'],
    'Nephrology / Dialysis Ward': ['e0901', 'e0902'],
    'Paediatric Medical Ward': [
        'e0903', 'e0904', 'e1001', 'e1002',
        'e1003', 'e1004', 'e1005', 'e1006',
        'e1007', 'e1008',
    ],
    'Neonatology Wards': ['e0905', 'e0906', 'e0907', 'e0908'],
    'Paediatric Surgical Ward': [
        'e1101', 'e1102', 'e1103', 'e1104',
        'e1105', 'e1106', 'e1107', 'e1108',
    ],
    'Obstetric Ward': ['e0701', 'e0702', 'e0703', 'e0704'],
}


def resolve_floor_ids(level_name: str) -> list[str]:
    """
    Resolve a floor name like 'Level 3' or 'L03' to device IDs.
    Returns empty list if not recognized.
    """
    # Normalize input
    normalized = level_name.strip().lower()

    # Try "Level X" format
    if normalized.startswith('level '):
        try:
            level_num = int(normalized.replace('level ', '').strip())
            level_code = f'L{level_num:02d}'
            return FLOOR_MAP.get(level_code, [])
        except ValueError:
            pass

    # Try direct level code like 'L03'
    if normalized.startswith('l') and len(normalized) == 3:
        return FLOOR_MAP.get(normalized.upper(), [])

    # Try floor number only
    try:
        level_num = int(normalized)
        level_code = f'L{level_num:02d}'
        return FLOOR_MAP.get(level_code, [])
    except ValueError:
        pass

    return []


def resolve_ward_ids(ward_name: str) -> list[str]:
    """
    Resolve a ward/department name to device IDs.
    Returns empty list if not recognized.
    """
    normalized = ward_name.strip()

    # Direct match
    if normalized in WARD_MAP:
        return WARD_MAP[normalized]

    # Case-insensitive match
    for ward in WARD_MAP:
        if ward.lower() == normalized.lower():
            return WARD_MAP[ward]

    return []


def resolve_floor_or_ward(query_text: str, device_ids: list[str]) -> list[str]:
    """
    If device_ids is empty but query_text mentions a floor/ward,
    resolve it to actual device IDs.

    Examples:
        "how is level 3 performing?" -> ['e0210', 'e0211', ...]
        "show power for level 1 last week" -> ['e0101', 'e0102', ...]
    """
    if device_ids:
        # Already has specific devices
        return device_ids

    # Extract floors from query text
    extracted_floors = extract_floor_from_text(query_text)
    if extracted_floors:
        all_devices = []
        for floor in extracted_floors:
            resolved = resolve_floor_ids(floor)
            if resolved:
                all_devices.extend(resolved)
        if all_devices:
            return list(dict.fromkeys(all_devices))  # deduplicate while preserving order

    # Extract wards from query text
    extracted_wards = extract_ward_from_text(query_text)
    if extracted_wards:
        all_devices = []
        for ward in extracted_wards:
            resolved = resolve_ward_ids(ward)
            if resolved:
                all_devices.extend(resolved)
        if all_devices:
            return list(dict.fromkeys(all_devices))  # deduplicate while preserving order

    return []


def get_all_floors() -> list[str]:
    """Return sorted list of all available floors (L01-L11)."""
    return sorted(FLOOR_MAP.keys())


def get_all_wards() -> list[str]:
    """Return sorted list of all available wards/departments."""
    return sorted(WARD_MAP.keys())


def get_floor_label(level_code: str) -> str:
    """Convert L03 -> 'Level 3'."""
    if not level_code or not level_code.startswith('L'):
        return level_code
    try:
        num = int(level_code[1:])
        return f'Level {num}'
    except ValueError:
        return level_code


def extract_floor_from_text(query: str) -> list[str]:
    """
    Extract floor level mentions from a natural language query.
    
    Examples:
        "Level 1 power" -> ['L01']
        "show me floor 3 devices" -> ['L03']
        "Level 10 and Level 11" -> ['L10', 'L11']
        "show devices on floor 5" -> ['L05']
    
    Returns list of level codes (e.g., ['L01', 'L03']).
    """
    floors_found = []

    # Pattern 1: "Level X" (with word boundary to avoid matching "wheeleD")
    level_matches = re.findall(r'\blevel\s+(\d+)\b', query, re.IGNORECASE)
    for match in level_matches:
        level_num = int(match)
        if 1 <= level_num <= 11:
            code = f'L{level_num:02d}'
            if code not in floors_found:
                floors_found.append(code)

    # Pattern 2: "Floor X" or "the floor X"
    floor_matches = re.findall(r'\b(?:floor|level\s+)\s*(\d+)\b', query, re.IGNORECASE)
    for match in floor_matches:
        level_num = int(match)
        if 1 <= level_num <= 11:
            code = f'L{level_num:02d}'
            if code not in floors_found:
                floors_found.append(code)

    # Pattern 3: Direct "L01" style mentions
    direct_matches = re.findall(r'\b(L\d{2})\b', query)
    for match in direct_matches:
        if match not in floors_found:
            floors_found.append(match)

    return sorted(floors_found)


def extract_ward_from_text(query: str) -> list[str]:
    """
    Extract ward/department names from a natural language query.
    
    Examples:
        "O&G Specialist Clinic" -> ['O&G Specialist Clinic']
        "show me devices in the Emergency Department" -> ['Emergency Department']
    
    Returns list of ward names that match exactly.
    """
    wards_found = []
    query_lower = query.lower()

    for ward_name in WARD_MAP:
        if ward_name.lower() in query_lower:
            if ward_name not in wards_found:
                wards_found.append(ward_name)

    return wards_found
