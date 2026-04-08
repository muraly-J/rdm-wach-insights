import React from 'react';
import type { AHUStatus } from './AHURankingsTable';

interface DeviceDetailCardProps {
  label: string;
  level: number;
  healthScore: number;
  trend: number;
  status: AHUStatus;
}

const STATUS_COLOR: Record<AHUStatus, string> = {
  Good: '#00E5A0',
  Warning: '#f59e0b',
  Critical: '#ff6b6b',
};

const DeviceDetailCard: React.FC<DeviceDetailCardProps> = ({ label, level, healthScore, trend, status }) => (
  <div style={{
    background: '#1a2234', border: `1px solid ${STATUS_COLOR[status]}44`,
    borderRadius: 12, padding: '16px 20px', marginBottom: 24,
    display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap',
  }}>
    <div style={{ flex: 1, minWidth: 200 }}>
      <div style={{ fontSize: 10, color: '#556677', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
        Selected Device — Level {level}
      </div>
      <div style={{ fontSize: 14, color: '#E8ECF1', fontWeight: 600 }}>{label}</div>
    </div>
    <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 10, color: '#556677', marginBottom: 2 }}>HEALTH</div>
        <div style={{ fontSize: 24, fontWeight: 700, color: STATUS_COLOR[status] }}>{Math.round(healthScore)}</div>
      </div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 10, color: '#556677', marginBottom: 2 }}>TREND</div>
        <div style={{ fontSize: 14, fontWeight: 600, color: trend >= 0 ? '#00E5A0' : '#ff6b6b' }}>
          {trend >= 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}%
        </div>
      </div>
      <span style={{
        background: `${STATUS_COLOR[status]}22`, color: STATUS_COLOR[status],
        border: `1px solid ${STATUS_COLOR[status]}55`,
        borderRadius: 20, padding: '4px 12px', fontSize: 11, fontWeight: 600,
      }}>
        {status}
      </span>
    </div>
  </div>
);

export default DeviceDetailCard;
