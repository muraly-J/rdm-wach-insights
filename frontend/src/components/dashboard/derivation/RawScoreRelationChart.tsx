import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface RawScoreRelationChartProps {
  scoreName: string;
  rawMetric: string;
  rawUnit: string;
  rawData: Array<{ timestamp: string; value: number }>;
  scoreData: Array<{ timestamp: string; value: number }>;
  chartColor: string;
}

/**
 * RawScoreRelationChart - Dual-axis chart for score derivation visualization (Section 5.5.1)
 *
 * Left Y-axis: Raw data value
 * Right Y-axis: Computed score (0-100)
 * X-axis: Time
 * 
 * Netflix-style shelf layout with larger, more prominent charts
 */
const RawScoreRelationChart: React.FC<RawScoreRelationChartProps> = ({
  scoreName,
  rawMetric,
  rawUnit,
  rawData,
  scoreData,
  chartColor,
}) => {
  // Merge data by timestamp
  const mergedData: any[] = [];

  rawData.forEach((point, idx) => {
    if (!mergedData[idx]) {
      mergedData[idx] = { timestamp: point.timestamp };
    }
    mergedData[idx].rawValue = point.value;
  });

  scoreData.forEach((point, idx) => {
    if (mergedData[idx]) {
      mergedData[idx].scoreValue = point.value;
    }
  });

  // Custom tooltip showing both values
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const rawEntry = payload.find((p: any) => p.dataKey === 'rawValue');
      const scoreEntry = payload.find((p: any) => p.dataKey === 'scoreValue');

      return (
        <div className="bg-[#1A2230] p-4 rounded-xl border border-[#1E2A3A] shadow-2xl">
          <p className="text-[#8A95A5] text-xs mb-3 font-mono">{label}</p>

          {rawEntry && (
            <div className="mb-2">
              <div
                className="text-xs text-[#8A95A5]"
                style={{ color: '#8A95A5' }}
              >
                {rawMetric} ({rawUnit})
              </div>
              <div
                className="text-sm font-medium"
                style={{ color: '#8A95A5' }}
              >
                {rawEntry.value.toFixed(2)}
              </div>
            </div>
          )}

          {scoreEntry && (
            <div>
              <div
                className="text-xs text-[#8A95A5]"
                style={{ color: chartColor }}
              >
                Score
              </div>
              <div
                className="text-sm font-medium"
                style={{ color: chartColor }}
              >
                {scoreEntry.value.toFixed(1)} / 100
              </div>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  // YAxis styles
  const leftAxisStyle = { stroke: '#8A95A5' };
  const rightAxisStyle = { stroke: chartColor };

  return (
    <div
      className="
        card p-6
        hover:border-[#1E2A3A]
        min-w-[400px] w-[400px] md:min-w-[500px] md:w-[500px]
        transition-all duration-300
      "
    >
      {/* Header (Section 5.5.1) */}
      <h4 className="text-[18px] font-semibold mb-4 text-white">
        {scoreName}
      </h4>

      <p className="text-[13px] text-[#8A95A5] mb-4 font-mono">
        Raw: {rawMetric} ({rawUnit}) → Score: 0–100
      </p>

      {/* Chart - Larger height for shelf layout */}
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={mergedData} margin={{ top: 15, right: 40, left: 0, bottom: 25 }}>
          <CartesianGrid
            stroke="#1E2A3A"
            strokeDasharray="3 3"
            vertical={false}
          />

          <XAxis
            dataKey="timestamp"
            stroke="#8A95A5"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            minTickGap={30}
          />

          {/* Left Y-axis: Raw data */}
          <YAxis
            yAxisId="left"
            stroke="#8A95A5"
            fontSize={11}
            tickLine={false}
            axisLine={leftAxisStyle as any}
            domain={['auto', 'auto']}
          />

          {/* Right Y-axis: Score */}
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke={chartColor}
            fontSize={11}
            tickLine={false}
            axisLine={rightAxisStyle as any}
            domain={[0, 100]}
          />

          <Tooltip content={<CustomTooltip />} />

          {/* Raw data series (thin line, secondary color) */}
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="rawValue"
            stroke="#8A95A5"
            strokeWidth={2}
            opacity={0.6}
            dot={false}
          />

          {/* Score series (thicker line, chart color with fill) */}
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="scoreValue"
            stroke={chartColor}
            strokeWidth={3}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex gap-4 mt-3">
        <div className="flex items-center gap-2 text-xs">
          <span
            className="w-3 h-1 rounded-full"
            style={{ backgroundColor: '#8A95A5' }}
          />
          <span className="text-[#8A95A5]">Raw</span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span
            className="w-3 h-1 rounded-full"
            style={{ backgroundColor: chartColor }}
          />
          <span className="text-[#8A95A5]">Score</span>
        </div>
      </div>
    </div>
  );
};

export default RawScoreRelationChart;
