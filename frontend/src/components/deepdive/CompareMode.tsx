import React from 'react';
import { SCORE_METRIC_GROUPS } from '../../constants/metricGroups';
import DeviceColumn from './DeviceColumn';

interface CompareModeProps {
  deviceIds: string[];
  labelMap: Record<string, string>;
  timeRange: string;
}

const CHART_COLORS = ['#00E5A0', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'];

const CompareMode: React.FC<CompareModeProps> = ({ deviceIds, labelMap, timeRange }) => {
  const [selectedMetrics, setSelectedMetrics] = React.useState<string[]>(['power_total', 'power_factor_avg']);
  const [groupOpen, setGroupOpen] = React.useState<string | null>(null);

  const colorMap = React.useMemo(() => {
    const map: Record<string, string> = {};
    selectedMetrics.forEach((m, i) => { map[m] = CHART_COLORS[i % CHART_COLORS.length]; });
    return map;
  }, [selectedMetrics]);

  const toggleMetric = (key: string) => {
    setSelectedMetrics((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 11, color: '#556677', marginBottom: 8, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Shared Metrics
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {SCORE_METRIC_GROUPS.map((group) => (
            <div key={group.scoreKey} style={{ position: 'relative' }}>
              <button
                onClick={() => setGroupOpen(groupOpen === group.scoreKey ? null : group.scoreKey)}
                style={{
                  background: '#1a2234', border: '1px solid #2a3649', borderRadius: 8,
                  padding: '5px 10px', fontSize: 11, color: '#8899aa', cursor: 'pointer',
                }}
              >
                {group.scoreLabel} ▾
              </button>
              {groupOpen === group.scoreKey && (
                <div style={{
                  position: 'absolute', top: 'calc(100% + 4px)', left: 0, zIndex: 20,
                  background: '#141D28', border: '1px solid #2a3649', borderRadius: 8,
                  padding: 6, minWidth: 180, boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                }}>
                  {group.availableMetrics.map((m) => (
                    <div
                      key={m.key}
                      onClick={() => toggleMetric(m.key)}
                      style={{
                        padding: '5px 8px', borderRadius: 5, cursor: 'pointer', fontSize: 11,
                        color: selectedMetrics.includes(m.key) ? '#00E5A0' : '#8899aa',
                        display: 'flex', alignItems: 'center', gap: 6,
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = '#2a3649')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                    >
                      <span style={{
                        width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                        background: selectedMetrics.includes(m.key) ? colorMap[m.key] ?? '#00E5A0' : '#2a3649',
                        border: '1px solid #2a3649',
                      }} />
                      {m.label}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 12 }}>
        {deviceIds.map((id) => (
          <DeviceColumn
            key={id}
            deviceId={id}
            deviceLabel={labelMap[id] ?? id}
            selectedMetrics={selectedMetrics}
            timeRange={timeRange}
            colorMap={colorMap}
          />
        ))}
      </div>
    </div>
  );
};

export default CompareMode;
