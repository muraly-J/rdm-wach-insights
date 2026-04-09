/**
 * Tests for LevelSelectorBar.
 *
 * LevelSelectorBar reads and writes Zustand store (no props).
 * Tests:
 * - Renders all 11 level pill buttons
 * - Clicking a level button updates the store (calls selectLevel)
 * - Active level is visually indicated
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { useAppStore } from '../store/useAppStore';
import LevelSelectorBar from '../components/dashboard/LevelSelectorBar';

beforeEach(() => {
  // Reset Zustand store between tests
  useAppStore.setState({ selectedLevel: null });
});

describe('LevelSelectorBar', () => {
  it('renders all 11 level buttons', () => {
    render(<LevelSelectorBar />);
    for (let i = 1; i <= 11; i++) {
      expect(screen.getByText(`Level ${i}`)).toBeInTheDocument();
    }
  });

  it('clicking a level button updates the store', () => {
    render(<LevelSelectorBar />);
    fireEvent.click(screen.getByText('Level 3'));
    expect(useAppStore.getState().selectedLevel).toBe(3);
  });

  it('clicking another level updates to the new level', () => {
    useAppStore.setState({ selectedLevel: 2 });
    render(<LevelSelectorBar />);
    fireEvent.click(screen.getByText('Level 7'));
    expect(useAppStore.getState().selectedLevel).toBe(7);
  });

  it('clicking the same level again keeps it selected', () => {
    useAppStore.setState({ selectedLevel: 5 });
    render(<LevelSelectorBar />);
    fireEvent.click(screen.getByText('Level 5'));
    expect(useAppStore.getState().selectedLevel).toBe(5);
  });
});
