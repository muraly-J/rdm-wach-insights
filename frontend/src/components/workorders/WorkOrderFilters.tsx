import React from 'react';

export interface WorkOrderFilterState {
  status: string;
  severity: string;
  search: string;
}

interface WorkOrderFiltersProps {
  filters: WorkOrderFilterState;
  onChange: (filters: WorkOrderFilterState) => void;
}

const STATUS_OPTIONS = ['all', 'draft', 'approved', 'dismissed'];
const SEVERITY_OPTIONS = ['all', 'Critical', 'Maintenance Soon', 'Monitor', 'Healthy'];

const chipStyle = (active: boolean, activeColor: string): React.CSSProperties => ({
  padding: '4px 12px',
  borderRadius: 20,
  fontSize: 11,
  fontWeight: active ? 700 : 400,
  cursor: 'pointer',
  border: `1px solid ${active ? activeColor : '#2a3649'}`,
  background: active ? `${activeColor}22` : 'transparent',
  color: active ? activeColor : '#8899aa',
  transition: 'all 0.12s',
  textTransform: 'capitalize' as const,
});

const SEVERITY_COLORS: Record<string, string> = {
  all: '#8899aa',
  Critical: '#FF4D4D',
  'Maintenance Soon': '#FFB020',
  Monitor: '#4DA6FF',
  Healthy: '#00E5A0',
};

const STATUS_COLORS: Record<string, string> = {
  all: '#8899aa',
  draft: '#f59e0b',
  approved: '#00E5A0',
  dismissed: '#556677',
};

const WorkOrderFilters: React.FC<WorkOrderFiltersProps> = ({ filters, onChange }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
      {/* Search */}
      <input
        type="text"
        placeholder="Search work orders…"
        value={filters.search}
        onChange={(e) => onChange({ ...filters, search: e.target.value })}
        style={{
          background: '#1a2234',
          border: '1px solid #2a3649',
          borderRadius: 8,
          padding: '8px 12px',
          color: '#E8ECF1',
          fontSize: 12,
          outline: 'none',
          width: '100%',
          maxWidth: 320,
          boxSizing: 'border-box',
        }}
      />

      {/* Status chips */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        <span
          style={{
            fontSize: 10,
            color: '#556677',
            marginRight: 4,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
          }}
        >
          Status:
        </span>
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            style={chipStyle(filters.status === s, STATUS_COLORS[s] ?? '#8899aa')}
            onClick={() => onChange({ ...filters, status: s })}
          >
            {s === 'all' ? 'All' : s}
          </button>
        ))}
      </div>

      {/* Severity chips */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        <span
          style={{
            fontSize: 10,
            color: '#556677',
            marginRight: 4,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
          }}
        >
          Severity:
        </span>
        {SEVERITY_OPTIONS.map((s) => (
          <button
            key={s}
            style={chipStyle(filters.severity === s, SEVERITY_COLORS[s] ?? '#8899aa')}
            onClick={() => onChange({ ...filters, severity: s })}
          >
            {s === 'all' ? 'All' : s}
          </button>
        ))}
      </div>
    </div>
  );
};

export default WorkOrderFilters;
