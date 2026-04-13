import React from 'react';
import { AreaChart, Area, ResponsiveContainer, YAxis } from 'recharts';
import InfoTooltip from '../shared/InfoTooltip';

interface SafetyFlagCardProps {
  title: string;
  value: number;
  trend: number;
  info?: React.ReactNode;
  chartColor: string;
  data: Array<{ timestamp: string; value: number }>;
}

/**
 * SafetyFlagCard — highlights the highest-risk score as a prominent banner card.
 * Shows the score with a wider sparkline area chart to draw attention.
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
    if (val <= 20) return '#4fbd95';
    if (val <= 50) return '#f9a020';
    return '#e96852';
  };

  const riskColor = getRiskColor(value);
  const trendColor = trend <= 0 ? '#4fbd95' : '#e96852';
  const trendIcon = trend >= 0 ? '↑' : '↓';

  const riskLabel = value <= 20 ? 'Low Risk' : value <= 50 ? 'Moderate Risk' : 'High Risk';

  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.04)',
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        border: `1px solid ${riskColor}44`,
        borderRadius: 12,
        padding: '16px 20px',
        boxShadow: `inset 0 1px 0 rgba(255,255,255,0.06), 0 8px 40px rgba(0,0,0,0.30), 0 0 0 1px ${riskColor}22`,
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span
            style={{
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: riskColor,
              background: `${riskColor}18`,
              border: `1px solid ${riskColor}44`,
              borderRadius: 4,
              padding: '2px 6px',
            }}
          >
            Top Risk Score
          </span>
          <span style={{ color: '#E8ECF1', fontSize: 14, fontWeight: 600 }}>{title}</span>
          {info && <InfoTooltip content={info} />}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ color: riskColor, fontSize: 10, fontWeight: 600 }}>{riskLabel}</span>
          <span style={{ color: trendColor, fontSize: 13, fontWeight: 600 }}>
            {trendIcon} {Math.abs(trend).toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Value + sparkline row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <div style={{ flexShrink: 0 }}>
          <span
            style={{
              fontFamily: 'var(--font-mono, monospace)',
              fontSize: 40,
              fontWeight: 700,
              color: riskColor,
              lineHeight: 1,
            }}
          >
            {value.toFixed(1)}
          </span>
          <span style={{ color: '#556677', fontSize: 13, marginLeft: 4 }}>/ 100</span>
        </div>

        <div style={{ flex: 1, height: 60 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 4 }}>
              <defs>
                <linearGradient
                  id={`sfg-${chartColor.replace('#', '')}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="5%" stopColor={chartColor} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <YAxis domain={[0, 100]} hide />
              <Area
                type="monotone"
                dataKey="value"
                stroke={chartColor}
                strokeWidth={1.5}
                fill={`url(#sfg-${chartColor.replace('#', '')})`}
                dot={false}
                connectNulls
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default SafetyFlagCard;
