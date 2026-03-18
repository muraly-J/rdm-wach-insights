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
    const colors = [
      '#00E5A0', // teal-green (original accent)
      '#00B8D4', // cyan
      '#7C5CFC', // purple
      '#FF6B8A', // pink-red
      '#FFB020', // amber
      '#F97316', // orange
      '#84CC16', // lime
      '#38BDF8', // sky-blue
      '#C084FC', // light-purple
      '#F43F5E', // rose
      '#22D3EE', // light-cyan
      '#4ADE80', // light-green
      '#FB923C', // peach
      '#818CF8', // indigo
      '#F472B6', // light-pink
      '#A3E635', // yellow-green
      '#FCD34D', // gold
      '#34D399', // emerald
      '#60A5FA', // blue
      '#E879F9', // fuchsia
      '#2DD4BF', // teal
      '#FCA5A5', // light-red
      '#86EFAC', // pale-green
      '#FDE68A', // pale-yellow
    ];
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
          <InfoTooltip content={
            <div className="space-y-2.5">
              <p className="text-[#E8ECF1] font-semibold text-[11px]">Composite AHU Health Index</p>
              <p>Weighted sum of five FAIR sub-scores, each normalised 0–100. Higher is healthier.</p>
              <div>
                <p className="text-[#E8ECF1] font-medium mb-1">Formula</p>
                <p className="font-mono bg-[#0B0F14] rounded px-2 py-1 text-[10px]">
                  HI = 0.25·PF + 0.25·PI + 0.20·OL + 0.15·EA + 0.15·THD
                </p>
              </div>
              <div>
                <p className="text-[#E8ECF1] font-medium mb-1">Tiers</p>
                <div className="space-y-0.5">
                  <p><span className="text-[#00E5A0]">■</span> 80–100 Healthy — normal operation</p>
                  <p><span className="text-yellow-400">■</span> 60–79 Monitor — watch for drift</p>
                  <p><span className="text-orange-400">■</span> 40–59 Maintenance Soon — schedule service</p>
                  <p><span className="text-red-400">■</span> 0–39 Critical — urgent intervention</p>
                </div>
              </div>
              <p className="text-[#4A5568] text-[10px]">Weights follow ASHRAE 180-2012 risk priority for HVAC fault detection.</p>
            </div>
          } />
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
