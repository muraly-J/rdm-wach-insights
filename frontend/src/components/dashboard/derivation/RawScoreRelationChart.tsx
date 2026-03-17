import React from 'react';
import { formatTickByRange, tickIntervalByRange, type TimeRange } from '../../../utils/formatTick';
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
  predictedData?: Array<{ timestamp: string; value: number }>; // Optional third line for energy anomaly
  scoreData: Array<{ timestamp: string; value: number }>;
  chartColor: string;
  headerAction?: React.ReactNode;
  timeRange: TimeRange;
}

/**
 * RawScoreRelationChart - Dual-axis chart for score derivation visualization (Section 5.5.1)
 *
 * Left Y-axis: Raw data value
 * Right Y-axis: Computed score (0-100)
 * X-axis: Time
 *
 * For energy anomaly, shows 3 lines:
 * - hourly_delta (raw consumption)
 * - predicted_delta (expected consumption from historical avg)
 * - energy_anomaly score
 *
 * For other scores, shows 2 lines (raw + score only)
 *
 * Netflix-style shelf layout with larger, more prominent charts
 */
const RawScoreRelationChart: React.FC<RawScoreRelationChartProps> = ({
  scoreName,
  rawMetric,
  rawUnit,
  rawData,
  predictedData,
  scoreData,
  chartColor,
  headerAction,
  timeRange,
}) => {
  // Merge data by timestamp
  const mergedData: any[] = [];

  rawData.forEach((point, idx) => {
    if (!mergedData[idx]) {
      mergedData[idx] = { timestamp: point.timestamp };
    }
    mergedData[idx].rawValue = point.value;
  });

  // Merge predicted data if available (for energy_anomaly)
  if (predictedData) {
    predictedData.forEach((point, idx) => {
      if (!mergedData[idx]) {
        mergedData[idx] = { timestamp: point.timestamp };
      }
      mergedData[idx].predictedValue = point.value;
    });
  }

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
      const predictedEntry = payload.find((p: any) => p.dataKey === 'predictedValue');

      return (
        <div className="bg-[#1A2230] p-4 rounded-xl border border-[#1E2A3A] shadow-2xl">
          <p className="text-[#8A95A5] text-xs mb-3 font-mono">{formatTickByRange(label, timeRange)}</p>

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

          {/* Show predicted_delta only for energy_anomaly */}
          {predictedEntry && (
            <div className="mb-2">
              <div
                className="text-xs text-[#8A95A5]"
                style={{ color: '#60A5FA' }}
              >
                predicted_delta (kWh)
              </div>
              <div
                className="text-sm font-medium"
                style={{ color: '#60A5FA' }}
              >
                {predictedEntry.value.toFixed(2)}
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
        transition-all duration-300
        w-full
      "
    >
      {/* Header (Section 5.5.1) */}
      <div className="flex items-start justify-between mb-4">
        <h4 className="text-[18px] font-semibold text-white">
          {scoreName}
        </h4>
        {headerAction && <div className="ml-2 flex-shrink-0">{headerAction}</div>}
      </div>

      {/* Dynamic description based on score type */}
      {scoreName === 'EnergyAnomaly' ? (
        <p className="text-[13px] text-[#8A95A5] mb-4 font-mono">
          hourly_delta → predicted_delta → Score: 0–100
        </p>
      ) : (
        <p className="text-[13px] text-[#8A95A5] mb-4 font-mono">
          Raw: {rawMetric} ({rawUnit}) → Score: 0–100
        </p>
      )}

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
            tickFormatter={(v) => formatTickByRange(v, timeRange)}
            interval={tickIntervalByRange(timeRange)}
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

          {/* Predicted delta line for energy anomaly (third line) */}
          {predictedData && predictedData.length > 0 && (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="predictedValue"
              stroke="#60A5FA"
              strokeWidth={2}
              strokeDasharray="4 4"
              opacity={0.7}
              dot={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex gap-4 mt-3">
        <div className="flex items-center gap-2 text-xs">
          <span
            className="w-3 h-1 rounded-full"
            style={{ backgroundColor: '#8A95A5' }}
          />
          <span className="text-[#8A95A5]">Raw ({rawMetric})</span>
        </div>
        {/* Show predicted_delta legend only for energy anomaly */}
        {predictedData && predictedData.length > 0 && (
          <div className="flex items-center gap-2 text-xs">
            <span
              className="w-3 h-1 rounded-full"
              style={{ backgroundColor: '#60A5FA' }}
            />
            <span className="text-[#8A95A5]">Predicted</span>
          </div>
        )}
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
