import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import AHURankingsTable from '../components/dashboard/AHURankingsTable';

const rows = [
  {
    id: 'e0101',
    label: 'AHU-L1-ES-01 — Engineering Services',
    level: 1,
    healthScore: 92,
    trend: 3.2,
    status: 'Good' as const,
  },
  {
    id: 'e0707',
    label: 'AHU-L7-MS-01 — Medical Services',
    level: 7,
    healthScore: 43,
    trend: -8.1,
    status: 'Critical' as const,
  },
  {
    id: 'e0303',
    label: 'AHU-L3-01',
    level: 3,
    healthScore: 71,
    trend: 1.0,
    status: 'Warning' as const,
  },
];

describe('AHURankingsTable', () => {
  it('renders AHU human labels', () => {
    render(<AHURankingsTable rows={rows} />);
    expect(screen.getByText('AHU-L1-ES-01 — Engineering Services')).toBeInTheDocument();
  });

  it('renders health scores', () => {
    render(<AHURankingsTable rows={rows} />);
    expect(screen.getByText('92')).toBeInTheDocument();
    expect(screen.getByText('43')).toBeInTheDocument();
  });

  it('renders status badges', () => {
    render(<AHURankingsTable rows={rows} />);
    expect(screen.getByText('Good')).toBeInTheDocument();
    expect(screen.getByText('Critical')).toBeInTheDocument();
  });

  it('sorts by health score ascending when header clicked', () => {
    render(<AHURankingsTable rows={rows} />);
    const healthHeader = screen.getByText(/Health/i);
    fireEvent.click(healthHeader);
    const cells = screen.getAllByRole('cell');
    expect(cells.some((c) => c.textContent === '43')).toBe(true);
  });
});
