import React from 'react';
import { formatTickByRange, tickIntervalByRange, type TimeRange } from '../../utils/formatTick';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

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
  { key: 'energy_anomaly',  label: 'Energy Anomaly',  color: '#3B82F6' },
  { key: 'pf_degradation',  label: 'PF Degradation',  color: '#8B5CF6' },
  { key: 'phase_imbalance', label: 'Phase Imbalance', color: '#F59E0B' },
  { key: 'thd_drift',       label: 'THD Drift',       color: '#10B981' },
  { key: 'overload',        label: 'Overload',        color: '#EF4444' },
] as const;

const CombinedScoresChart: React.FC<CombinedScoresChartProps> = ({ scoreData, timeRange }) => {
  // Merge all score series into a single array indexed by position
  const mergedData = React.useMemo(() => {
    const firstScore = scoreData[SCORE_NAMES[0].key];
    if (!firstScore || firstScore.data.length === 0) return [];

    return firstScore.data.map((point, idx) => {
      const entry: Record<string, any> = { timestamp: point.timestamp };
      SCORE_NAMES.forEach(({ key }) => {
        entry[key] = scoreData[key]?.data[idx]?.value ?? null;
      });
      return entry;
    });
  }, [scoreData]);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#1A2230] p-4 rounded-xl border border-[#1E2A3A]">
          <p className="text-[#8A95A5] text-xs mb-2 font-mono">{formatTickByRange(label, timeRange)}</p>
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

  if (mergedData.length === 0) {
    return (
      <div className="card p-6 mb-8 h-[320px] flex items-center justify-center">
        <span className="text-[#8A95A5]">No score data available</span>
      </div>
    );
  }

  return (
    <div className="card p-6 mb-8">
      <h3 className="font-display text-[24px] font-bold mb-6 tracking-[-0.01em]">
        Five-Score Overview
      </h3>

      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={mergedData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#1E2A3A" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="timestamp"
            stroke="#8A95A5"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => formatTickByRange(v, timeRange)}
            interval={tickIntervalByRange(timeRange)}
          />
          <YAxis
            domain={[0, 100]}
            stroke="#8A95A5"
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
        </LineChart>
      </ResponsiveContainer>

      <p className="text-xs text-[#8A95A5] mt-4 text-center">
        Click legend items to toggle individual scores
      </p>
    </div>
  );
};

export default CombinedScoresChart;
