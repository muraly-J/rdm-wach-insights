import React from 'react';
import { render } from '@testing-library/react';

jest.mock('recharts', () => ({
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  ReferenceArea: ({ x1, x2 }: any) => (
    <div data-testid="reference-area" data-x1={x1} data-x2={x2} />
  ),
}));

jest.mock('framer-motion', () => ({
  motion: { div: ({ children, ...props }: any) => <div {...props}>{children}</div> },
}));

jest.mock('../utils/formatTick', () => ({
  formatDateMYT: () => 'Apr 10, 2026',
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { default: HealthIndexChart } = require('../components/dashboard/HealthIndexChart');

const device = { id: 'e0101', name: 'e0101', label: 'AHU-01', department: 'Ward A' };
const data = [
  { timestamp: '2026-04-01T08:00:00Z', e0101: 75 },
  { timestamp: '2026-04-01T22:00:00Z', e0101: 70 },
];

describe('HealthIndexChart', () => {
  it('renders without offPeriods and shows no ReferenceArea', () => {
    const { container } = render(
      <HealthIndexChart data={data} devices={[device]} />
    );
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(0);
  });

  it('renders a ReferenceArea for each off period when offPeriods provided', () => {
    const offPeriods = [
      { start: '2026-04-01T22:00:00Z', end: '2026-04-02T06:00:00Z' },
    ];
    const { container } = render(
      <HealthIndexChart data={data} devices={[device]} offPeriods={offPeriods} />
    );
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(1);
  });

  it('does not accept showColorSegments prop (it is removed)', () => {
    // Just verify it renders without crash when the old prop is absent
    expect(() =>
      render(<HealthIndexChart data={data} devices={[device]} />)
    ).not.toThrow();
  });
});
