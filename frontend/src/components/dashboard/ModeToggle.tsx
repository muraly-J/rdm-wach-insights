import React from 'react';
import { useAppStore, DashboardMode } from '../../store/useAppStore';

const MODES: DashboardMode[] = ['simple', 'deepdive'];

const ModeToggle: React.FC = () => {
  const { dashboardMode, setDashboardMode, selectedDevice } = useAppStore();
  const [hint, setHint] = React.useState(false);

  const deepDiveEnabled = Boolean(selectedDevice && selectedDevice !== 'all');

  const handleClick = (mode: DashboardMode) => {
    if (mode === 'deepdive' && !deepDiveEnabled) {
      setHint(true);
      setTimeout(() => setHint(false), 2500);
      return;
    }
    setDashboardMode(mode);
  };

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', gap: 6, marginBottom: 20 }}>
      <div
        style={{
          display: 'inline-flex',
          background: '#1a2234',
          border: '1px solid #2a3649',
          borderRadius: 10,
          padding: 3,
        }}
      >
        {MODES.map((mode) => {
          const isActive = dashboardMode === mode;
          const isDisabled = mode === 'deepdive' && !deepDiveEnabled;
          const label = mode === 'simple' ? 'Simple Mode' : 'Deep Dive Mode';
          return (
            <button
              key={mode}
              onClick={() => handleClick(mode)}
              style={{
                background: isActive ? '#00E5A0' : 'transparent',
                color: isActive ? '#000' : isDisabled ? '#3a4a5a' : '#8899aa',
                border: 'none',
                borderRadius: 8,
                padding: '6px 16px',
                fontSize: 12,
                fontWeight: isActive ? 700 : 400,
                cursor: isDisabled ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s',
                opacity: isDisabled ? 0.45 : 1,
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      {hint && (
        <span
          style={{
            fontSize: 11,
            color: '#f59e0b',
            paddingLeft: 4,
            animation: 'fadeIn 0.15s ease',
          }}
        >
          Select 1 device to begin Deep Dive.
        </span>
      )}
    </div>
  );
};

export default ModeToggle;
