import React from 'react';
import { render } from '@testing-library/react';

// Mock ReferenceArea so we can inspect it in jsdom
jest.mock('recharts', () => ({
  ReferenceArea: ({ x1, x2, fill, label }: any) => (
    <div
      data-testid="reference-area"
      data-x1={x1}
      data-x2={x2}
      data-fill={fill}
      data-label={label?.value}
    />
  ),
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { renderOffPeriodAreas } = require('../utils/offPeriodAreas');

describe('renderOffPeriodAreas', () => {
  it('returns null when offPeriods is undefined', () => {
    const { container } = render(<div>{renderOffPeriodAreas(undefined)}</div>);
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(0);
  });

  it('returns null when offPeriods is empty', () => {
    const { container } = render(<div>{renderOffPeriodAreas([])}</div>);
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(0);
  });

  it('renders one ReferenceArea per off period', () => {
    const periods = [
      { start: '2026-04-01T22:00:00Z', end: '2026-04-02T06:00:00Z' },
      { start: '2026-04-03T23:00:00Z', end: '2026-04-04T07:00:00Z' },
    ];
    const { container } = render(<div>{renderOffPeriodAreas(periods)}</div>);
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(2);
  });

  it('passes correct x1/x2 from period start/end', () => {
    const periods = [{ start: '2026-04-01T22:00:00Z', end: '2026-04-02T06:00:00Z' }];
    const { container } = render(<div>{renderOffPeriodAreas(periods)}</div>);
    const area = container.querySelector('[data-testid="reference-area"]');
    expect(area?.getAttribute('data-x1')).toBe('2026-04-01T22:00:00Z');
    expect(area?.getAttribute('data-x2')).toBe('2026-04-02T06:00:00Z');
  });

  it('renders the OFF label', () => {
    const periods = [{ start: '2026-04-01T22:00:00Z', end: '2026-04-02T06:00:00Z' }];
    const { container } = render(<div>{renderOffPeriodAreas(periods)}</div>);
    const area = container.querySelector('[data-testid="reference-area"]');
    expect(area?.getAttribute('data-label')).toBe('OFF');
  });
});
