import { resolveDeviceLabel, buildLabelMap } from '../utils/deviceLabel';

const devices = [
  { id: 'e0101', label: 'AHU-L1-ES-01', department: 'Engineering Services', area: 'Zone A' },
  { id: 'e0202', label: 'AHU-L2-MS-01', department: 'Medical Services', area: 'Zone B' },
  { id: 'e0303', label: 'AHU-L3-01', department: '', area: '' },
];

describe('resolveDeviceLabel', () => {
  it('returns label — department when both present', () => {
    expect(resolveDeviceLabel('e0101', devices)).toBe('AHU-L1-ES-01 — Engineering Services');
  });

  it('returns label only when department is empty', () => {
    expect(resolveDeviceLabel('e0303', devices)).toBe('AHU-L3-01');
  });

  it('returns the raw id when device is not found', () => {
    expect(resolveDeviceLabel('e9999', devices)).toBe('e9999');
  });
});

describe('buildLabelMap', () => {
  it('builds a map from id to human label', () => {
    const map = buildLabelMap(devices);
    expect(map['e0101']).toBe('AHU-L1-ES-01 — Engineering Services');
    expect(map['e0202']).toBe('AHU-L2-MS-01 — Medical Services');
    expect(map['e0303']).toBe('AHU-L3-01');
  });

  it('returns empty object for empty input', () => {
    expect(buildLabelMap([])).toEqual({});
  });
});
