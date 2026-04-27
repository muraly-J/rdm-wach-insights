import React from 'react';
import type { OperationalState } from '../../types';

interface StateBadgeProps {
  state: OperationalState;
  lastMeasured?: string | null;
  className?: string;
}

const STATE_CONFIG: Record<
  OperationalState,
  { label: string; dot: string; color: string; bg: string }
> = {
  On: {
    label: 'On',
    dot: '●',
    color: '#00E5A0',
    bg: 'rgba(0, 229, 160, 0.12)',
  },
  Off: {
    label: 'Off',
    dot: '○',
    color: '#f59e0b',
    bg: 'rgba(245, 158, 11, 0.12)',
  },
  Off_Stale: {
    label: 'Off · Stale',
    dot: '○',
    color: '#f97316',
    bg: 'rgba(249, 115, 22, 0.12)',
  },
  Inactive: {
    label: 'Inactive',
    dot: '—',
    color: '#556677',
    bg: 'rgba(85, 102, 119, 0.12)',
  },
};

function formatHoursAgo(isoTimestamp: string): string {
  const diff = Date.now() - new Date(isoTimestamp).getTime();
  const hours = Math.floor(diff / 3_600_000);
  return hours < 24 ? `${hours}h ago` : `${Math.floor(hours / 24)}d ago`;
}

const StateBadge: React.FC<StateBadgeProps> = ({ state, lastMeasured, className }) => {
  const cfg = STATE_CONFIG[state];
  const tooltip =
    state === 'Off_Stale' && lastMeasured
      ? `Last measured ${formatHoursAgo(lastMeasured)}`
      : undefined;

  return (
    <span
      title={tooltip}
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 8px',
        borderRadius: 9999,
        fontSize: 11,
        fontWeight: 500,
        color: cfg.color,
        background: cfg.bg,
        border: `1px solid ${cfg.color}44`,
        whiteSpace: 'nowrap',
        cursor: tooltip ? 'help' : 'default',
      }}
    >
      <span style={{ fontSize: 8 }}>{cfg.dot}</span>
      {cfg.label}
    </span>
  );
};

export default StateBadge;
