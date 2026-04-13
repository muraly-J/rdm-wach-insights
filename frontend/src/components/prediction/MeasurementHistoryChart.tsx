import React from 'react';
import {
  LineChart, Line, YAxis, XAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts';
import type { MeasurementPoint } from '../../types';
import { formatDateMYT, formatDateTimeMYT } from '../../utils/formatTick';

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
    return <div className="h-[220px] bg-[#131A23] rounded-xl border border-[#2e3f55] animate-pulse" />;
  }

  return (
    <div className="bg-[#131A23] rounded-xl border border-[#2e3f55] p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="inline-block w-4 h-px" style={{ backgroundColor: color }} />
          <span className="text-sm font-medium text-white font-mono">{label}</span>
          {unit && <span className="text-xs text-[#4A5568]">{unit}</span>}
        </div>
        {!isCoreMetric && (
          <span className="text-[10px] text-[#4A5568] border border-[#2e3f55] rounded-full px-2 py-0.5">
            Historical only
          </span>
        )}
        {isCoreMetric && (
          <span className="text-[10px] text-[#4fbd95]/60 border border-[#4fbd95]/20 rounded-full px-2 py-0.5">
            Use metric toggle for forecast
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data} margin={{ top: 4, right: 24, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="#2e3f55" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="timestamp"
            stroke="#4A5568"
            fontSize={10}
            tickLine={false}
            axisLine={false}
            minTickGap={48}
            tickFormatter={(ts: string) =>
              formatDateMYT(new Date(ts), { month: 'short', day: 'numeric' })
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
              backgroundColor: '#2a3649',
              border: '1px solid #2e3f55',
              borderRadius: 8,
              fontSize: 11,
            }}
            labelFormatter={(l: string) => formatDateTimeMYT(new Date(l), {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
              hour12: false
            })}
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
