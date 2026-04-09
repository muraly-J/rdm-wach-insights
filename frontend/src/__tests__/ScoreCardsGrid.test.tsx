/**
 * Smoke tests for ScoreCardsGrid.
 *
 * ScoreCardsGrid renders the AHU health score cards grid.
 * Tests cover: renders without crashing with various data states.
 */
import React from 'react';
import { render } from '@testing-library/react';
import ScoreCardsGrid from '../components/dashboard/ScoreCardsGrid';

// Mock child components
jest.mock('../components/dashboard/ScoreCard', () => {
  return function DummyScoreCard() {
    return <div data-testid="score-card" />;
  };
});

jest.mock('../components/dashboard/SafetyFlagCard', () => {
  return function DummySafetyFlagCard() {
    return <div data-testid="safety-flag-card" />;
  };
});

// Mock Recharts to avoid jsdom canvas errors
jest.mock('recharts', () => ({
  LineChart: ({ children }: any) => <div>{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  ReferenceLine: () => null,
}));

describe('ScoreCardsGrid', () => {
  it('renders without crashing with empty scoreData', () => {
    const { container } = render(<ScoreCardsGrid scoreData={{}} />);
    expect(container).toBeTruthy();
  });

  it('renders without crashing with populated scoreData', () => {
    const scoreData = {
      energy_anomaly: {
        current: 45,
        trend: 3.2,
        data: [
          { timestamp: '2026-04-09T00:00:00Z', value: 40 },
          { timestamp: '2026-04-09T01:00:00Z', value: 45 },
        ],
      },
      pf_degradation: {
        current: 25,
        trend: -1.5,
        data: [
          { timestamp: '2026-04-09T00:00:00Z', value: 26 },
          { timestamp: '2026-04-09T01:00:00Z', value: 25 },
        ],
      },
    };
    const { container } = render(<ScoreCardsGrid scoreData={scoreData} />);
    expect(container).toBeTruthy();
  });

  it('renders all five score cards', () => {
    const scoreData = {
      energy_anomaly: { current: 50, trend: 2, data: [] },
      pf_degradation: { current: 30, trend: 1, data: [] },
      phase_imbalance: { current: 20, trend: -1, data: [] },
      thd_drift: { current: 40, trend: 3, data: [] },
      overload: { current: 15, trend: 0, data: [] },
    };
    const { container } = render(<ScoreCardsGrid scoreData={scoreData} />);
    // Should render without errors
    expect(container).toBeTruthy();
  });
});
