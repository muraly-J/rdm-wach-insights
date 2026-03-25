import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import { apiFetch } from '../../api/client';

interface HourEntry {
  hour: number;
  avg_health: number | null;
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

function healthColor(score: number | null): { bg: string; text: string; glow: string } {
  if (score === null) return { bg: '#1A2230', text: '#3A4455', glow: SHADOW_NONE };
  if (score >= 80) return { bg: '#00E5A0', text: '#0B0F14', glow: '0 0 14px rgba(0,229,160,0.45)' };
  if (score >= 60) return { bg: '#F59E0B', text: '#0B0F14', glow: '0 0 14px rgba(245,158,11,0.45)' };
  if (score >= 40) return { bg: '#F97316', text: '#0B0F14', glow: '0 0 14px rgba(249,115,22,0.45)' };
  return { bg: '#EF4444', text: '#ffffff', glow: '0 0 14px rgba(239,68,68,0.45)' };
}

function healthLabel(score: number | null): string {
  if (score === null) return 'No data';
  if (score >= 80) return 'Healthy';
  if (score >= 60) return 'Moderate';
  if (score >= 40) return 'Poor';
  return 'Critical';
}

function formatHour(h: number): string {
  if (h === 0) return '12 AM';
  if (h === 12) return '12 PM';
  return h < 12 ? `${h} AM` : `${h - 12} PM`;
}

const ROWS = 4;
const COLS = 6;

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
      className="card p-0 overflow-hidden"
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
            { label: 'Healthy', color: '#00E5A0' },
            { label: 'Moderate', color: '#F59E0B' },
            { label: 'Poor', color: '#F97316' },
            { label: 'Critical', color: '#EF4444' },
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
            <div className="grid grid-cols-6 gap-2">
              {data.hours.map((entry, idx) => {
                const { bg, text, glow } = healthColor(entry.avg_health);
                const isHov = hovered === idx;
                return (
                  <motion.div
                    key={entry.hour}
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

                    {/* Tooltip */}
                    <AnimatePresence>
                      {isHov && (
                        <motion.div
                          className="absolute z-20 bottom-full left-1/2 -translate-x-1/2 mb-2 pointer-events-none"
                          initial={{ opacity: 0, y: 4 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: 4 }}
                          transition={{ duration: 0.15 }}
                        >
                          <div className="bg-[#0D1520] border border-[#1E2A3A] rounded-lg px-3 py-2 text-center whitespace-nowrap shadow-xl">
                            <div className="font-mono text-xs text-[#E8ECF1] font-bold">{formatHour(entry.hour)}</div>
                            {entry.avg_health !== null ? (
                              <>
                                <div className="font-mono text-sm font-bold" style={{ color: bg }}>
                                  {entry.avg_health.toFixed(1)}
                                </div>
                                <div className="text-[10px] text-[#8A95A5]">{healthLabel(entry.avg_health)}</div>
                              </>
                            ) : (
                              <div className="text-[10px] text-[#8A95A5]">No data</div>
                            )}
                          </div>
                          {/* Caret */}
                          <div className="w-0 h-0 mx-auto border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-[#1E2A3A]" />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })}
            </div>

            {/* Hour-of-day axis labels */}
            <div className="grid grid-cols-6 gap-2 mt-1.5">
              {[0, 4, 8, 12, 16, 20].map((h) => (
                <div key={h} className="text-center text-[9px] text-[#4A5568] font-mono">
                  {formatHour(h)}
                </div>
              ))}
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
