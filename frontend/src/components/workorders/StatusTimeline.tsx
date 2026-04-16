import React from 'react';
import { WorkOrder } from '../../types/chat';

interface StatusTimelineProps {
  order: WorkOrder;
}

interface TimelineEvent {
  label: string;
  date: string | null;
  color: string;
  done: boolean;
}

const StatusTimeline: React.FC<StatusTimelineProps> = ({ order }) => {
  const events: TimelineEvent[] = [
    {
      label: 'Created',
      date: order.created_at,
      color: '#8899aa',
      done: true,
    },
    {
      label: 'Updated',
      date: order.updated_at !== order.created_at ? order.updated_at : null,
      color: '#8899aa',
      done: order.updated_at !== order.created_at,
    },
    {
      label: 'Approved',
      date: order.approved_by ? order.updated_at : null,
      color: '#00E5A0',
      done: order.status === 'approved' || order.status === 'resolved',
    },
    {
      label: 'Resolved',
      date: order.resolved_at,
      color: '#00E5A0',
      done: Boolean(order.resolved_at),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {events.map((ev, idx) => (
        <div key={ev.label} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          {/* Connector column */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 20, flexShrink: 0 }}>
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: ev.done ? ev.color : '#2a3649',
                border: `2px solid ${ev.done ? ev.color : '#3a4a5a'}`,
                marginTop: 2,
                flexShrink: 0,
              }}
            />
            {idx < events.length - 1 && (
              <div
                style={{
                  width: 2,
                  flex: 1,
                  minHeight: 24,
                  background: ev.done ? `${ev.color}44` : '#2a3649',
                }}
              />
            )}
          </div>

          {/* Content */}
          <div style={{ paddingBottom: idx < events.length - 1 ? 16 : 0 }}>
            <div
              style={{
                fontSize: 12,
                fontWeight: ev.done ? 600 : 400,
                color: ev.done ? '#E8ECF1' : '#556677',
              }}
            >
              {ev.label}
            </div>
            {ev.date && (
              <div style={{ fontSize: 10, color: '#556677', marginTop: 2 }}>
                {new Date(ev.date).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default StatusTimeline;
