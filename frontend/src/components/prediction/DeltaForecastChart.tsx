import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { DeltaForecastPoint } from '../../types';

interface Props {
  forecast: DeltaForecastPoint[];
  tNow: string;
}

const DeltaForecastChart: React.FC<Props> = ({ forecast }) => {
  const data = forecast.map((pt) => ({
    label: `+${pt.hour}h`,
    value: pt.predicted_delta_kwh,
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    const v = payload[0].value;
    return (
      <div className="bg-[#1A2230] p-3 rounded-xl border border-[#1E2A3A]">
        <p className="text-[#8A95A5] text-xs mb-1 font-mono">{label} from now</p>
        <p className="text-sm font-medium text-[#00E5A0]">
          {v !== null && v !== undefined ? `${v.toFixed(3)} kWh` : 'No data'}
        </p>
      </div>
    );
  };

  return (
    <div className="card p-6">
      <div className="mb-4">
        <h3 className="font-display text-[20px] font-bold">Predicted Hourly Consumption</h3>
        <p className="text-sm text-[#8A95A5] mt-1">
          Next 23 hours · 3-point historical average (−24h, −168h, −336h)
        </p>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid stroke="#1E2A3A" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="label"
            stroke="#8A95A5"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            interval={2}
          />
          <YAxis
            stroke="#8A95A5"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            unit=" kWh"
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke="#3B4B5A" strokeDasharray="3 3" />
          <Bar dataKey="value" radius={[3, 3, 0, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill="#00E5A0" opacity={0.8} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default DeltaForecastChart;
