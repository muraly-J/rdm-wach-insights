// frontend/src/__tests__/DashboardControls.test.tsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { useAppStore } from '../store/useAppStore';
import DashboardControls from '../components/dashboard/DashboardControls';

// Reset Zustand store between tests
beforeEach(() => {
  useAppStore.setState({
    selectedLevel: null,
    selectedDevice: null,
    timeRange: '7d',
  });
});

const devices = [
  { id: 'e0413', name: 'AHU-01', label: 'Unit 1', department: 'Mechanical' },
  { id: 'e0414', name: 'AHU-02', label: 'Unit 2', department: 'Electrical' },
];

describe('DashboardControls — strip rendering', () => {
  it('renders LVL, DEV, RANGE segments', () => {
    render(<DashboardControls devices={[]} />);
    expect(screen.getByText('LVL')).toBeInTheDocument();
    expect(screen.getByText('DEV')).toBeInTheDocument();
    expect(screen.getByText('RANGE')).toBeInTheDocument();
  });

  it('shows — for LVL when no level selected', () => {
    render(<DashboardControls devices={[]} />);
    // LVL segment should display —
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });

  it('shows selected level number when level is set', () => {
    useAppStore.setState({ selectedLevel: 4 });
    render(<DashboardControls devices={[]} />);
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('shows current timeRange value (7d by default)', () => {
    render(<DashboardControls devices={[]} />);
    expect(screen.getByText('7d')).toBeInTheDocument();
  });
});

describe('DashboardControls — DEV segment disabled state', () => {
  it('DEV segment shows — and ignores clicks when no level selected', () => {
    render(<DashboardControls devices={devices} />);
    // DEV segment shows —
    const devSegmentValues = screen.getAllByText('—');
    // at least one — for DEV
    expect(devSegmentValues.length).toBeGreaterThan(0);
    // Clicking DEV does not open a panel
    const devLabel = screen.getByText('DEV');
    fireEvent.click(devLabel.parentElement!);
    expect(screen.queryByPlaceholderText('Search…')).not.toBeInTheDocument();
  });

  it('DEV segment opens panel when level is selected', () => {
    useAppStore.setState({ selectedLevel: 3 });
    render(<DashboardControls devices={devices} />);
    const devLabel = screen.getByText('DEV');
    fireEvent.click(devLabel.parentElement!);
    expect(screen.getByPlaceholderText('Search…')).toBeInTheDocument();
  });
});

describe('DashboardControls — Level panel', () => {
  it('opens level panel on LVL segment click', () => {
    render(<DashboardControls devices={[]} />);
    const lvlLabel = screen.getByText('LVL');
    fireEvent.click(lvlLabel.parentElement!);
    expect(screen.getByText('Level 1')).toBeInTheDocument();
    expect(screen.getByText('Level 11')).toBeInTheDocument();
  });

  it('selecting a level calls selectLevel and closes the panel', () => {
    render(<DashboardControls devices={[]} />);
    const lvlLabel = screen.getByText('LVL');
    fireEvent.click(lvlLabel.parentElement!);
    fireEvent.click(screen.getByText('Level 5'));
    expect(useAppStore.getState().selectedLevel).toBe(5);
    expect(screen.queryByText('Level 1')).not.toBeInTheDocument();
  });

  it('only one panel open at a time — opening RANGE closes LVL panel', () => {
    render(<DashboardControls devices={[]} />);
    // Open LVL panel
    fireEvent.click(screen.getByText('LVL').parentElement!);
    expect(screen.getByText('Level 1')).toBeInTheDocument();
    // Open RANGE panel
    fireEvent.click(screen.getByText('RANGE').parentElement!);
    expect(screen.queryByText('Level 1')).not.toBeInTheDocument();
    expect(screen.getByText('24h')).toBeInTheDocument();
  });
});

describe('DashboardControls — Range panel', () => {
  it('opens range panel and shows 24h / 7d / 30d', () => {
    render(<DashboardControls devices={[]} />);
    fireEvent.click(screen.getByText('RANGE').parentElement!);
    // 24h appears in the panel (may also appear in the strip value)
    const items = screen.getAllByText('24h');
    expect(items.length).toBeGreaterThan(0);
    expect(screen.getAllByText('30d').length).toBeGreaterThan(0);
  });

  it('selecting a range calls setTimeRange and closes the panel', () => {
    render(<DashboardControls devices={[]} />);
    fireEvent.click(screen.getByText('RANGE').parentElement!);
    // Find the 30d option inside the panel and click it
    const thirtyD = screen.getAllByText('30d')[0];
    fireEvent.click(thirtyD);
    expect(useAppStore.getState().timeRange).toBe('30d');
    // Panel should close — 24h should no longer be in the panel
    // (strip still shows 30d, but the list is gone)
    expect(screen.queryByText('24h')).not.toBeInTheDocument();
  });
});

describe('DashboardControls — Device search', () => {
  it('filters device list by id substring', () => {
    useAppStore.setState({ selectedLevel: 2 });
    render(<DashboardControls devices={devices} />);
    fireEvent.click(screen.getByText('DEV').parentElement!);
    const search = screen.getByPlaceholderText('Search…');
    fireEvent.change(search, { target: { value: '0413' } });
    expect(screen.getByText('e0413')).toBeInTheDocument();
    expect(screen.queryByText('e0414')).not.toBeInTheDocument();
  });

  it('shows No devices available row when devices is empty and level selected', () => {
    useAppStore.setState({ selectedLevel: 1 });
    render(<DashboardControls devices={[]} />);
    fireEvent.click(screen.getByText('DEV').parentElement!);
    expect(screen.getByText('No devices available')).toBeInTheDocument();
    expect(screen.getByText('All AHUs')).toBeInTheDocument();
  });
});
