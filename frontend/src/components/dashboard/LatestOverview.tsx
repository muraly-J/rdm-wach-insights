/**
 * LatestOverview
 * Shown when no level is selected. Displays:
 *   1. Level Health — avg health score per level (11 rows)
 *   2. Fleet Directory — AHU count + expandable ID list per level
 *   3. Alert Status — ahusInAlert count, critical/star spotlights
 */
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import { deviceIdToDisplay } from '../../utils/deviceNames';

// Static AHU IDs per level (mirrors backend/models/schemas.py AHU_LEVEL_CONFIG)
const LEVEL_AHU_IDS: Record<number, string[]> = {
  1: [
    'e0101',
    'e0102',
    'e0103',
    'e0104',
    'e0105',
    'e0106',
    'e0107',
    'e0108',
    'e0109',
    'e0110',
    'e0111',
    'e0112',
    'e0113',
    'e0114',
    'e0115',
    'e0116',
    'e0117',
    'e0118',
    'e0120',
    'e0121',
    'e0212',
  ],
  2: [
    'e0201',
    'e0202',
    'e0203',
    'e0204',
    'e0205',
    'e0206',
    'e0207',
    'e0208',
    'e0209',
    'e0213',
    'e0214',
    'e0215',
    'e0216',
    'e0217',
    'e0218',
  ],
  3: [
    'e0210',
    'e0211',
    'e0301',
    'e0303',
    'e0304',
    'e0306',
    'e0307',
    'e0308',
    'e0311',
    'e0312',
    'e0313',
    'e0314',
    'e0315',
    'e0401',
    'e0402',
    'e0423',
  ],
  4: [
    'e0403',
    'e0404',
    'e0406',
    'e0407',
    'e0408',
    'e0409',
    'e0411',
    'e0412',
    'e0413',
    'e0414',
    'e0415',
    'e0416',
    'e0419',
  ],
  5: [
    'e0501',
    'e0502',
    'e0503',
    'e0504',
    'e0505',
    'e0506',
    'e0507',
    'e0508',
    'e0509',
    'e0510',
    'e0511',
    'e0622',
  ],
  6: [
    'e0602',
    'e0603',
    'e0604',
    'e0605',
    'e0606',
    'e0607',
    'e0611',
    'e0625',
    'e0626',
    'e0627',
    'e0628',
  ],
  7: ['e0701', 'e0702', 'e0703', 'e0704'],
  8: ['e0801', 'e0802', 'e0803', 'e0804', 'e0805'],
  9: ['e0901', 'e0902', 'e0903', 'e0904', 'e0905', 'e0906', 'e0907', 'e0908'],
  10: ['e1001', 'e1002', 'e1003', 'e1004', 'e1005', 'e1006', 'e1007', 'e1008'],
  11: ['e1101', 'e1102', 'e1103', 'e1104', 'e1105', 'e1106', 'e1107', 'e1108'],
};

function healthColor(score: number) {
  if (score >= 80) return '#00E5A0';
  if (score >= 60) return '#f59e0b';
  return '#ef4444';
}

function healthBg(score: number) {
  if (score >= 80) return 'rgba(0,229,160,0.08)';
  if (score >= 60) return 'rgba(245,158,11,0.08)';
  return 'rgba(239,68,68,0.08)';
}

function healthLabel(score: number) {
  if (score >= 80) return 'GOOD';
  if (score >= 60) return 'WARN';
  return 'CRIT';
}

// ── Panel 1: Level Health ──────────────────────────────────────────────────

function LevelHealthPanel() {
  const { siteSummaryData, selectLevel } = useAppStore();
  const tiles = siteSummaryData?.levelTiles ?? [];

  return (
    <div
      style={{
        background: '#131c2b',
        border: '1px solid #1e2d42',
        borderRadius: 12,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div style={{ padding: '14px 18px 10px', borderBottom: '1px solid #1e2d42' }}>
        <div
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: '0.12em',
            color: '#00E5A0',
            textTransform: 'uppercase',
          }}
        >
          Level Health
        </div>
        <div style={{ fontSize: 11, color: '#445566', marginTop: 2 }}>
          Latest Average Per Floor · Click To Open
        </div>
      </div>

      {/* Rows */}
      <div>
        {tiles.length === 0
          ? Array.from({ length: 11 }, (_, i) => <SkeletonLevelRow key={i} />)
          : tiles.map((tile, i) => {
              const color = healthColor(tile.avgHealth);
              const pct = Math.max(0, Math.min(100, tile.avgHealth));
              return (
                <motion.button
                  key={tile.level}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04, duration: 0.25 }}
                  onClick={() => selectLevel(tile.level)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    width: '100%',
                    padding: '10px 18px',
                    background: 'transparent',
                    border: 'none',
                    borderBottom: i < tiles.length - 1 ? '1px solid #1a2638' : 'none',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                  whileHover={{ background: healthBg(tile.avgHealth) }}
                >
                  {/* Level label */}
                  <span
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11,
                      color: '#556677',
                      minWidth: 28,
                    }}
                  >
                    L{String(tile.level).padStart(2, '0')}
                  </span>

                  {/* Bar */}
                  <div
                    style={{
                      flex: 1,
                      height: 5,
                      background: '#1e2d42',
                      borderRadius: 3,
                      overflow: 'hidden',
                    }}
                  >
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ delay: i * 0.04 + 0.1, duration: 0.5, ease: 'easeOut' }}
                      style={{ height: '100%', background: color, borderRadius: 3 }}
                    />
                  </div>

                  {/* Score */}
                  <span
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 12,
                      color: color,
                      minWidth: 42,
                      textAlign: 'right',
                      fontWeight: 600,
                    }}
                  >
                    {tile.avgHealth.toFixed(1)}
                  </span>

                  {/* Status badge */}
                  <span
                    style={{
                      fontSize: 8,
                      fontWeight: 700,
                      letterSpacing: '0.08em',
                      color: color,
                      background: healthBg(tile.avgHealth),
                      border: `1px solid ${color}30`,
                      borderRadius: 4,
                      padding: '2px 5px',
                      minWidth: 30,
                      textAlign: 'center',
                    }}
                  >
                    {healthLabel(tile.avgHealth)}
                  </span>
                </motion.button>
              );
            })}
      </div>
    </div>
  );
}

function SkeletonLevelRow() {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '10px 18px',
        borderBottom: '1px solid #1a2638',
      }}
    >
      <div
        style={{
          width: 28,
          height: 10,
          background: '#1e2d42',
          borderRadius: 3,
          animation: 'pulse 1.5s infinite',
        }}
      />
      <div
        style={{
          flex: 1,
          height: 5,
          background: '#1e2d42',
          borderRadius: 3,
          animation: 'pulse 1.5s infinite',
        }}
      />
      <div
        style={{
          width: 42,
          height: 10,
          background: '#1e2d42',
          borderRadius: 3,
          animation: 'pulse 1.5s infinite',
        }}
      />
      <div
        style={{
          width: 30,
          height: 14,
          background: '#1e2d42',
          borderRadius: 4,
          animation: 'pulse 1.5s infinite',
        }}
      />
    </div>
  );
}

// ── Panel 2: Fleet Directory ───────────────────────────────────────────────

function FleetDirectoryPanel() {
  const { siteSummaryData, selectLevel, selectDevice } = useAppStore();
  const [expanded, setExpanded] = useState<number | null>(null);

  const tiles = siteSummaryData?.levelTiles ?? [];

  // Build a count map from live data; fall back to static lengths
  const countMap: Record<number, number> = {};
  tiles.forEach((t) => {
    countMap[t.level] = t.ahuCount;
  });

  const levels = Array.from({ length: 11 }, (_, i) => i + 1);

  return (
    <div
      style={{
        background: '#131c2b',
        border: '1px solid #1e2d42',
        borderRadius: 12,
        overflow: 'hidden',
      }}
    >
      <div style={{ padding: '14px 18px 10px', borderBottom: '1px solid #1e2d42' }}>
        <div
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: '0.12em',
            color: '#00E5A0',
            textTransform: 'uppercase',
          }}
        >
          Fleet Directory
        </div>
        <div style={{ fontSize: 11, color: '#445566', marginTop: 2 }}>
          AHU Count + Device IDs Per Level
        </div>
      </div>

      <div>
        {levels.map((level, i) => {
          const ids = LEVEL_AHU_IDS[level] ?? [];
          const count = countMap[level] ?? ids.length;
          const isOpen = expanded === level;

          return (
            <motion.div
              key={level}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.03 }}
              style={{ borderBottom: i < levels.length - 1 ? '1px solid #1a2638' : 'none' }}
            >
              {/* Row header */}
              <button
                onClick={() => setExpanded(isOpen ? null : level)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  width: '100%',
                  padding: '10px 18px',
                  background: isOpen ? 'rgba(0,229,160,0.05)' : 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                <span
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                    color: '#556677',
                    minWidth: 28,
                  }}
                >
                  L{String(level).padStart(2, '0')}
                </span>

                <span style={{ flex: 1, fontSize: 11, color: '#8899aa' }}>
                  <span
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      color: '#E8ECF1',
                      fontWeight: 600,
                    }}
                  >
                    {count}
                  </span>{' '}
                  AHUs
                </span>

                {/* Chevron */}
                <motion.span
                  animate={{ rotate: isOpen ? 180 : 0 }}
                  transition={{ duration: 0.2 }}
                  style={{ color: isOpen ? '#00E5A0' : '#334455', fontSize: 12, lineHeight: 1 }}
                >
                  ▾
                </motion.span>

                {/* Navigate to level */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    selectLevel(level);
                  }}
                  style={{
                    fontSize: 9,
                    fontWeight: 600,
                    letterSpacing: '0.06em',
                    color: '#00E5A0',
                    background: 'rgba(0,229,160,0.08)',
                    border: '1px solid rgba(0,229,160,0.2)',
                    borderRadius: 4,
                    padding: '2px 7px',
                    cursor: 'pointer',
                  }}
                >
                  VIEW →
                </button>
              </button>

              {/* Expanded AHU IDs */}
              <AnimatePresence>
                {isOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.22, ease: 'easeInOut' }}
                    style={{ overflow: 'hidden' }}
                  >
                    <div
                      style={{
                        padding: '6px 18px 12px',
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: 5,
                      }}
                    >
                      {ids.map((id) => {
                        const display = deviceIdToDisplay(id);
                        const shortName = display.split(' \u2014 ')[0];
                        return (
                          <motion.button
                            key={id}
                            onClick={() => {
                              selectLevel(level);
                              selectDevice(id);
                            }}
                            whileHover={{
                              borderColor: 'rgba(0,229,160,0.5)',
                              background: '#1e3048',
                            }}
                            style={{
                              fontFamily: "'JetBrains Mono', monospace",
                              background: '#1a2638',
                              border: '1px solid #243040',
                              borderRadius: 5,
                              padding: '4px 8px',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: 1,
                              cursor: 'pointer',
                              textAlign: 'left',
                            }}
                          >
                            <span
                              style={{
                                fontSize: 10,
                                color: '#C8D4E0',
                                fontWeight: 600,
                                letterSpacing: '0.02em',
                              }}
                            >
                              {shortName}
                            </span>
                            <span
                              style={{ fontSize: 9, color: '#445566', letterSpacing: '0.03em' }}
                            >
                              {id}
                            </span>
                          </motion.button>
                        );
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

// ── Panel 3: Alert Status ──────────────────────────────────────────────────

function AlertStatusPanel() {
  const { siteSummaryData, selectLevel, selectDevice } = useAppStore();

  if (!siteSummaryData) {
    return (
      <div
        style={{
          background: '#131c2b',
          border: '1px solid #1e2d42',
          borderRadius: 12,
          padding: '18px',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        <div
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: '0.12em',
            color: '#00E5A0',
            textTransform: 'uppercase',
          }}
        >
          Alert Status
        </div>
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            style={{
              height: 60,
              background: '#1e2d42',
              borderRadius: 8,
              animation: 'pulse 1.5s infinite',
            }}
          />
        ))}
      </div>
    );
  }

  const { ahusInAlert, criticalAHU, starAHU, totalAHUs, avgSiteHealth } = siteSummaryData;
  const alertColor = ahusInAlert === 0 ? '#00E5A0' : ahusInAlert < 5 ? '#f59e0b' : '#ef4444';

  return (
    <div
      style={{
        background: '#131c2b',
        border: '1px solid #1e2d42',
        borderRadius: 12,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div style={{ padding: '14px 18px 10px', borderBottom: '1px solid #1e2d42' }}>
        <div
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: '0.12em',
            color: '#00E5A0',
            textTransform: 'uppercase',
          }}
        >
          Alert Status
        </div>
        <div style={{ fontSize: 11, color: '#445566', marginTop: 2 }}>
          Maintenance Soon + Critical Tier
        </div>
      </div>

      <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* Alert count hero */}
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.3 }}
          style={{
            background: ahusInAlert > 0 ? 'rgba(239,68,68,0.06)' : 'rgba(0,229,160,0.06)',
            border: `1px solid ${ahusInAlert > 0 ? 'rgba(239,68,68,0.2)' : 'rgba(0,229,160,0.2)'}`,
            borderRadius: 10,
            padding: '14px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: 14,
          }}
        >
          <span
            style={{
              fontSize: 36,
              fontWeight: 800,
              color: alertColor,
              fontFamily: "'JetBrains Mono', monospace",
              lineHeight: 1,
            }}
          >
            {ahusInAlert}
          </span>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#E8ECF1' }}>AHUs in Alert</div>
            <div style={{ fontSize: 10, color: '#556677', marginTop: 2 }}>
              Out of {totalAHUs} Total Monitored Units
            </div>
          </div>
        </motion.div>

        {/* Site-wide stat pills */}
        <div style={{ display: 'flex', gap: 8 }}>
          <StatPill
            label="Site Health"
            value={`${avgSiteHealth.toFixed(1)}`}
            unit="pts"
            color={healthColor(avgSiteHealth)}
          />
          <StatPill label="Total AHUs" value={`${totalAHUs}`} unit="" color="#8899aa" />
        </div>

        {/* Critical AHU */}
        {criticalAHU?.id && (
          <SpotlightCard
            label="Most Critical"
            id={criticalAHU.id}
            name={criticalAHU.name}
            level={criticalAHU.level}
            score={criticalAHU.healthScore}
            accent="#ef4444"
            onViewDevice={() => {
              selectLevel(criticalAHU.level);
              selectDevice(criticalAHU.id);
            }}
          />
        )}

        {/* Star AHU */}
        {starAHU?.id && (
          <SpotlightCard
            label="Best Performing"
            id={starAHU.id}
            name={starAHU.name}
            level={starAHU.level}
            score={starAHU.healthScore}
            accent="#00E5A0"
            onViewDevice={() => {
              selectLevel(starAHU.level);
              selectDevice(starAHU.id);
            }}
          />
        )}
      </div>
    </div>
  );
}

function StatPill({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value: string;
  unit: string;
  color: string;
}) {
  return (
    <div
      style={{
        flex: 1,
        background: '#1a2638',
        border: '1px solid #243040',
        borderRadius: 8,
        padding: '8px 12px',
      }}
    >
      <div
        style={{
          fontSize: 9,
          color: '#445566',
          fontWeight: 600,
          letterSpacing: '0.07em',
          textTransform: 'uppercase',
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 16, fontWeight: 700, color }}
      >
        {value}
        <span style={{ fontSize: 10, color: '#445566', marginLeft: 2 }}>{unit}</span>
      </div>
    </div>
  );
}

function SpotlightCard({
  label,
  id,
  name,
  level,
  score,
  accent,
  onViewDevice,
}: {
  label: string;
  id: string;
  name: string;
  level: number;
  score: number;
  accent: string;
  onViewDevice: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        background: `${accent}08`,
        border: `1px solid ${accent}25`,
        borderRadius: 10,
        padding: '12px 14px',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}
    >
      {/* Score ring */}
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: '50%',
          border: `2px solid ${accent}40`,
          background: `${accent}10`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            fontWeight: 700,
            color: accent,
          }}
        >
          {score.toFixed(0)}
        </span>
      </div>

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 8,
            fontWeight: 700,
            letterSpacing: '0.1em',
            color: accent,
            textTransform: 'uppercase',
            marginBottom: 2,
          }}
        >
          {label}
        </div>
        <div
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: '#E8ECF1',
            fontWeight: 600,
          }}
        >
          {id}
        </div>
        <div style={{ fontSize: 10, color: '#556677', marginTop: 1 }}>
          {name} · L{String(level).padStart(2, '0')}
        </div>
      </div>

      {/* View device button */}
      <button
        onClick={onViewDevice}
        style={{
          fontSize: 8,
          fontWeight: 700,
          letterSpacing: '0.06em',
          color: accent,
          background: `${accent}10`,
          border: `1px solid ${accent}30`,
          borderRadius: 5,
          padding: '4px 8px',
          cursor: 'pointer',
          flexShrink: 0,
        }}
      >
        VIEW →
      </button>
    </motion.div>
  );
}

// ── Root export ────────────────────────────────────────────────────────────

export default function LatestOverview() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.35 }}
    >
      {/* Section title */}
      <div style={{ marginBottom: 20, display: 'flex', alignItems: 'baseline', gap: 12 }}>
        <h2
          style={{
            margin: 0,
            fontSize: 15,
            fontWeight: 700,
            color: '#E8ECF1',
            letterSpacing: '-0.01em',
          }}
        >
          Building Overview
        </h2>
        <span style={{ fontSize: 11, color: '#445566' }}>Select a Level Below to Drill In</span>
      </div>

      {/* Three-column grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 16,
          alignItems: 'start',
        }}
        className="overview-grid"
      >
        <LevelHealthPanel />
        <FleetDirectoryPanel />
        <AlertStatusPanel />
      </div>

      <style>{`
        @media (max-width: 900px) {
          .overview-grid { grid-template-columns: 1fr 1fr !important; }
        }
        @media (max-width: 600px) {
          .overview-grid { grid-template-columns: 1fr !important; }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </motion.div>
  );
}
