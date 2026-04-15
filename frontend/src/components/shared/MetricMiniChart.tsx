import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { MeasurementPoint } from '../../types';
import { formatDateTimeMYT } from '../../utils/formatTick';
import { renderOffPeriodAreas } from '../../utils/offPeriodAreas';

interface MetricMiniChartProps {
  label: string;
  unit: string;
  data: Array<MeasurementPoint & { is_on?: boolean }>;
  color: string;
  loading?: boolean;
}

export default function MetricMiniChart({
  label,
  unit,
  data,
  color,
  loading,
}: MetricMiniChartProps) {
  if (loading) {
    return <div className="mt-3 h-[104px] bg-[#2a3649] rounded-lg animate-pulse" />;
  }

  return (
    <div className="mt-3 border-t border-[#2e3f55] pt-3">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="inline-block w-4 h-px" style={{ backgroundColor: color }} />
        <span className="text-[11px] text-[#6d6e71] font-mono">{label}</span>
        {unit && <span className="text-[10px] text-[#4A5568]">{unit}</span>}
        {data.length === 0 && <span className="text-[10px] text-[#4A5568] ml-auto">No data</span>}
      </div>
      <ResponsiveContainer width="100%" height={80}>
        <LineChart data={data} margin={{ top: 2, right: 36, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#2e3f55" strokeDasharray="3 3" vertical={false} />
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
              border: '1px solid #2e3f55',
              borderRadius: 6,
              fontSize: 11,
            }}
            labelFormatter={(l: string) =>
              formatDateTimeMYT(new Date(l), {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                hour12: false,
              })
            }
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
          {renderOffPeriodAreas(data, 'timestamp')}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
