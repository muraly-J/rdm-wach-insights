import React from 'react';
import type { AHUStatus } from './AHURankingsTable';

interface DeviceDetailCardProps {
  label: string;
  level: number;
  healthScore: number;
  trend: number;
  status: AHUStatus;
  isOn?: boolean;
}

const STATUS_COLOR: Record<AHUStatus, string> = {
  Good: '#00E5A0',
  Warning: '#f59e0b',
  Critical: '#ff6b6b',
};

const DeviceDetailCard: React.FC<DeviceDetailCardProps> = ({ label, level, healthScore, trend, status, isOn = true }) => (
  <div style={{
    background: '#1a2234', border: `1px solid ${isOn ? STATUS_COLOR[status] : '#556677'}44`,
    borderRadius: 12, padding: '16px 20px', marginBottom: 24,
    display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap',
    opacity: isOn ? 1 : 0.45,
    filter: isOn ? 'none' : 'grayscale(80%)',
  }}>
    <div style={{ flex: 1, minWidth: 200 }}>
      <div style={{ fontSize: 10, color: '#556677', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
        Selected Device — Level {level}
      </div>
      <div style={{ fontSize: 14, color: '#E8ECF1', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
        {label}
        {!isOn && (
          <span style={{ fontSize: 10, color: '#556677', background: '#0B0F14', border: '1px solid #2a3649', borderRadius: 4, padding: '2px 6px', fontWeight: 600, letterSpacing: '0.05em' }}>
            OFF
          </span>
        )}
      </div>
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
