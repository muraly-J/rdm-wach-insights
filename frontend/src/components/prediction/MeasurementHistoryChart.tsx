import React from 'react';
import {
  LineChart, Line, YAxis, XAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts';
import type { MeasurementPoint } from '../../types';

interface MeasurementHistoryChartProps {
  label: string;
  unit: string;
  data: MeasurementPoint[];
  color: string;
  loading?: boolean;
  isCoreMetric: boolean;
  tNow?: string;
}

export default function MeasurementHistoryChart({
  label, unit, data, color, loading, isCoreMetric, tNow,
}: MeasurementHistoryChartProps) {
  if (loading) {
    return <div className="h-[220px] bg-[#131A23] rounded-xl border border-[#1E2A3A] animate-pulse" />;
  }

  return (
    <div className="bg-[#131A23] rounded-xl border border-[#1E2A3A] p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="inline-block w-4 h-px" style={{ backgroundColor: color }} />
          <span className="text-sm font-medium text-white font-mono">{label}</span>
          {unit && <span className="text-xs text-[#4A5568]">{unit}</span>}
        </div>
        {!isCoreMetric && (
          <span className="text-[10px] text-[#4A5568] border border-[#1E2A3A] rounded-full px-2 py-0.5">
            Historical only
          </span>
        )}
        {isCoreMetric && (
          <span className="text-[10px] text-[#00E5A0]/60 border border-[#00E5A0]/20 rounded-full px-2 py-0.5">
            Use metric toggle for forecast
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data} margin={{ top: 4, right: 24, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="#1E2A3A" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="timestamp"
            stroke="#4A5568"
            fontSize={10}
            tickLine={false}
            axisLine={false}
            minTickGap={48}
            tickFormatter={(ts: string) =>
              new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
            }
          />
          <YAxis
            width={42}
            fontSize={10}
            stroke="#4A5568"
            tickLine={false}
            axisLine={false}
            domain={['auto', 'auto']}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1A2230',
              border: '1px solid #1E2A3A',
              borderRadius: 8,
              fontSize: 11,
            }}
            labelFormatter={(l: string) => new Date(l).toLocaleString()}
            formatter={(v: number) => [`${v.toFixed(2)} ${unit}`, label]}
          />
          {tNow && (
            <ReferenceLine
              x={tNow}
              stroke="#2A3A4A"
              strokeDasharray="4 2"
              label={{ value: 'Now', fill: '#4A5568', fontSize: 9, position: 'insideTop' }}
            />
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
