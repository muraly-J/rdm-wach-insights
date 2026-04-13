import { deviceIdToDisplay, replaceDeviceIds } from '../utils/deviceNames';

describe('deviceNames utilities', () => {
    it('formats a known device ID correctly', () => {
        expect(deviceIdToDisplay('e0101')).toBe('AHU-L1-ES-01 — Engineering Services');
    });

    it('passes through unknown device IDs unchanged', () => {
        expect(deviceIdToDisplay('foo123')).toBe('foo123');
    });

    it('returns a safe fallback for undefined/invalid device IDs', () => {
        expect(deviceIdToDisplay(undefined)).toBe('Unknown AHU');
        expect(deviceIdToDisplay(null)).toBe('Unknown AHU');
    });

    it('replaces raw device IDs inside text with readable names', () => {
        const text = 'Devices: e0101, e0201, and e9999.';
        expect(replaceDeviceIds(text)).toContain('AHU-L1-ES-01 — Engineering Services');
        expect(replaceDeviceIds(text)).toContain('AHU-L2-CDC-01');
        expect(replaceDeviceIds(text)).toContain('AHU-L99-99');
    });

    it('returns empty string when replaceDeviceIds receives no content', () => {
        expect(replaceDeviceIds(undefined)).toBe('');
        expect(replaceDeviceIds(null)).toBe('');
    });
});
