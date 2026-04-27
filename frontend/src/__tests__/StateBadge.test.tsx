import React from 'react';
import { render, screen } from '@testing-library/react';
import StateBadge from '../components/shared/StateBadge';

describe('StateBadge', () => {
  it('renders On state', () => {
    render(<StateBadge state="On" />);
    expect(screen.getByText(/On/)).toBeInTheDocument();
  });

  it('renders Inactive state', () => {
    render(<StateBadge state="Inactive" />);
    expect(screen.getByText(/Inactive/)).toBeInTheDocument();
  });

  it('adds tooltip for Off_Stale when lastMeasured provided', () => {
    const ts = new Date(Date.now() - 50 * 3_600_000).toISOString(); // 50h ago
    render(<StateBadge state="Off_Stale" lastMeasured={ts} />);
    const badge = screen.getByText(/Off · Stale/);
    expect(badge.closest('[title]')).toHaveAttribute('title', expect.stringContaining('ago'));
  });
});
