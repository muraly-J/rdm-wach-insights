/**
 * CombinedScoresChart tests.
 * Mocks Recharts (doesn't render in jsdom) to test the data merge logic
 * by checking what data gets passed through.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';

// Mock Recharts to avoid jsdom canvas errors
jest.mock('recharts', () => ({
  LineChart: ({ data, children }: any) => (
    <div data-testid="line-chart" data-points={data?.length ?? 0}>{children}</div>
  ),
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

// Mock formatTick utility (not under test)
jest.mock('../utils/formatTick', () => ({
  formatTickByRange: () => '',
  tickIntervalByRange: () => 10,
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { default: CombinedScoresChart } = require('../components/dashboard/CombinedScoresChart');
// Note: path is relative to this file in src/__tests__/, component is at src/components/dashboard/

const makeScoreEntry = (values: number[]) => ({
  current: values[values.length - 1],
  trend: 0,
  data: values.map((v, i) => ({ timestamp: `2026-01-0${i + 1}T00:00:00Z`, value: v })),
});

describe('CombinedScoresChart', () => {
  it('renders without crashing when scoreData is empty', () => {
    const { container } = render(
      <CombinedScoresChart scoreData={{}} timeRange="7d" />
    );
    expect(container.firstChild).toBeTruthy();
  });

  it('renders the chart with valid scoreData', () => {
    const scoreData = {
      energy_anomaly:  makeScoreEntry([0.1, 0.2, 0.3]),
      pf_degradation:  makeScoreEntry([0.2, 0.3, 0.4]),
      phase_imbalance: makeScoreEntry([0.1, 0.1, 0.2]),
      thd_drift:       makeScoreEntry([0.3, 0.3, 0.3]),
      overload:        makeScoreEntry([0.0, 0.1, 0.1]),
    };
    render(<CombinedScoresChart scoreData={scoreData} timeRange="7d" />);
    const chart = screen.getByTestId('line-chart');
    // The merge should produce 3 data points (one per timestamp in energy_anomaly)
    expect(chart.getAttribute('data-points')).toBe('3');
  });

  it('merges scores by index — each point has all five score keys', () => {
    const scoreData = {
      energy_anomaly:  makeScoreEntry([0.1, 0.5]),
      pf_degradation:  makeScoreEntry([0.2, 0.6]),
      phase_imbalance: makeScoreEntry([0.3, 0.7]),
      thd_drift:       makeScoreEntry([0.4, 0.8]),
      overload:        makeScoreEntry([0.0, 0.2]),
    };

    // Capture the data prop passed to LineChart
    let capturedData: any[] = [];
    jest.spyOn(require('recharts'), 'LineChart').mockImplementation(({ data, children }: any) => {
      capturedData = data;
      return <div data-testid="line-chart">{children}</div>;
    });

    render(<CombinedScoresChart scoreData={scoreData} timeRange="7d" />);

    expect(capturedData).toHaveLength(2);
    const keys = Object.keys(capturedData[0]);
    expect(keys).toContain('timestamp');
    expect(keys).toContain('energy_anomaly');
    expect(keys).toContain('pf_degradation');
    expect(keys).toContain('phase_imbalance');
    expect(keys).toContain('thd_drift');
    expect(keys).toContain('overload');
  });

  it('handles missing score series gracefully (no crash)', () => {
    // Only provide 2 of 5 scores — missing ones should fill as null
    const scoreData = {
      energy_anomaly: makeScoreEntry([0.1, 0.2]),
      pf_degradation: makeScoreEntry([0.3, 0.4]),
      // phase_imbalance, thd_drift, overload missing
    };
    expect(() =>
      render(<CombinedScoresChart scoreData={scoreData} timeRange="7d" />)
    ).not.toThrow();
  });

  it('renders a ReferenceArea for each off period', () => {
    const scoreData = {
      energy_anomaly:  makeScoreEntry([0.1, 0.2]),
      pf_degradation:  makeScoreEntry([0.2, 0.3]),
      phase_imbalance: makeScoreEntry([0.1, 0.1]),
      thd_drift:       makeScoreEntry([0.3, 0.3]),
      overload:        makeScoreEntry([0.0, 0.1]),
    };
    const offPeriods = [
      { start: '2026-01-01T22:00:00Z', end: '2026-01-02T06:00:00Z' },
    ];
    const { container } = render(
      <CombinedScoresChart scoreData={scoreData} timeRange="7d" offPeriods={offPeriods} />
    );
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(1);
  });

  it('renders no ReferenceArea when offPeriods is undefined', () => {
    const scoreData = {
      energy_anomaly:  makeScoreEntry([0.1]),
      pf_degradation:  makeScoreEntry([0.2]),
      phase_imbalance: makeScoreEntry([0.1]),
      thd_drift:       makeScoreEntry([0.3]),
      overload:        makeScoreEntry([0.0]),
    };
    const { container } = render(
      <CombinedScoresChart scoreData={scoreData} timeRange="7d" />
    );
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(0);
  });
});
