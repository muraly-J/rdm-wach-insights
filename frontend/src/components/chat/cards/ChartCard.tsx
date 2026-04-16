import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';
import type { ChartCardData } from '../../../types/chat';

interface ChartCardProps {
  data: ChartCardData;
}

export default function ChartCard({ data }: ChartCardProps) {
  return (
    <div className="rounded-[10px] px-3.5 py-2.5 mt-2 bg-[#141920] border border-[#1a2638]">
      <div className="text-[12px] font-semibold text-[#E8ECF1] mb-2">{data.title}</div>
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={data.entries} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
          <XAxis
            dataKey="device"
            tick={{ fontSize: 9, fill: '#556677' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis hide />
          <Tooltip
            contentStyle={{
              background: '#0D1520',
              border: '1px solid #1a2638',
              borderRadius: 6,
              fontSize: 11,
              color: '#E8ECF1',
            }}
            formatter={(v: number) => [`${v}${data.unit}`, '']}
          />
          <Bar dataKey="value" fill="#00E5A0" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
