import React from 'react';
import { render, screen } from '@testing-library/react';
import KPIStrip from '../components/dashboard/KPIStrip';
import type { SiteSummaryData } from '../types';

const mockSummary: SiteSummaryData = {
  totalAHUs: 47,
  avgSiteHealth: 82.4,
  ahusInAlert: 6,
  estMonthlyCostMYR: 0,
  starAHU: { id: 'e0303', name: 'AHU-L3-ES-02', level: 3, healthScore: 97, monthlyCostMYR: 0, safetyFlags: 0 },
  criticalAHU: { id: 'e0707', name: 'AHU-L7-MS-01', level: 7, healthScore: 43, monthlyCostMYR: 0, safetyFlags: 2 },
  levelTiles: [],
  trendDeltas: [],
};

describe('KPIStrip', () => {
  it('renders site health score', () => {
    render(<KPIStrip summary={mockSummary} selectedLevel={null} selectedDevice={null} deviceLabel={null} deviceHealth={null} />);
    expect(screen.getByText('82.4')).toBeInTheDocument();
  });

  it('renders total AHU count', () => {
    render(<KPIStrip summary={mockSummary} selectedLevel={null} selectedDevice={null} deviceLabel={null} deviceHealth={null} />);
    expect(screen.getByText('47')).toBeInTheDocument();
  });

  it('renders in-alert count', () => {
    render(<KPIStrip summary={mockSummary} selectedLevel={null} selectedDevice={null} deviceLabel={null} deviceHealth={null} />);
    expect(screen.getByText('6')).toBeInTheDocument();
  });

  it('renders best AHU label', () => {
    render(<KPIStrip summary={mockSummary} selectedLevel={null} selectedDevice={null} deviceLabel={null} deviceHealth={null} />);
    expect(screen.getByText('AHU-L3-ES-02')).toBeInTheDocument();
  });

  it('renders worst AHU label', () => {
    render(<KPIStrip summary={mockSummary} selectedLevel={null} selectedDevice={null} deviceLabel={null} deviceHealth={null} />);
    expect(screen.getByText('AHU-L7-MS-01')).toBeInTheDocument();
  });

  it('shows device health when device is selected', () => {
    render(<KPIStrip summary={mockSummary} selectedLevel={1} selectedDevice="e0101" deviceLabel="AHU-L1-ES-01 — Engineering Services" deviceHealth={88} />);
    expect(screen.getByText('88')).toBeInTheDocument();
  });
});
