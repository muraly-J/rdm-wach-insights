import React from 'react';
import { deviceIdToDisplay } from '../../utils/deviceNames';

export type AHUStatus = 'Good' | 'Warning' | 'Critical';

export interface AHURankRow {
  id: string;
  label: string;
  level: number;
  healthScore: number;
  trend: number;
  status: AHUStatus;
}

type SortKey = 'label' | 'level' | 'healthScore' | 'trend' | 'status';
type SortDir = 'asc' | 'desc';

interface AHURankingsTableProps {
  rows: AHURankRow[];
}

const STATUS_COLOR: Record<AHUStatus, string> = {
  Good: '#00E5A0',
  Warning: '#f59e0b',
  Critical: '#ff6b6b',
};

const AHURankingsTable: React.FC<AHURankingsTableProps> = ({ rows }) => {
  const [sortKey, setSortKey] = React.useState<SortKey>('healthScore');
  const [sortDir, setSortDir] = React.useState<SortDir>('desc');

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sorted = React.useMemo(() => {
    return [...rows].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      const cmp =
        typeof aVal === 'string'
          ? aVal.localeCompare(bVal as string)
          : (aVal as number) - (bVal as number);
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [rows, sortKey, sortDir]);

  const SortHeader: React.FC<{ label: string; sortK: SortKey }> = ({ label, sortK }) => (
    <th
      onClick={() => handleSort(sortK)}
      style={{
        cursor: 'pointer',
        userSelect: 'none',
        padding: '8px 12px',
        textAlign: 'left',
        fontSize: 10,
        fontWeight: 600,
        color: sortKey === sortK ? '#00E5A0' : '#556677',
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
      }}
    >
      {label} {sortKey === sortK ? (sortDir === 'asc' ? '↑' : '↓') : ''}
    </th>
  );

  if (rows.length === 0) {
    return (
      <div style={{ padding: 24, color: '#556677', textAlign: 'center', fontSize: 13 }}>
        No AHU Data Available for This Selection.
      </div>
    );
  }

  return (
    <div
      style={{
        background: '#1a2234',
        border: '1px solid #2a3649',
        borderRadius: 12,
        overflow: 'hidden',
        marginBottom: 24,
      }}
    >
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #2a3649' }}>
            <SortHeader label="AHU Name" sortK="label" />
            <SortHeader label="Level" sortK="level" />
            <SortHeader label="Health" sortK="healthScore" />
            <SortHeader label="Trend" sortK="trend" />
            <SortHeader label="Status" sortK="status" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr
              key={row.id}
              style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <td style={{ padding: '10px 12px' }}>
                {(() => {
                  const display = deviceIdToDisplay(row.id);
                  const shortName = display.split(' \u2014 ')[0];
                  return (
                    <span style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <span
                        style={{
                          fontSize: 12,
                          color: '#C8D4E0',
                          fontFamily: "'JetBrains Mono', monospace",
                        }}
                      >
                        {shortName}
                      </span>
                      <span style={{ fontSize: 10, color: '#445566' }}>{row.id}</span>
                    </span>
                  );
                })()}
              </td>
              <td style={{ padding: '10px 12px', fontSize: 12, color: '#8899aa' }}>L{row.level}</td>
              <td style={{ padding: '10px 12px' }}>
                <span
                  style={{
                    fontSize: 14,
                    fontWeight: 700,
                    color:
                      row.healthScore >= 80
                        ? '#00E5A0'
                        : row.healthScore >= 60
                          ? '#f59e0b'
                          : '#ff6b6b',
                  }}
                >
                  {Math.round(row.healthScore)}
                </span>
              </td>
              <td
                style={{
                  padding: '10px 12px',
                  fontSize: 12,
                  color: row.trend >= 0 ? '#00E5A0' : '#ff6b6b',
                }}
              >
                {row.trend >= 0 ? '↑' : '↓'} {Math.abs(row.trend).toFixed(1)}%
              </td>
              <td style={{ padding: '10px 12px' }}>
                <span
                  style={{
                    background: `${STATUS_COLOR[row.status]}22`,
                    color: STATUS_COLOR[row.status],
                    border: `1px solid ${STATUS_COLOR[row.status]}55`,
                    borderRadius: 20,
                    padding: '2px 8px',
                    fontSize: 10,
                    fontWeight: 600,
                  }}
                >
                  {row.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AHURankingsTable;
