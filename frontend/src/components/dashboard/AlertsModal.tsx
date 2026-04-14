/**
 * AlertsModal
 * Centered overlay listing all AHUs in alert state.
 * Primary: uses alertAHUs list from siteSummaryData prop.
 * Fallback: fetches /api/site/alerts if prop is empty (backend pre-restart).
 */
import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import { fetchSiteAlerts } from '../../api/client';
import { deviceIdToDisplay } from '../../utils/deviceNames';
import type { AlertAHU } from '../../types';

interface AlertsModalProps {
  isOpen: boolean;
  onClose: () => void;
  ahus: AlertAHU[];
  /** Total alert count from KPI strip — used to trigger fallback fetch when ahus prop is empty */
  alertCount?: number;
}

function tierColor(tier: string) {
  return tier === 'Critical' ? '#ef4444' : '#f59e0b';
}

function tierBg(tier: string) {
  return tier === 'Critical' ? 'rgba(239,68,68,0.08)' : 'rgba(245,158,11,0.08)';
}

function healthBarColor(score: number) {
  if (score >= 60) return '#f59e0b';
  return '#ef4444';
}

function AHURow({
  ahu,
  index,
  onInspect,
}: {
  ahu: AlertAHU;
  index: number;
  onInspect: () => void;
}) {
  const display = deviceIdToDisplay(ahu.id);
  const [shortLabel, deptName] = display.split(' \u2014 ');
  const pct = Math.max(0, Math.min(100, ahu.healthScore));
  const accent = tierColor(ahu.tier);

  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.045, duration: 0.25 }}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '12px 20px',
        borderBottom: '1px solid #1a2638',
      }}
    >
      {/* Level badge */}
      <div
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          fontWeight: 700,
          color: '#556677',
          background: '#151f2e',
          border: '1px solid #243040',
          borderRadius: 5,
          padding: '3px 7px',
          minWidth: 36,
          textAlign: 'center',
          flexShrink: 0,
        }}
      >
        L{String(ahu.level).padStart(2, '0')}
      </div>

      {/* AHU info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            fontWeight: 600,
            color: '#C8D4E0',
            letterSpacing: '0.02em',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {shortLabel}
        </div>
        <div
          style={{
            fontSize: 10,
            color: '#445566',
            marginTop: 1,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {deptName ?? ahu.name} &middot; {ahu.id}
        </div>
      </div>

      {/* Health score + bar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 72 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 13,
              fontWeight: 700,
              color: healthBarColor(ahu.healthScore),
            }}
          >
            {ahu.healthScore.toFixed(1)}
          </span>
          <span
            style={{
              fontSize: 7,
              fontWeight: 700,
              letterSpacing: '0.08em',
              color: accent,
              background: tierBg(ahu.tier),
              border: `1px solid ${accent}30`,
              borderRadius: 3,
              padding: '2px 5px',
              textTransform: 'uppercase',
              flexShrink: 0,
            }}
          >
            {ahu.tier === 'Maintenance Soon' ? 'MAINT.' : 'CRIT.'}
          </span>
        </div>
        <div style={{ height: 3, background: '#1e2d42', borderRadius: 2, overflow: 'hidden' }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ delay: index * 0.045 + 0.15, duration: 0.4, ease: 'easeOut' }}
            style={{ height: '100%', background: healthBarColor(ahu.healthScore), borderRadius: 2 }}
          />
        </div>
      </div>

      {/* Inspect button */}
      <motion.button
        onClick={onInspect}
        whileHover={{ background: `${accent}18`, borderColor: `${accent}60` }}
        style={{
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: '0.07em',
          color: accent,
          background: `${accent}0C`,
          border: `1px solid ${accent}30`,
          borderRadius: 5,
          padding: '5px 10px',
          cursor: 'pointer',
          flexShrink: 0,
          whiteSpace: 'nowrap',
        }}
      >
        INSPECT →
      </motion.button>
    </motion.div>
  );
}

export default function AlertsModal({ isOpen, onClose, ahus, alertCount }: AlertsModalProps) {
  const { selectLevel, selectDevice, timeRange } = useAppStore();
  const [sortBy, setSortBy] = useState<'score' | 'level'>('score');
  const [fetchedAhus, setFetchedAhus] = useState<AlertAHU[]>([]);
  const [loading, setLoading] = useState(false);

  // Fallback: if summary didn't include alertAHUs (backend pre-restart),
  // fetch directly from /api/site/alerts
  useEffect(() => {
    if (!isOpen) return;
    if (ahus.length > 0) {
      setFetchedAhus([]);
      return;
    }
    // Only bother fetching if we know there are alerts to show
    if (!alertCount || alertCount === 0) return;

    setLoading(true);
    fetchSiteAlerts(timeRange as '24h' | '7d' | '30d' | 'all')
      .then((data) => setFetchedAhus(data.ahus))
      .catch(() => setFetchedAhus([]))
      .finally(() => setLoading(false));
  }, [isOpen, ahus.length, alertCount, timeRange]);

  // Use prop list if available, otherwise use fetched fallback
  const displayAhus = ahus.length > 0 ? ahus : fetchedAhus;

  const sorted = [...displayAhus].sort((a, b) =>
    sortBy === 'score' ? a.healthScore - b.healthScore : a.level - b.level
  );

  const criticalCount = displayAhus.filter((a) => a.tier === 'Critical').length;
  const maintCount = displayAhus.filter((a) => a.tier === 'Maintenance Soon').length;

  function handleInspect(ahu: AlertAHU) {
    selectLevel(ahu.level);
    selectDevice(ahu.id);
    onClose();
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop — also acts as centering flex container */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(5,9,15,0.72)',
              backdropFilter: 'blur(4px)',
              zIndex: 9998,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {/* Panel — stop propagation so clicks inside don't close */}
            <motion.div
              key="panel"
              initial={{ opacity: 0, y: 24, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 16, scale: 0.97 }}
              transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
              onClick={(e) => e.stopPropagation()}
              style={{
                width: 'min(580px, 92vw)',
                maxHeight: '80vh',
                background: '#0D1520',
                border: '1px solid rgba(239,68,68,0.18)',
                borderRadius: 14,
                boxShadow: '0 32px 80px rgba(0,0,0,0.7), 0 0 0 1px rgba(239,68,68,0.08) inset',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                position: 'relative',
              }}
            >
              {/* Ambient red glow at top */}
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: 80,
                  background: 'linear-gradient(to bottom, rgba(239,68,68,0.07), transparent)',
                  pointerEvents: 'none',
                }}
              />

              {/* Header */}
              <div
                style={{
                  padding: '18px 20px 14px',
                  borderBottom: '1px solid #1a2638',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 14,
                  position: 'relative',
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 8,
                    background: 'rgba(239,68,68,0.1)',
                    border: '1px solid rgba(239,68,68,0.25)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <span style={{ fontSize: 16 }}>⚠</span>
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span
                      style={{
                        fontSize: 13,
                        fontWeight: 700,
                        color: '#E8ECF1',
                        letterSpacing: '-0.01em',
                      }}
                    >
                      AHUs in Alert
                    </span>
                    {displayAhus.length > 0 && (
                      <div style={{ display: 'flex', gap: 5 }}>
                        {criticalCount > 0 && (
                          <span
                            style={{
                              fontSize: 9,
                              fontWeight: 700,
                              letterSpacing: '0.07em',
                              color: '#ef4444',
                              background: 'rgba(239,68,68,0.1)',
                              border: '1px solid rgba(239,68,68,0.25)',
                              borderRadius: 4,
                              padding: '2px 6px',
                            }}
                          >
                            {criticalCount} CRITICAL
                          </span>
                        )}
                        {maintCount > 0 && (
                          <span
                            style={{
                              fontSize: 9,
                              fontWeight: 700,
                              letterSpacing: '0.07em',
                              color: '#f59e0b',
                              background: 'rgba(245,158,11,0.1)',
                              border: '1px solid rgba(245,158,11,0.25)',
                              borderRadius: 4,
                              padding: '2px 6px',
                            }}
                          >
                            {maintCount} MAINT. SOON
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  <div style={{ fontSize: 10, color: '#445566', marginTop: 3 }}>
                    Requires attention · Click any unit to inspect
                  </div>
                </div>

                <button
                  onClick={onClose}
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: 6,
                    background: 'transparent',
                    border: '1px solid #243040',
                    color: '#556677',
                    fontSize: 14,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  ✕
                </button>
              </div>

              {/* Sort controls */}
              {displayAhus.length > 0 && (
                <div
                  style={{
                    padding: '8px 20px',
                    borderBottom: '1px solid #151f2e',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  <span
                    style={{
                      fontSize: 9,
                      color: '#445566',
                      fontWeight: 600,
                      letterSpacing: '0.06em',
                      textTransform: 'uppercase',
                    }}
                  >
                    Sort:
                  </span>
                  {(['score', 'level'] as const).map((opt) => (
                    <button
                      key={opt}
                      onClick={() => setSortBy(opt)}
                      style={{
                        fontSize: 9,
                        fontWeight: 600,
                        letterSpacing: '0.06em',
                        textTransform: 'uppercase',
                        color: sortBy === opt ? '#00E5A0' : '#445566',
                        background: sortBy === opt ? 'rgba(0,229,160,0.08)' : 'transparent',
                        border:
                          sortBy === opt
                            ? '1px solid rgba(0,229,160,0.2)'
                            : '1px solid transparent',
                        borderRadius: 4,
                        padding: '3px 8px',
                        cursor: 'pointer',
                      }}
                    >
                      {opt === 'score' ? 'Health ↑' : 'Level'}
                    </button>
                  ))}
                  <span
                    style={{
                      marginLeft: 'auto',
                      fontSize: 9,
                      color: '#2d4055',
                      fontFamily: "'JetBrains Mono', monospace",
                    }}
                  >
                    {displayAhus.length} unit{displayAhus.length !== 1 ? 's' : ''}
                  </span>
                </div>
              )}

              {/* List */}
              <div style={{ overflowY: 'auto', flex: 1 }}>
                {loading ? (
                  <div style={{ padding: '32px 24px', textAlign: 'center' }}>
                    <div
                      style={{
                        fontSize: 11,
                        color: '#445566',
                        fontFamily: "'JetBrains Mono', monospace",
                        animation: 'pulse 1.5s infinite',
                      }}
                    >
                      Loading alert data…
                    </div>
                  </div>
                ) : displayAhus.length === 0 ? (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.3 }}
                    style={{
                      padding: '48px 24px',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: 12,
                    }}
                  >
                    <div
                      style={{
                        width: 56,
                        height: 56,
                        borderRadius: '50%',
                        background: 'rgba(0,229,160,0.08)',
                        border: '1px solid rgba(0,229,160,0.2)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 24,
                      }}
                    >
                      ✓
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#00E5A0' }}>
                        All Clear
                      </div>
                      <div style={{ fontSize: 11, color: '#445566', marginTop: 4 }}>
                        No AHUs are currently in alert state
                      </div>
                    </div>
                  </motion.div>
                ) : (
                  sorted.map((ahu, i) => (
                    <AHURow key={ahu.id} ahu={ahu} index={i} onInspect={() => handleInspect(ahu)} />
                  ))
                )}
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
