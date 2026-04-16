import React from 'react';
import { DashboardMode, useAppStore } from '../../store/useAppStore';

const MODE_CONFIG: { mode: DashboardMode; label: string }[] = [
  { mode: 'simple', label: 'Simple Mode' },
  { mode: 'deepdive', label: 'Deep Dive Mode' },
  { mode: 'workorders', label: 'Work Orders' },
];

const ModeToggle: React.FC = () => {
  const { dashboardMode, setDashboardMode, selectedDevice, workOrderDraftsCount } = useAppStore();
  const [hint, setHint] = React.useState(false);

  const deepDiveEnabled = Boolean(selectedDevice && selectedDevice !== 'all');

  const getModeLabel = (mode: DashboardMode): string => {
    if (mode === 'simple') return 'Simple Mode';
    if (mode === 'deepdive') return 'Deep Dive Mode';
    return 'Work Orders';
  };

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
        {MODE_CONFIG.map(({ mode, label }) => {
          const isActive = dashboardMode === mode;
          const isDisabled = mode === 'deepdive' && !deepDiveEnabled;
          return (
            <button
              key={mode}
              onClick={() => handleClick(mode)}
              style={{
                position: 'relative',
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
              {mode === 'workorders' && workOrderDraftsCount > 0 && (
                <span
                  style={{
                    position: 'absolute',
                    top: 2,
                    right: 4,
                    background: '#f59e0b',
                    color: '#000',
                    borderRadius: '50%',
                    fontSize: 9,
                    fontWeight: 700,
                    minWidth: 14,
                    height: 14,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    lineHeight: 1,
                    padding: '0 3px',
                  }}
                >
                  {workOrderDraftsCount > 99 ? '99+' : workOrderDraftsCount}
                </span>
              )}
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
