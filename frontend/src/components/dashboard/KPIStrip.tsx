import React, { useState } from 'react';
import type { SiteSummaryData } from '../../types';
import { useAppStore } from '../../store/useAppStore';
import AlertsModal from './AlertsModal';

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
  subtitle?: string;
  onClick?: () => void;
}

const KPICard: React.FC<KPICardProps> = ({
  label,
  value,
  valueColor = '#E8ECF1',
  small = false,
  subtitle,
  onClick,
}) => (
  <div
    onClick={onClick}
    style={{
      background: '#1a2234',
      border: '1px solid #2a3649',
      borderRadius: 10,
      padding: '10px 14px',
      flex: 1,
      minWidth: 0,
      cursor: onClick ? 'pointer' : 'default',
    }}
  >
    <div
      style={{
        color: '#556677',
        fontSize: 9,
        fontWeight: 600,
        letterSpacing: '0.06em',
        marginBottom: 4,
        textTransform: 'uppercase',
      }}
    >
      {label}
    </div>
    <div
      style={{
        color: valueColor,
        fontSize: small ? 11 : 20,
        fontWeight: 700,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: small ? 'normal' : 'nowrap',
        lineHeight: 1.3,
      }}
    >
      {value}
    </div>
    {subtitle && (
      <div
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9,
          color: '#445566',
          marginTop: 3,
          letterSpacing: '0.04em',
        }}
      >
        {subtitle}
      </div>
    )}
  </div>
);

const KPIStrip: React.FC<KPIStripProps> = ({
  summary,
  selectedLevel,
  selectedDevice,
  deviceLabel,
  deviceHealth,
}) => {
  const { selectLevel, selectDevice } = useAppStore();
  const [alertsOpen, setAlertsOpen] = useState(false);
  if (!summary) {
    return (
      <div className="flex gap-3 mb-6">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: 60,
              background: '#1a2234',
              borderRadius: 10,
              animation: 'pulse 1.5s infinite',
            }}
          />
        ))}
      </div>
    );
  }

  const healthValue = selectedDevice
    ? deviceHealth !== null
      ? String(deviceHealth)
      : '—'
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
    <>
      <AlertsModal
        isOpen={alertsOpen}
        onClose={() => setAlertsOpen(false)}
        ahus={summary.alertAHUs ?? []}
        alertCount={summary.ahusInAlert}
      />
      <div className="flex gap-3 mb-6 flex-wrap">
        <KPICard
          label={selectedDevice ? 'AHU Health' : selectedLevel ? 'Level Health' : 'Site Health'}
          value={healthValue}
          valueColor={healthColor}
        />
        <KPICard label="Total AHUs" value={summary.totalAHUs} />
        <KPICard
          label="In Alert"
          value={summary.ahusInAlert}
          valueColor={alertColor}
          subtitle={summary.ahusInAlert > 0 ? 'Click to Inspect' : undefined}
          onClick={summary.ahusInAlert > 0 ? () => setAlertsOpen(true) : undefined}
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
            subtitle={summary.starAHU.id}
            small
            valueColor="#00E5A0"
            onClick={() => {
              selectLevel(summary.starAHU.level);
              selectDevice(summary.starAHU.id);
            }}
          />
        )}
        {!selectedDevice && (
          <KPICard
            label="Worst AHU"
            value={summary.criticalAHU.name}
            subtitle={summary.criticalAHU.id}
            small
            valueColor="#ff6b6b"
            onClick={() => {
              selectLevel(summary.criticalAHU.level);
              selectDevice(summary.criticalAHU.id);
            }}
          />
        )}
      </div>
    </>
  );
};

export default KPIStrip;
