import React from 'react';
import { useAppStore, DashboardMode } from '../../store/useAppStore';

const MODES: DashboardMode[] = ['simple', 'deepdive'];

const ModeToggle: React.FC = () => {
  const { dashboardMode, setDashboardMode } = useAppStore();

  return (
    <div
      style={{
        display: 'inline-flex',
        background: '#1a2234',
        border: '1px solid #2a3649',
        borderRadius: 10,
        padding: 3,
        marginBottom: 20,
      }}
    >
      {MODES.map((mode) => {
        const isActive = dashboardMode === mode;
        const label = mode === 'simple' ? 'Simple Mode' : 'Deep Dive Mode';
        return (
          <button
            key={mode}
            onClick={() => setDashboardMode(mode)}
            style={{
              background: isActive ? '#00E5A0' : 'transparent',
              color: isActive ? '#000' : '#8899aa',
              border: 'none',
              borderRadius: 8,
              padding: '6px 16px',
              fontSize: 12,
              fontWeight: isActive ? 700 : 400,
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
};

export default ModeToggle;
