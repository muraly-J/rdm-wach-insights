import React from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { formatTickByRange, tickIntervalByRange, type TimeRange } from '../../utils/formatTick';
import { renderOffPeriodAreas } from '../../utils/offPeriodAreas';

interface ScoreEntry {
  current: number;
  trend: number;
  data: Array<{ timestamp: string; value: number }>;
}

interface CombinedScoresChartProps {
  scoreData: Record<string, ScoreEntry>;
  timeRange: TimeRange;
}

/**
 * CombinedScoresChart - Full-width overlaid line chart showing all five scores (Section 5.3)
 *
 * One plot with distinct colours from chart-1..5 palette.
 * Toggle individual scores on/off via legend.
 */
const SCORE_NAMES = [
  { key: 'energy_anomaly', label: 'Energy Anomaly', color: '#3B82F6' },
  { key: 'pf_degradation', label: 'PF Degradation', color: '#8B5CF6' },
  { key: 'phase_imbalance', label: 'Phase Imbalance', color: '#F59E0B' },
  { key: 'thd_drift', label: 'THD Drift', color: '#10B981' },
  { key: 'overload', label: 'Overload', color: '#EF4444' },
] as const;

const CombinedScoresChart: React.FC<CombinedScoresChartProps> = ({ scoreData, timeRange }) => {
  // Merge all score series into a single array indexed by position
  const mergedData = React.useMemo(() => {
    const firstScore = scoreData[SCORE_NAMES[0].key];
    if (!firstScore || firstScore.data.length === 0) return [];

    return firstScore.data.map((point, idx) => {
      const entry: Record<string, any> = {
        timestamp: point.timestamp,
        is_on: (point as any).is_on,
      };
      SCORE_NAMES.forEach(({ key }) => {
        entry[key] = scoreData[key]?.data[idx]?.value ?? null;
      });
      return entry;
    });
  }, [scoreData]);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#2a3649] p-4 rounded-xl border border-[#2e3f55]">
          <p className="text-[#6d6e71] text-xs mb-2 font-mono">
            {formatTickByRange(label, timeRange)}
          </p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {Number(entry.value).toFixed(1)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const glassStyle: React.CSSProperties = {
    background: 'rgba(255,255,255,0.04)',
    backdropFilter: 'blur(20px) saturate(180%)',
    WebkitBackdropFilter: 'blur(20px) saturate(180%)',
    border: '1px solid rgba(255,255,255,0.08)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06), 0 8px 40px rgba(0,0,0,0.30)',
  };

  if (mergedData.length === 0) {
    return (
      <div
        className="card p-4 sm:p-6 mb-6 sm:mb-8 h-[200px] sm:h-[320px] flex items-center justify-center"
        style={glassStyle}
      >
        <span className="text-[#6d6e71]">No Score Data Available</span>
      </div>
    );
  }

  return (
    <div className="card p-4 sm:p-6 mb-6 sm:mb-8" style={glassStyle}>
      <h3 className="font-display text-lg sm:text-[24px] font-bold mb-4 sm:mb-6 tracking-[-0.01em]">
        Five-Score Overview
      </h3>

      <div className="h-[220px] sm:h-[280px] lg:h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={mergedData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#2e3f55" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="timestamp"
              stroke="#6d6e71"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => formatTickByRange(v, timeRange)}
              interval={tickIntervalByRange(timeRange)}
            />
            <YAxis
              domain={[0, 100]}
              stroke="#6d6e71"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ paddingTop: 10 }} iconType="circle" />

            {SCORE_NAMES.map((score) => (
              <Line
                key={score.key}
                type="monotone"
                dataKey={score.key}
                name={score.label}
                stroke={score.color}
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            ))}
            {renderOffPeriodAreas(mergedData, 'timestamp')}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="text-xs text-[#6d6e71] mt-4 text-center">
        Click legend items to toggle individual scores
      </p>
    </div>
  );
};

export default CombinedScoresChart;
