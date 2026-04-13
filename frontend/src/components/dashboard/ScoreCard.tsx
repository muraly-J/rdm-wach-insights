import React from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import InfoTooltip from '../shared/InfoTooltip';

interface ScoreCardProps {
  title: string;
  value: number;
  trendValue: number;
  data: Array<{ timestamp: string; value: number }>;
  chartColor: string;
  infoText?: React.ReactNode;
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
    if (val <= 20) return 'text-[#4fbd95]'; // low risk
    if (val <= 50) return 'text-[#f9a020]'; // moderate risk
    return 'text-[#e96852]'; // high risk
  };

  const numberColor = getRiskColor(value);
  // For risk scores: increasing trend is bad (red), decreasing is good (green)
  const trendColor = trendValue <= 0 ? 'text-[#4fbd95]' : 'text-[#e96852]';
  const trendIcon = trendValue >= 0 ? '↑' : '↓';

  return (
    <div
      className="card p-4 sm:p-6 transition-all duration-0.25s ease hover:border-[#2e3f55]"
      style={{
        background: 'rgba(255,255,255,0.04)',
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        border: '1px solid rgba(255,255,255,0.08)',
        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06), 0 8px 40px rgba(0,0,0,0.30)',
      }}
    >
      {/* Score label */}
      <h4 className="text-[16px] font-semibold text-[#E8ECF1] mb-4 flex items-center">
        {title}
        {infoText && <InfoTooltip content={infoText} />}
      </h4>

      {/* Current value */}
      <div className="flex items-baseline gap-2 mb-3">
        <span className={`font-mono text-[28px] sm:text-[36px] font-bold ${numberColor}`}>
          {value.toFixed(1)}
        </span>
        <span className="text-[#6d6e71] text-sm">/ 100</span>
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
        <span className="text-[#6d6e71]">vs previous period</span>
      </div>
    </div>
  );
};

export default ScoreCard;
