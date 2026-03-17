import React from 'react';
import {
  LineChart, Line, YAxis, XAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { MeasurementPoint } from '../../types';

interface MetricMiniChartProps {
  label: string;
  unit: string;
  data: MeasurementPoint[];
  color: string;
  loading?: boolean;
}

export default function MetricMiniChart({
  label, unit, data, color, loading,
}: MetricMiniChartProps) {
  if (loading) {
    return <div className="mt-3 h-[104px] bg-[#1A2230] rounded-lg animate-pulse" />;
  }

  return (
    <div className="mt-3 border-t border-[#1E2A3A] pt-3">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="inline-block w-4 h-px" style={{ backgroundColor: color }} />
        <span className="text-[11px] text-[#8A95A5] font-mono">{label}</span>
        {unit && (
          <span className="text-[10px] text-[#4A5568]">{unit}</span>
        )}
        {data.length === 0 && (
          <span className="text-[10px] text-[#4A5568] ml-auto">No data</span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={80}>
        <LineChart data={data} margin={{ top: 2, right: 36, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#1E2A3A" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="timestamp" hide />
          <YAxis
            width={34}
            fontSize={9}
            stroke="#4A5568"
            tickLine={false}
            axisLine={false}
            domain={['auto', 'auto']}
            tickFormatter={(v: number) => v.toFixed(1)}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#131A23',
              border: '1px solid #1E2A3A',
              borderRadius: 6,
              fontSize: 11,
            }}
            labelFormatter={(l: string) => new Date(l).toLocaleString()}
            formatter={(v: number) => [`${v.toFixed(2)} ${unit}`, label]}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
