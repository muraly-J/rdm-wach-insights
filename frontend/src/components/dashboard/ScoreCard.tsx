import React from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

interface ScoreCardProps {
  title: string;
  value: number;
  trendValue: number; // percentage change
  data: Array<{ timestamp: string; value: number }>;
  chartColor: string;
}

/**
 * ScoreCard - Individual score card with sparkline (Section 5.3)
 * 
 * Contains:
 * 1. Score label
 * 2. Current average (large number, colored by health band)
 * 3. Sparkline (small LineChart)
 * 4. Trend indicator (↑ or ↓ with percentage)
 */
const ScoreCard: React.FC<ScoreCardProps> = ({
  title,
  value,
  trendValue,
  data,
  chartColor,
}) => {
  // Determine color based on health band (Section 5.3)
  const getColorByHealth = (val: number) => {
    if (val >= 80) return 'text-[#00E5A0]'; // success
    if (val >= 50) return 'text-[#FFB020]'; // warning
    return 'text-[#FF4D6A]'; // danger
  };

  const numberColor = getColorByHealth(value);
  const trendColor = trendValue >= 0 ? 'text-[#00E5A0]' : 'text-[#FF4D6A]';
  const trendIcon = trendValue >= 0 ? '↑' : '↓';

  return (
    <div
      className="
        card p-6 transition-all duration-0.25s ease
        hover:border-[#1E2A3A]
      "
    >
      {/* Score label (Section 5.3) */}
      <h4 className="text-[16px] font-semibold text-[#E8ECF1] mb-4">
        {title}
      </h4>

      {/* Current average (Section 5.3) */}
      <div className="flex items-baseline gap-2 mb-3">
        <span
          className={`font-mono text-[36px] font-bold ${numberColor}`}
        >
          {value.toFixed(1)}
        </span>
        <span className="text-[#8A95A5] text-sm">/ 100</span>
      </div>

      {/* Sparkline (Section 5.3) */}
      <div className="h-[80px] w-full mb-3">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <Line
              type="monotone"
              dataKey="value"
              stroke={chartColor}
              strokeWidth={1.5}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Trend indicator (Section 5.3) */}
      <div className="flex items-center gap-2 text-sm">
        <span className={`font-medium ${trendColor}`}>
          {trendIcon} {Math.abs(trendValue).toFixed(1)}%
        </span>
        <span className="text-[#8A95A5]">vs previous period</span>
      </div>
    </div>
  );
};

export default ScoreCard;
