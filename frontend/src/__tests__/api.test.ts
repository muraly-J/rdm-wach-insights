/**
 * API client tests. Mocks global fetch via jest.fn() — no extra dependencies.
 */
import { fetchHealthIndex, fetchScoreBreakdown, fetchRawScoreRelationship } from '../api/client';

const mockFetch = (body: unknown, status = 200) => {
  const mockFn = jest.fn().mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as Response);
  global.fetch = mockFn;
  return mockFn;
};

afterEach(() => {
  jest.restoreAllMocks();
});

describe('fetchHealthIndex', () => {
  it('returns parsed JSON on 200', async () => {
    const payload = [{ timestamp: '2026-01-01T00:00:00Z', health_index: 82 }];
    mockFetch(payload);
    const result = await fetchHealthIndex(1, '7d');
    expect(result).toEqual(payload);
  });

  it('throws on 404', async () => {
    mockFetch({ detail: 'Not found' }, 404);
    await expect(fetchHealthIndex(99, '7d')).rejects.toThrow();
  });
});

describe('fetchScoreBreakdown', () => {
  it('returns a list with device_id field on 200', async () => {
    const payload = [{ device_id: 'e0101', health_index: 75, scores: {} }];
    mockFetch(payload);
    const result = await fetchScoreBreakdown(1, '7d');
    expect(Array.isArray(result)).toBe(true);
    expect(result[0]).toHaveProperty('device_id');
  });

  it('throws on 401 unauthorized', async () => {
    mockFetch({ detail: 'Unauthorized' }, 401);
    await expect(fetchScoreBreakdown(1, '7d')).rejects.toThrow();
  });
});

describe('fetchRawScoreRelationship', () => {
  it('calls the correct URL', async () => {
    const mockFn = mockFetch({ device_id: 'e0101', scores: {} });
    await fetchRawScoreRelationship('e0101', '7d');
    const calledUrl = mockFn.mock.calls[0][0] as string;
    expect(calledUrl).toContain('/device/e0101/raw-score-relationship');
    expect(calledUrl).toContain('range=7d');
  });

  it('returns a non-null result on 200', async () => {
    mockFetch({ device_id: 'e0101', scores: { energy_anomaly: {} } });
    const result = await fetchRawScoreRelationship('e0101', '24h');
    expect(result).toBeTruthy();
  });
});
