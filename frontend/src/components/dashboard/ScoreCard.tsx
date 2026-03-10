import React from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import InfoTooltip from '../shared/InfoTooltip';

interface ScoreCardProps {
  title: string;
  value: number;
  trendValue: number;
  data: Array<{ timestamp: string; value: number }>;
  chartColor: string;
  infoText?: string;
}

/**
 * ScoreCard — risk-direction scoring (0=healthy, 100=critical).
 */
const ScoreCard: React.FC<ScoreCardProps> = ({
  title,
  value,
  trendValue,
  data,
  chartColor,
  infoText,
}) => {
  // Risk direction: low value = green (good), high value = red (bad)
  const getRiskColor = (val: number) => {
    if (val <= 20) return 'text-[#00E5A0]';  // low risk
    if (val <= 50) return 'text-[#FFB020]';  // moderate risk
    return 'text-[#FF4D6A]';                 // high risk
  };

  const numberColor = getRiskColor(value);
  // For risk scores: increasing trend is bad (red), decreasing is good (green)
  const trendColor = trendValue <= 0 ? 'text-[#00E5A0]' : 'text-[#FF4D6A]';
  const trendIcon = trendValue >= 0 ? '↑' : '↓';

  return (
    <div className="card p-6 transition-all duration-0.25s ease hover:border-[#1E2A3A]">
      {/* Score label */}
      <h4 className="text-[16px] font-semibold text-[#E8ECF1] mb-4 flex items-center">
        {title}
        {infoText && <InfoTooltip text={infoText} />}
      </h4>

      {/* Current value */}
      <div className="flex items-baseline gap-2 mb-3">
        <span className={`font-mono text-[36px] font-bold ${numberColor}`}>
          {value.toFixed(1)}
        </span>
        <span className="text-[#8A95A5] text-sm">/ 100</span>
      </div>

      {/* Sparkline */}
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

      {/* Trend indicator */}
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
