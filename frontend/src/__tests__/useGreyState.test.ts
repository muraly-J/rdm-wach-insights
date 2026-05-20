import { renderHook } from '@testing-library/react';
import { useGreyState, STALE_HOURS, CONFIDENCE_MIN } from '../hooks/useGreyState';

describe('useGreyState', () => {
  test('On + fresh + high confidence → not grey', () => {
    const { result } = renderHook(() =>
      useGreyState({
        operationalState: 'On',
        lastMeasured: new Date().toISOString(),
        confidence: 0.9,
      })
    );
    expect(result.current.isGrey).toBe(false);
    expect(result.current.reason).toBeNull();
  });

  test('isOn=false → grey, reason=off', () => {
    const { result } = renderHook(() => useGreyState({ isOn: false }));
    expect(result.current.isGrey).toBe(true);
    expect(result.current.reason).toBe('off');
  });

  test('operationalState Off_Stale → grey, reason=stale', () => {
    const { result } = renderHook(() =>
      useGreyState({ operationalState: 'Off_Stale', lastMeasured: '2020-01-01T00:00:00Z' })
    );
    expect(result.current.isGrey).toBe(true);
    expect(result.current.reason).toBe('stale');
  });

  test('lastMeasured older than STALE_HOURS → grey, reason=stale', () => {
    const old = new Date(Date.now() - (STALE_HOURS + 1) * 3600_000).toISOString();
    const { result } = renderHook(() =>
      useGreyState({ operationalState: 'On', lastMeasured: old })
    );
    expect(result.current.isGrey).toBe(true);
    expect(result.current.reason).toBe('stale');
  });

  test('confidence below CONFIDENCE_MIN → grey, reason=low_confidence', () => {
    const { result } = renderHook(() =>
      useGreyState({ operationalState: 'On', confidence: CONFIDENCE_MIN - 0.01 })
    );
    expect(result.current.isGrey).toBe(true);
    expect(result.current.reason).toBe('low_confidence');
  });

  test('off precedence over stale + low_confidence', () => {
    const { result } = renderHook(() =>
      useGreyState({
        operationalState: 'Off',
        confidence: 0.1,
        lastMeasured: '2020-01-01T00:00:00Z',
      })
    );
    expect(result.current.reason).toBe('off');
  });

  test('returns visual constants when grey', () => {
    const { result } = renderHook(() => useGreyState({ isOn: false }));
    expect(result.current.opacity).toBe(0.4);
    expect(result.current.filter).toBe('grayscale(85%) saturate(0.4)');
  });

  test('returns identity treatment when not grey', () => {
    const { result } = renderHook(() => useGreyState({ operationalState: 'On' }));
    expect(result.current.opacity).toBe(1);
    expect(result.current.filter).toBe('none');
  });
});
