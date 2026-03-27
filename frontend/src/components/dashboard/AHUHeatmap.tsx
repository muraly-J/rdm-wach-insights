import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import { apiFetch } from '../../api/client';

interface HourScores {
  energy_anomaly: number | null;
  pf_degradation: number | null;
  phase_imbalance: number | null;
  thd_drift: number | null;
  overload: number | null;
}

interface HourEntry {
  hour: number;
  avg_health: number | null;
  scores: HourScores;
}

interface HeatmapData {
  ahu_id: string;
  range: string;
  hours: HourEntry[];
}

interface Props {
  ahuId: string;
}

const SHADOW_NONE = '0 0 0px rgba(0,0,0,0)';

function healthColor(score: number | null): { bg: string; text: string; glow: string; accent: string } {
  if (score === null) return { bg: '#1A2230', text: '#3A4455', glow: SHADOW_NONE, accent: '#3A4455' };
  if (score >= 80) return { bg: '#00E5A0', text: '#0B0F14', glow: '0 0 18px rgba(0,229,160,0.55)', accent: '#00E5A0' };
  if (score >= 60) return { bg: '#F59E0B', text: '#0B0F14', glow: '0 0 18px rgba(245,158,11,0.55)', accent: '#F59E0B' };
  if (score >= 40) return { bg: '#F97316', text: '#0B0F14', glow: '0 0 18px rgba(249,115,22,0.55)', accent: '#F97316' };
  return { bg: '#EF4444', text: '#ffffff', glow: '0 0 18px rgba(239,68,68,0.55)', accent: '#EF4444' };
}

function scoreColor(score: number | null): string {
  if (score === null) return '#3A4455';
  if (score >= 80) return '#00E5A0';
  if (score >= 60) return '#F59E0B';
  if (score >= 40) return '#F97316';
  return '#EF4444';
}

function healthLabel(score: number | null): string {
  if (score === null) return 'No data';
  if (score >= 80) return 'Healthy';
  if (score >= 60) return 'Monitor';
  if (score >= 40) return 'Maintenance Soon';
  return 'Critical';
}

function formatHour(h: number): string {
  if (h === 0) return '12 AM';
  if (h === 12) return '12 PM';
  return h < 12 ? `${h} AM` : `${h - 12} PM`;
}

const SCORE_LABELS: { key: keyof HourScores; label: string }[] = [
  { key: 'energy_anomaly',  label: 'Energy Anomaly' },
  { key: 'pf_degradation',  label: 'PF Degradation' },
  { key: 'phase_imbalance', label: 'Phase Imbalance' },
  { key: 'thd_drift',       label: 'THD Drift' },
  { key: 'overload',        label: 'Overload' },
];

/** Tooltip — diagnostic readout panel */
function HoverTooltip({ entry, bg }: { entry: HourEntry; bg: string }) {
  const isLeft = entry.hour >= 18; // flip to left side for last 6 cells
  const isTop  = entry.hour >= 12; // flip above for bottom row

  return (
    <motion.div
      className="absolute z-30 pointer-events-none"
      style={{
        bottom: isTop ? 'calc(100% + 10px)' : undefined,
        top: !isTop ? 'calc(100% + 10px)' : undefined,
        right: isLeft ? 0 : undefined,
        left: !isLeft ? 0 : undefined,
        minWidth: 220,
      }}
      initial={{ opacity: 0, y: isTop ? 6 : -6, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: isTop ? 6 : -6, scale: 0.96 }}
      transition={{ duration: 0.15, ease: [0.22, 1, 0.36, 1] }}
    >
      <div
        style={{
          background: 'rgba(9, 14, 22, 0.97)',
          border: `1px solid ${bg}40`,
          borderRadius: 12,
          boxShadow: `0 20px 48px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.04), 0 0 24px ${bg}18`,
          overflow: 'hidden',
        }}
      >
        {/* Header strip */}
        <div
          style={{
            background: `linear-gradient(135deg, ${bg}18 0%, transparent 100%)`,
            borderBottom: `1px solid ${bg}25`,
            padding: '10px 14px 8px',
          }}
        >
          <div className="flex items-baseline justify-between gap-3">
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: '#8A95A5',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}
            >
              {formatHour(entry.hour)}
            </span>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 18,
                fontWeight: 700,
                color: bg,
                letterSpacing: '-0.02em',
                lineHeight: 1,
              }}
            >
              {entry.avg_health !== null ? entry.avg_health.toFixed(1) : '—'}
            </span>
          </div>
          <div className="flex items-center justify-between mt-1">
            <span
              style={{
                fontSize: 10,
                color: `${bg}CC`,
                fontFamily: 'var(--font-display)',
                fontWeight: 600,
              }}
            >
              {healthLabel(entry.avg_health)}
            </span>
            <span style={{ fontSize: 9, color: '#4A5568', fontFamily: 'var(--font-mono)' }}>
              HEALTH INDEX
            </span>
          </div>
        </div>

        {/* Score rows */}
        <div style={{ padding: '8px 14px 10px' }}>
          {SCORE_LABELS.map(({ key, label }) => {
            const val = entry.scores?.[key] ?? null;
            const col = scoreColor(val);
            const pct = val !== null ? Math.min(100, Math.max(0, val)) : 0;
            return (
              <div
                key={key}
                style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}
              >
                {/* Label */}
                <span
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: 10,
                    color: '#6B7888',
                    width: 96,
                    flexShrink: 0,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {label}
                </span>

                {/* Bar track */}
                <div
                  style={{
                    flex: 1,
                    height: 3,
                    background: 'rgba(255,255,255,0.06)',
                    borderRadius: 99,
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${pct}%`,
                      height: '100%',
                      background: val !== null ? col : 'transparent',
                      borderRadius: 99,
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>

                {/* Value */}
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 10,
                    fontWeight: 600,
                    color: val !== null ? col : '#3A4455',
                    width: 28,
                    textAlign: 'right',
                    flexShrink: 0,
                  }}
                >
                  {val !== null ? val.toFixed(0) : '—'}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}

const AHUHeatmap: React.FC<Props> = ({ ahuId }) => {
  const timeRange = useAppStore((s) => s.timeRange);
  const [data, setData] = React.useState<HeatmapData | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [hovered, setHovered] = React.useState<number | null>(null);

  React.useEffect(() => {
    setLoading(true);
    setError(null);
    setData(null);
    apiFetch<HeatmapData>(`/dashboard/ahu-heatmap?ahu_id=${encodeURIComponent(ahuId)}&range=${timeRange}`)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [ahuId, timeRange]);

  const bestHour = React.useMemo(() => {
    if (!data) return null;
    const valid = data.hours.filter((h) => h.avg_health !== null);
    if (!valid.length) return null;
    return valid.reduce((a, b) => (a.avg_health! > b.avg_health! ? a : b));
  }, [data]);

  const worstHour = React.useMemo(() => {
    if (!data) return null;
    const valid = data.hours.filter((h) => h.avg_health !== null);
    if (!valid.length) return null;
    return valid.reduce((a, b) => (a.avg_health! < b.avg_health! ? a : b));
  }, [data]);

  const rangeLabel = { '24h': 'past 24 hours', '7d': 'past 7 days', '30d': 'past 30 days' }[timeRange] ?? timeRange;

  return (
    <motion.div
      className="card p-0 overflow-visible"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Header */}
      <div className="px-6 py-4 border-b border-[#1E2A3A] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h3 className="font-display text-[18px] font-bold tracking-tight flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-[#00E5A0] shadow-[0_0_8px_rgba(0,229,160,0.7)]" />
            Hourly Health Pattern
          </h3>
          <p className="text-xs text-[#8A95A5] mt-0.5">
            Average health index by hour of day · {rangeLabel}
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-[10px] text-[#8A95A5]">
          {[
            { label: 'Healthy',          color: '#00E5A0' },
            { label: 'Monitor',          color: '#F59E0B' },
            { label: 'Maintenance Soon', color: '#F97316' },
            { label: 'Critical',         color: '#EF4444' },
          ].map(({ label, color }) => (
            <span key={label} className="flex items-center gap-1">
              <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: color }} />
              {label}
            </span>
          ))}
        </div>
      </div>

      {/* Body */}
      <div className="px-6 py-5">
        {loading && (
          <div className="grid grid-cols-6 gap-2">
            {Array.from({ length: 24 }).map((_, i) => (
              <div key={i} className="aspect-square rounded-lg bg-[#1A2230] animate-pulse" />
            ))}
          </div>
        )}

        {error && !loading && (
          <div className="flex items-center justify-center h-32 text-[#8A95A5] text-sm">
            Failed to load heatmap data
          </div>
        )}

        {data && !loading && (
          <>
            {/* 6×4 grid */}
            <div className="grid grid-cols-6 gap-2" style={{ position: 'relative' }}>
              {data.hours.map((entry, idx) => {
                const { bg, text, glow } = healthColor(entry.avg_health);
                const isHov = hovered === idx;
                return (
                  <div key={entry.hour} style={{ position: 'relative' }}>
                    <motion.div
                      className="relative aspect-square rounded-lg cursor-default select-none"
                      style={{
                        backgroundColor: bg,
                        boxShadow: isHov ? glow : SHADOW_NONE,
                      }}
                      initial={{ opacity: 0, scale: 0.7 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: idx * 0.018, duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                      onMouseEnter={() => setHovered(idx)}
                      onMouseLeave={() => setHovered(null)}
                      whileHover={{ scale: 1.12, zIndex: 10 }}
                    >
                      {/* Hour label */}
                      <div
                        className="absolute inset-0 flex flex-col items-center justify-center"
                        style={{ color: text }}
                      >
                        <span className="font-mono text-[10px] sm:text-[11px] font-bold leading-none">
                          {String(entry.hour).padStart(2, '0')}
                        </span>
                        {entry.avg_health !== null && (
                          <span className="font-mono text-[9px] sm:text-[10px] opacity-70 leading-none mt-0.5">
                            {entry.avg_health.toFixed(0)}
                          </span>
                        )}
                      </div>
                    </motion.div>

                    {/* Tooltip — rendered outside motion.div to avoid clip */}
                    <AnimatePresence>
                      {isHov && entry.avg_health !== null && (
                        <HoverTooltip entry={entry} bg={healthColor(entry.avg_health).bg} />
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </div>

            {/* Best / worst callout */}
            {(bestHour || worstHour) && (
              <div className="mt-4 grid grid-cols-2 gap-3">
                {bestHour && (
                  <div className="rounded-lg border border-[#00E5A0]/20 bg-[#00E5A0]/5 px-4 py-3">
                    <p className="text-[10px] text-[#8A95A5] mb-0.5">Best period</p>
                    <p className="font-mono text-sm font-bold text-[#00E5A0]">{formatHour(bestHour.hour)}</p>
                    <p className="font-mono text-xs text-[#E8ECF1]">{bestHour.avg_health!.toFixed(1)} avg</p>
                  </div>
                )}
                {worstHour && (
                  <div className="rounded-lg border border-[#EF4444]/20 bg-[#EF4444]/5 px-4 py-3">
                    <p className="text-[10px] text-[#8A95A5] mb-0.5">Worst period</p>
                    <p className="font-mono text-sm font-bold text-[#EF4444]">{formatHour(worstHour.hour)}</p>
                    <p className="font-mono text-xs text-[#E8ECF1]">{worstHour.avg_health!.toFixed(1)} avg</p>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </motion.div>
  );
};

export default AHUHeatmap;
