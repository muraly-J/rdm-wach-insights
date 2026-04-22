import React from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { DerivationReferenceLine, DerivationSeries } from '../../../types';
import {
  formatDateMYT,
  formatTickByRange,
  tickIntervalByRange,
  type TimeRange,
} from '../../../utils/formatTick';
import { renderOffPeriodAreas } from '../../../utils/offPeriodAreas';

interface RawScoreRelationChartProps {
  scoreName: string;
  series: DerivationSeries[];
  scoreData: Array<{ timestamp: string; value: number; is_on?: boolean }>;
  referenceLines?: DerivationReferenceLine[];
  chartColor: string;
  headerAction?: React.ReactNode;
  timeRange: TimeRange;
  loading?: boolean;
}

// Color palette for up to 7 left-axis series
const SERIES_PALETTE = [
  '#6d6e71', // grey
  '#60A5FA', // blue
  '#34D399', // green
  '#F97316', // orange
  '#C084FC', // purple
  '#F472B6', // pink
  '#FCD34D', // yellow
];

/**
 * RawScoreRelationChart — Dual-axis chart for score derivation visualization
 *
 * Left Y-axis: Variable-number raw data series (voltages, currents, THD%, etc.)
 * Right Y-axis: Computed score (0–100)
 * X-axis: Time
 *
 * Supports reference lines (e.g. IEEE 519: 5% for THD, P95 for overload)
 */
const RawScoreRelationChart: React.FC<RawScoreRelationChartProps> = ({
  scoreName,
  series,
  scoreData,
  referenceLines = [],
  chartColor,
  headerAction,
  timeRange,
  loading = false,
}) => {
  if (loading) {
    return (
      <div className="card p-6 w-full h-[560px] bg-[#2a3649] rounded-lg animate-pulse border border-[#2e3f55]" />
    );
  }
  // Merge all series into a single data array keyed by index
  // Each series maps to key `s0`, `s1`, etc.
  const mergedData: Record<string, any>[] = [];

  series.forEach((s, si) => {
    const key = `s${si}`;
    s.data.forEach((pt, idx) => {
      if (!mergedData[idx]) {
        mergedData[idx] = { timestamp: pt.timestamp };
      }
      mergedData[idx][key] = pt.value;
    });
  });

  // Merge score data and is_on flags
  scoreData.forEach((pt, idx) => {
    if (mergedData[idx]) {
      mergedData[idx].scoreValue = pt.value;
      mergedData[idx].is_on = pt.is_on;
    }
  });

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-[#2a3649] p-4 rounded-xl border border-[#2e3f55] shadow-2xl max-w-[220px]">
        <p className="text-[#6d6e71] text-xs mb-3 font-mono">
          {formatTickByRange(label, timeRange)}
        </p>
        {payload.map((entry: any) => {
          if (entry.dataKey === 'scoreValue') return null;
          const idx = parseInt(entry.dataKey.replace('s', ''), 10);
          const s = series[idx];
          if (!s) return null;
          return (
            <div key={entry.dataKey} className="mb-1.5">
              <span className="text-xs" style={{ color: entry.color }}>
                {s.label} {s.unit && `(${s.unit})`}:
              </span>{' '}
              <span className="text-xs font-medium text-white">
                {typeof entry.value === 'number' ? entry.value.toFixed(2) : '—'}
              </span>
            </div>
          );
        })}
        {payload.find((p: any) => p.dataKey === 'scoreValue') && (
          <div className="mt-2 pt-2 border-t border-[#2e3f55]">
            <span className="text-xs" style={{ color: chartColor }}>
              Score:
            </span>{' '}
            <span className="text-xs font-medium" style={{ color: chartColor }}>
              {payload.find((p: any) => p.dataKey === 'scoreValue').value?.toFixed(1)} / 100
            </span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="card p-6 hover:border-[#2e3f55] transition-all duration-300 w-full">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <h4 className="text-[18px] font-semibold text-white">{scoreName}</h4>
        {headerAction && <div className="ml-2 flex-shrink-0">{headerAction}</div>}
      </div>

      {/* Subtitle: list series */}
      <p className="text-[13px] text-[#6d6e71] mb-4 font-mono">
        {series.map((s) => s.label).join(' · ')} → Score 0–100
      </p>

      <ResponsiveContainer width="100%" height={560}>
        <LineChart data={mergedData} margin={{ top: 15, right: 40, left: 0, bottom: 25 }}>
          <CartesianGrid stroke="#2e3f55" strokeDasharray="3 3" vertical={false} />

          <XAxis
            dataKey="timestamp"
            stroke="#6d6e71"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => {
              if (timeRange === '7d') {
                return formatDateMYT(new Date(v), { month: 'short', day: 'numeric' });
              }
              return formatTickByRange(v, timeRange);
            }}
            interval={tickIntervalByRange(timeRange)}
          />

          {/* Left Y-axis: raw series */}
          <YAxis
            yAxisId="left"
            stroke="#6d6e71"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#6d6e71' } as any}
            domain={['auto', 'auto']}
          />

          {/* Right Y-axis: score */}
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke={chartColor}
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: chartColor } as any}
            domain={[0, 100]}
          />

          <Tooltip content={<CustomTooltip />} />

          {/* Reference lines (e.g. IEEE 519: 5%) */}
          {referenceLines.map((rl, i) => (
            <ReferenceLine
              key={i}
              yAxisId="left"
              y={rl.value}
              stroke={rl.color}
              strokeDasharray="4 4"
              label={{ value: rl.label, fill: rl.color, fontSize: 10, position: 'insideTopRight' }}
            />
          ))}

          {/* Raw data series */}
          {series.map((s, si) => {
            const key = `s${si}`;
            const color = SERIES_PALETTE[si % SERIES_PALETTE.length];
            const strokeWidth = s.style === 'bold' ? 3 : 2;
            const strokeDasharray =
              s.style === 'dashed' ? '4 4' : s.style === 'ref' ? '3 3' : undefined;
            const opacity = s.style === 'ref' ? 0.5 : 0.8;
            return (
              <Line
                key={key}
                yAxisId="left"
                type="monotone"
                dataKey={key}
                stroke={color}
                strokeWidth={strokeWidth}
                strokeDasharray={strokeDasharray}
                opacity={opacity}
                dot={false}
                name={s.label}
              />
            );
          })}

          {/* Score line */}
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="scoreValue"
            stroke={chartColor}
            strokeWidth={3}
            dot={false}
            name="Score"
          />

          {renderOffPeriodAreas(mergedData, 'timestamp')}
        </LineChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-3">
        {series.map((s, si) => (
          <div key={si} className="flex items-center gap-1.5 text-xs">
            <span
              className="inline-block w-4 h-0.5 rounded-full"
              style={{ backgroundColor: SERIES_PALETTE[si % SERIES_PALETTE.length] }}
            />
            <span className="text-[#6d6e71]">
              {s.label}
              {s.unit ? ` (${s.unit})` : ''}
            </span>
          </div>
        ))}
        <div className="flex items-center gap-1.5 text-xs">
          <span
            className="inline-block w-4 h-0.5 rounded-full"
            style={{ backgroundColor: chartColor }}
          />
          <span className="text-[#6d6e71]">Score</span>
        </div>
      </div>
    </div>
  );
};

export default RawScoreRelationChart;
