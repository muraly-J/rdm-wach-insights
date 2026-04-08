import React from 'react';
import type { SiteSummaryData } from '../../types';

interface KPIStripProps {
  summary: SiteSummaryData | null;
  selectedLevel: number | null;
  selectedDevice: string | null;
  deviceLabel: string | null;
  deviceHealth: number | null;
}

interface KPICardProps {
  label: string;
  value: string | number;
  valueColor?: string;
  small?: boolean;
}

const KPICard: React.FC<KPICardProps> = ({ label, value, valueColor = '#E8ECF1', small = false }) => (
  <div style={{
    background: '#1a2234',
    border: '1px solid #2a3649',
    borderRadius: 10,
    padding: '10px 14px',
    flex: 1,
    minWidth: 0,
  }}>
    <div style={{ color: '#556677', fontSize: 9, fontWeight: 600, letterSpacing: '0.06em', marginBottom: 4, textTransform: 'uppercase' }}>
      {label}
    </div>
    <div style={{ color: valueColor, fontSize: small ? 11 : 20, fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
      {value}
    </div>
  </div>
);

const KPIStrip: React.FC<KPIStripProps> = ({ summary, selectedLevel, selectedDevice, deviceLabel, deviceHealth }) => {
  if (!summary) {
    return (
      <div className="flex gap-3 mb-6">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} style={{ flex: 1, height: 60, background: '#1a2234', borderRadius: 10, animation: 'pulse 1.5s infinite' }} />
        ))}
      </div>
    );
  }

  const healthValue = selectedDevice
    ? (deviceHealth !== null ? String(deviceHealth) : '—')
    : summary.avgSiteHealth.toFixed(1);

  const healthColor = (() => {
    const v = selectedDevice ? deviceHealth : summary.avgSiteHealth;
    if (v === null) return '#8899aa';
    if (v >= 80) return '#00E5A0';
    if (v >= 60) return '#f59e0b';
    return '#ff6b6b';
  })();

  const alertColor = summary.ahusInAlert > 0 ? '#ff6b6b' : '#00E5A0';

  return (
    <div className="flex gap-3 mb-6 flex-wrap">
      <KPICard
        label={selectedDevice ? 'AHU Health' : selectedLevel ? 'Level Health' : 'Site Health'}
        value={healthValue}
        valueColor={healthColor}
      />
      <KPICard
        label="Total AHUs"
        value={summary.totalAHUs}
      />
      <KPICard
        label="In Alert"
        value={summary.ahusInAlert}
        valueColor={alertColor}
      />
      {selectedDevice ? (
        <KPICard
          label="Device"
          value={deviceLabel ?? selectedDevice}
          small
          valueColor="#8899aa"
        />
      ) : (
        <KPICard
          label="Best AHU"
          value={summary.starAHU.name}
          small
          valueColor="#00E5A0"
        />
      )}
      {!selectedDevice && (
        <KPICard
          label="Worst AHU"
          value={summary.criticalAHU.name}
          small
          valueColor="#ff6b6b"
        />
      )}
    </div>
  );
};

export default KPIStrip;
