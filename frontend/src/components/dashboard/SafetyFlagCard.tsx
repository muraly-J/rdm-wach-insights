import React from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

interface SafetyFlagCardProps {
  title: string;
  value: number;
  trend: number;
  info: React.ReactNode;
  chartColor: string;
  data: Array<{ timestamp: string; value: number }>;
}

/**
 * SafetyFlagCard — Full-width centered card for the highest-risk score.
 * Shown below the 3+2 score cards grid.
 */
const SafetyFlagCard: React.FC<SafetyFlagCardProps> = ({
  title,
  value,
  trend,
  info,
  chartColor,
  data,
}) => {
  const getRiskColor = (val: number) => {
    if (val <= 20) return 'text-[#4fbd95]';
    if (val <= 50) return 'text-[#f9a020]';
    return 'text-[#e96852]';
  };

  const getRiskBadgeColor = (val: number) => {
    if (val <= 20) return 'bg-[#4fbd95]/10 border-[#4fbd95]/30 text-[#4fbd95]';
    if (val <= 50) return 'bg-[#f9a020]/10 border-[#f9a020]/30 text-[#f9a020]';
    return 'bg-[#e96852]/10 border-[#e96852]/30 text-[#e96852]';
  };

  const getRiskLabel = (val: number) => {
    if (val <= 20) return 'Low Risk';
    if (val <= 50) return 'Moderate Risk';
    return 'High Risk';
  };

  const trendColor = trend <= 0 ? 'text-[#4fbd95]' : 'text-[#e96852]';
  const trendIcon = trend >= 0 ? '↑' : '↓';
  const numberColor = getRiskColor(value);

  return (
    <div
      className="card p-6"
      style={{
        background: 'rgba(255,255,255,0.04)',
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        border: '1px solid rgba(255,255,255,0.08)',
        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06), 0 8px 40px rgba(0,0,0,0.30)',
      }}
    >
      {/* Header row */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="text-[#6d6e71] text-xs font-display uppercase tracking-[0.15em]">
              Safety Flag
            </span>
            <span
              className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border
 ${getRiskBadgeColor(value)}`}
            >
              {getRiskLabel(value)}
            </span>
          </div>
          <h4 className="text-[20px] font-semibold text-[#E8ECF1]">{title}</h4>
        </div>

        {/* Big risk number */}
        <div className="text-right">
          <span className={`font-mono text-[48px] font-bold leading-none ${numberColor}`}>
            {value.toFixed(1)}
          </span>
          <span className="text-[#6d6e71] text-sm block">/ 100</span>
        </div>
      </div>

      {/* Sparkline + trend */}
      <div className="flex items-center gap-6 mb-4">
        <div className="flex-1 h-[60px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <Line
                type="monotone"
                dataKey="value"
                stroke={chartColor}
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="text-right shrink-0">
          <span className={`text-sm font-medium ${trendColor}`}>
            {trendIcon} {Math.abs(trend).toFixed(1)}%
          </span>
          <span className="text-[#6d6e71] text-xs block">vs previous period</span>
        </div>
      </div>

      {/* Explanation */}
      <div className="border-t border-[#2e3f55] pt-4">
        <p className="text-sm text-[#6d6e71] leading-relaxed">{info}</p>
      </div>
    </div>
  );
};

export default SafetyFlagCard;
