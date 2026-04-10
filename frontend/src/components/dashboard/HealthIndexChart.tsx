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
import { formatDateMYT } from '../../utils/formatTick';

interface HealthIndexChartProps {
  data: Array<{ timestamp: string; [key: string]: number; originalTs?: string; is_on?: boolean }>;
  devices: Array<{ id: string; name: string; label?: string; department?: string }>;
  showColorSegments?: boolean;
}

/**
 * HealthIndexChart - Time-series health index chart (Section 5.2)
 *
 * Library: Recharts AreaChart
 * Y-axis: Health Index (0-100)
 * Series: One line per AHU in selected level
 * Fill: Gradient from accent at 30% → transparent
 * Off-time sections: Greyed out stroke and reduced opacity
 */
const HealthIndexChart: React.FC<HealthIndexChartProps> = ({ data, devices, showColorSegments = false }) => {
  // Generate colors from chart palette (repeating)
  const getColor = (index: number) => {
    const colors = [
      '#4fbd95', // teal-green (original accent)
      '#00a9a5', // cyan
      '#00aeef', // purple
      '#e96852', // pink-red
      '#f9a020', // amber
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

  // Invert a hex color
  const invertColor = (hex: string): string => {
    hex = hex.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    const invR = (255 - r).toString(16).padStart(2, '0');
    const invG = (255 - g).toString(16).padStart(2, '0');
    const invB = (255 - b).toString(16).padStart(2, '0');
    return `#${invR}${invG}${invB}`;
  };

  // Custom tooltip (Section 5.2)
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#2a3649] p-4 rounded-xl border border-[#2e3f55]">
          <p className="text-[#6d6e71] text-xs mb-2 font-mono">{label}</p>
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
              <span className="text-xs text-[#6d6e71]">{entry.value}</span>
            </div>
          );
        })}
      </div>
    );
  };

  const glassStyle: React.CSSProperties = {
    background: 'rgba(255,255,255,0.04)',
    backdropFilter: 'blur(20px) saturate(180%)',
    WebkitBackdropFilter: 'blur(20px) saturate(180%)',
    border: '1px solid rgba(255,255,255,0.08)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06), 0 8px 40px rgba(0,0,0,0.30)',
  };

  if (!data || data.length === 0) {
    return (
      <div className="card p-4 sm:p-6 h-[200px] sm:h-[320px] flex items-center justify-center" style={glassStyle}>
        <span className="text-[#6d6e71]">No health index data available</span>
      </div>
    );
  }

  return (
    <motion.div
      className="card p-4 sm:p-6"
      style={glassStyle}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
    >
      {/* Header (Section 5.2) */}
      <div className="mb-6">
        <h3 className="font-display text-[20px] sm:text-[24px] font-bold tracking-[-0.01em] flex items-center">
          Health Index
          <InfoTooltip content={
            <div className="space-y-2.5">
              <p className="text-[#E8ECF1] font-semibold text-[11px]">Composite AHU Health Index</p>
              <p>Weighted sum of five FAIR sub-scores, each normalised 0–100. Higher is healthier.</p>
              <div>
                <p className="text-[#E8ECF1] font-medium mb-1">Formula</p>
                <p className="font-mono bg-[#1c2431] rounded px-2 py-1 text-[10px]">
                  HI = 0.25·PF + 0.25·PI + 0.20·OL + 0.15·EA + 0.15·THD
                </p>
              </div>
              <div>
                <p className="text-[#E8ECF1] font-medium mb-1">Tiers</p>
                <div className="space-y-0.5">
                  <p><span className="text-[#4fbd95]">■</span> 80–100 Healthy — normal operation</p>
                  <p><span className="text-yellow-400">■</span> 60–79 Monitor — watch for drift</p>
                  <p><span className="text-orange-400">■</span> 40–59 Maintenance Soon — schedule service</p>
                  <p><span className="text-red-400">■</span> 0–39 Critical — urgent intervention</p>
                </div>
              </div>
              <p className="text-[#4A5568] text-[10px]">Weights follow ASHRAE 180-2012 risk priority for HVAC fault detection.</p>
            </div>
          } />
        </h3>
        
        <p className="mt-2 text-sm text-[#6d6e71]">
          {devices.length} AHUs monitored • Last updated {formatDateMYT(new Date(), { month: 'short', day: 'numeric', year: 'numeric' })}
        </p>
      </div>

      {/* Chart container — legend rendered outside so it never eats into chart height */}
      <div className="h-[200px] sm:h-[280px] lg:h-[320px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid
            stroke="#2e3f55"
            strokeDasharray="3 3"
            vertical={false}
          />

          <XAxis
            dataKey="timestamp"
            stroke="#6d6e71"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            interval={Math.max(0, Math.floor(data.length / 8) - 1)}
          />

          <YAxis
            domain={[0, 100]}
            stroke="#6d6e71"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            interval={Math.max(0, Math.floor(data.length / 8) - 1)}
          />

          <Tooltip content={<CustomTooltip />} />

          {/* Multi-device: simple lines, no color segments */}
          {!showColorSegments && devices.map((device, index) => (
            <Area
              key={device.id}
              type="monotone"
              dataKey={device.name}
              stroke={getColor(index)}
              strokeWidth={2}
              fill="none"
              connectNulls
              dot={false}
            />
          ))}

          {/* Single device: render on/off color segments */}
          {showColorSegments && devices.map((device, index) => {
            const baseColor = getColor(index);
            const invertedColor = invertColor(baseColor);

            return (
              <React.Fragment key={device.id}>
                {/* On-time: normal color */}
                <Area
                  type="monotone"
                  dataKey={device.name}
                  data={data}
                  stroke={baseColor}
                  strokeWidth={2}
                  fill="none"
                  connectNulls
                  dot={false}
                  shape={(props: any) => {
                    const { points } = props;
                    if (!points || points.length === 0) return null;

                    let pathD = '';
                    for (let i = 0; i < points.length; i++) {
                      const point = points[i];
                      if (point && (data[i] as any).is_on !== false) {
                        const cmd = i === 0 ? 'M' : 'L';
                        pathD += `${cmd} ${point.x} ${point.y} `;
                      }
                    }
                    return <path d={pathD} stroke={baseColor} strokeWidth={2} fill="none" />;
                  }}
                />

                {/* Off-time: inverted color */}
                <Area
                  type="monotone"
                  dataKey={device.name}
                  data={data}
                  stroke={invertedColor}
                  strokeWidth={2}
                  fill="none"
                  connectNulls
                  dot={false}
                  opacity={0.7}
                  shape={(props: any) => {
                    const { points } = props;
                    if (!points || points.length === 0) return null;

                    let pathD = '';
                    for (let i = 0; i < points.length; i++) {
                      const point = points[i];
                      if (point && (data[i] as any).is_on === false) {
                        const cmd = i === 0 ? 'M' : 'L';
                        pathD += `${cmd} ${point.x} ${point.y} `;
                      }
                    }
                    return <path d={pathD} stroke={invertedColor} strokeWidth={2} fill="none" opacity={0.7} />;
                  }}
                />
              </React.Fragment>
            );
          })}
        </AreaChart>
      </ResponsiveContainer>
      </div>

      {/* Legend outside the fixed-height div so it never squishes the chart */}
      <CustomLegend payload={devices.map((device, index) => ({ value: device.name, color: getColor(index) }))} />
    </motion.div>
  );
};

export default HealthIndexChart;
