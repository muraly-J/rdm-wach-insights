import React from 'react';
import { render, waitFor } from '@testing-library/react';

jest.mock('recharts', () => ({
  LineChart: ({ children }: any) => <div>{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  ReferenceArea: ({ x1, x2 }: any) => (
    <div data-testid="reference-area" data-x1={x1} data-x2={x2} />
  ),
}));

jest.mock('../api/client', () => ({
  fetchMeasurements: jest.fn().mockResolvedValue({
    measurements: {
      active_power: [
        { timestamp: '2026-04-01T00:00:00Z', value: 10 },
        { timestamp: '2026-04-01T01:00:00Z', value: 11 },
      ],
    },
  }),
}));

jest.mock('../constants/metricGroups', () => ({
  SCORE_METRIC_GROUPS: [],
  METRIC_META: { active_power: { label: 'Active Power', unit: 'kW' } },
}));

jest.mock('../constants/chartConfig', () => ({
  CHART_CONFIG: { HEIGHTS: { LOADING_STATE: 180, SINGLE_DEVICE: 300 }, MARGINS: { SINGLE: {} }, CHART_COLORS: ['#4fbd95'] },
}));

jest.mock('../hooks/useMetricSelection', () => ({
  useMetricSelection: () => ({ selectedMetrics: ['active_power'], setSelectedMetrics: jest.fn(), toggleMetric: jest.fn() }),
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { default: SingleDeviceChart } = require('../components/deepdive/SingleDeviceChart');

describe('SingleDeviceChart', () => {
  it('renders without opacity dimming style regardless of isOn', () => {
    const { container } = render(
      <SingleDeviceChart deviceId="e0101" deviceLabel="AHU-01" timeRange="7d" isOn={false} />
    );
    // The wrapper div should not have opacity or grayscale inline styles
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper?.style?.opacity).not.toBe('0.45');
    expect(wrapper?.style?.filter).not.toContain('grayscale');
  });

  it('renders ReferenceArea for each off period', async () => {
    const offPeriods = [{ start: '2026-04-01T22:00:00Z', end: '2026-04-02T06:00:00Z' }];
    const { container } = render(
      <SingleDeviceChart deviceId="e0101" deviceLabel="AHU-01" timeRange="7d" offPeriods={offPeriods} />
    );
    await waitFor(() => {
      expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(1);
    });
  });
});
