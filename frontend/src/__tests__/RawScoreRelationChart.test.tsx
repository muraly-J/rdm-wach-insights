import React from 'react';
import { render } from '@testing-library/react';

jest.mock('recharts', () => ({
  LineChart: ({ children }: any) => <div>{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ReferenceLine: () => null,
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  ReferenceArea: ({ x1, x2 }: any) => (
    <div data-testid="reference-area" data-x1={x1} data-x2={x2} />
  ),
}));

jest.mock('../utils/formatTick', () => ({
  formatTickByRange: () => '',
  tickIntervalByRange: () => 5,
  formatDateMYT: () => '',
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { default: RawScoreRelationChart } = require('../components/dashboard/derivation/RawScoreRelationChart');

const makeProps = () => ({
  scoreName: 'Energy Anomaly',
  series: [{ label: 'δ kWh', unit: 'kWh', style: 'solid', data: [{ timestamp: '2026-04-01T00:00:00Z', value: 1.0 }] }],
  scoreData: [{ timestamp: '2026-04-01T00:00:00Z', value: 70 }],
  referenceLines: [],
  chartColor: '#3B82F6',
  timeRange: '7d' as const,
});

describe('RawScoreRelationChart', () => {
  it('renders no ReferenceArea when offPeriods is absent', () => {
    const { container } = render(<RawScoreRelationChart {...makeProps()} />);
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(0);
  });

  it('renders a ReferenceArea per off period', () => {
    const offPeriods = [{ start: '2026-04-01T22:00:00Z', end: '2026-04-02T06:00:00Z' }];
    const { container } = render(<RawScoreRelationChart {...makeProps()} offPeriods={offPeriods} />);
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(1);
  });
});
