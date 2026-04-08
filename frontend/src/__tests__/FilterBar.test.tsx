import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import FilterBar from '../components/nav/FilterBar';
import { useAppStore } from '../store/useAppStore';

beforeEach(() => {
  useAppStore.setState({
    selectedLevel: null,
    selectedDevice: null,
    timeRange: '7d',
    dashboardMode: 'simple',
    deepDiveSubMode: 'single',
    compareDevices: [],
  });
});

const devices = [
  { id: 'e0101', label: 'AHU-L1-ES-01', department: 'Engineering Services', area: '' },
  { id: 'e0202', label: 'AHU-L1-MS-01', department: 'Medical Services', area: '' },
];

describe('FilterBar', () => {
  it('renders RDM-WACH brand name', () => {
    render(<FilterBar levelDevices={devices} />);
    expect(screen.getByText('RDM-WACH')).toBeInTheDocument();
  });

  it('shows All Levels when no level selected', () => {
    render(<FilterBar levelDevices={devices} />);
    expect(screen.getByText(/All Levels/i)).toBeInTheDocument();
  });

  it('shows active time range highlighted', () => {
    render(<FilterBar levelDevices={devices} />);
    expect(screen.getByText('7d')).toBeInTheDocument();
  });

  it('clicking a time range updates the store', () => {
    render(<FilterBar levelDevices={devices} />);
    fireEvent.click(screen.getByText('24h'));
    expect(useAppStore.getState().timeRange).toBe('24h');
  });

  it('shows All as time range option', () => {
    render(<FilterBar levelDevices={devices} />);
    expect(screen.getByText('All')).toBeInTheDocument();
  });
});
