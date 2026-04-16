import React from 'react';
import { WorkOrder } from '../../types/chat';

interface WorkOrderStatsBarProps {
  orders: WorkOrder[];
}

interface StatItem {
  label: string;
  count: number;
  color: string;
}

const WorkOrderStatsBar: React.FC<WorkOrderStatsBarProps> = ({ orders }) => {
  const stats: StatItem[] = [
    {
      label: 'Total',
      count: orders.length,
      color: '#8899aa',
    },
    {
      label: 'Drafts',
      count: orders.filter((o) => o.status === 'draft').length,
      color: '#f59e0b',
    },
    {
      label: 'Approved',
      count: orders.filter((o) => o.status === 'approved').length,
      color: '#00E5A0',
    },
    {
      label: 'Dismissed',
      count: orders.filter((o) => o.status === 'dismissed').length,
      color: '#556677',
    },
    {
      label: 'Critical',
      count: orders.filter((o) => o.severity?.toLowerCase() === 'critical').length,
      color: '#ef4444',
    },
    {
      label: 'High',
      count: orders.filter((o) => o.severity?.toLowerCase() === 'high').length,
      color: '#f97316',
    },
  ];

  return (
    <div
      style={{
        display: 'flex',
        gap: 12,
        flexWrap: 'wrap',
        marginBottom: 20,
      }}
    >
      {stats.map(({ label, count, color }) => (
        <div
          key={label}
          style={{
            background: '#1a2234',
            border: '1px solid #2a3649',
            borderRadius: 8,
            padding: '10px 16px',
            minWidth: 80,
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
          }}
        >
          <span
            style={{
              fontSize: 22,
              fontWeight: 700,
              color,
              lineHeight: 1,
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {count}
          </span>
          <span
            style={{
              fontSize: 10,
              color: '#556677',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}
          >
            {label}
          </span>
        </div>
      ))}
    </div>
  );
};

export default WorkOrderStatsBar;
