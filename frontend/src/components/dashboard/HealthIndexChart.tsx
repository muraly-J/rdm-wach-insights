import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { motion } from 'framer-motion';
import InfoTooltip from '../shared/InfoTooltip';

interface HealthIndexChartProps {
  data: Array<{ timestamp: string; [key: string]: number }>;
  devices: Array<{ id: string; name: string; label?: string; department?: string }>;
}

/**
 * HealthIndexChart - Time-series health index chart (Section 5.2)
 * 
 * Library: Recharts AreaChart
 * Y-axis: Health Index (0-100)
 * Series: One line per AHU in selected level
 * Fill: Gradient from accent at 30% → transparent
 */
const HealthIndexChart: React.FC<HealthIndexChartProps> = ({ data, devices }) => {
  // Generate colors from chart palette (repeating)
  const getColor = (index: number) => {
    const colors = ['#00E5A0', '#00B8D4', '#7C5CFC', '#FF6B8A', '#FFB020'];
    return colors[index % colors.length];
  };

  // Custom tooltip (Section 5.2)
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#1A2230] p-4 rounded-xl border border-[#1E2A3A]">
          <p className="text-[#8A95A5] text-xs mb-2 font-mono">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p
              key={index}
              className="text-sm"
              style={{ color: entry.color }}
            >
              {entry.name}: {entry.value.toFixed(1)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // Custom legend with highlight on hover
  const CustomLegend = ({ payload }: any) => {
    return (
      <div className="flex flex-wrap justify-center gap-4 mt-6">
        {payload.map((entry: any, index: number) => {
          const dev = devices.find((d) => d.name === entry.value);
          const tooltip = [dev?.label, dev?.department].filter(Boolean).join(' — ') || entry.value;
          return (
            <div key={index} className="flex items-center gap-2" title={tooltip}>
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-xs text-[#8A95A5]">{entry.value}</span>
            </div>
          );
        })}
      </div>
    );
  };

  if (!data || data.length === 0) {
    return (
      <div className="card p-6 h-[320px] flex items-center justify-center">
        <span className="text-[#8A95A5]">No health index data available</span>
      </div>
    );
  }

  return (
    <motion.div
      className="card p-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
    >
      {/* Header (Section 5.2) */}
      <div className="mb-6">
        <h3 className="font-display text-[24px] font-bold tracking-[-0.01em] flex items-center">
          Health Index
          <InfoTooltip text="Combined health score for each AHU. 0 = all systems healthy, 100 = critical failure risk. Calculated as a weighted sum of all five indicators: Phase Imbalance (25%), Power Factor (25%), Overload (20%), Energy Anomaly (15%), THD Drift (15%). Higher is better." />
        </h3>
        
        <p className="mt-2 text-sm text-[#8A95A5]">
          {devices.length} AHUs monitored • Last updated {new Date().toLocaleDateString()}
        </p>
      </div>

      {/* Chart container */}
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid
            stroke="#1E2A3A"
            strokeDasharray="3 3"
            vertical={false}
          />
          
          <XAxis
            dataKey="timestamp"
            stroke="#8A95A5"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            interval={Math.max(0, Math.floor(data.length / 8) - 1)}
          />
          
          <YAxis
            domain={[0, 100]}
            stroke="#8A95A5"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            interval={Math.max(0, Math.floor(data.length / 8) - 1)}
          />
          
          <Tooltip content={<CustomTooltip />} />
          
          <Legend
            wrapperStyle={{ paddingTop: 10 }}
            content={<CustomLegend />}
          />

          {/* Render area for each device */}
          {devices.map((device, index) => (
            <Area
              key={device.id}
              type="monotone"
              dataKey={device.name}
              stroke={getColor(index)}
              strokeWidth={2}
              fill="none"
              connectNulls
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </motion.div>
  );
};

export default HealthIndexChart;
