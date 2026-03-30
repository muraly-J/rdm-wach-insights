import React, { useCallback } from 'react';
import { motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';

function getHealthColor(health: number): string {
  if (health >= 80) return '#00E5A0';
  if (health >= 50) return '#FFB020';
  return '#FF4D6A';
}

function getHealthBg(health: number): string {
  if (health >= 80) return 'rgba(0,229,160,0.08)';
  if (health >= 50) return 'rgba(255,176,32,0.08)';
  return 'rgba(255,77,106,0.08)';
}

function getHealthGlow(health: number): string {
  if (health >= 80) return 'inset 0 1px 0 rgba(255,255,255,0.10), 0 0 20px rgba(0,229,160,0.13)';
  if (health >= 50) return 'inset 0 1px 0 rgba(255,255,255,0.10), 0 0 20px rgba(255,176,32,0.13)';
  return 'inset 0 1px 0 rgba(255,255,255,0.10), 0 0 20px rgba(255,77,106,0.13)';
}

export default function LevelHeatMap() {
  const data = useAppStore((s) => s.siteSummaryData);
  const selectLevel = useAppStore((s) => s.selectLevel);

  const handleTileClick = useCallback((level: number) => {
    selectLevel(level);
    document.getElementById('dashboard')?.scrollIntoView({ behavior: 'smooth' });
  }, [selectLevel]);

  if (!data) return null;

  return (
    <div style={{ marginBottom: '2rem' }}>
      <div
        style={{
          fontSize: '12px',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: '#8A95A5',
          marginBottom: '12px',
        }}
      >
        Level Health Map
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))',
          gap: '10px',
          marginBottom: '8px',
        }}
      >
        {data.levelTiles.map((tile, i) => {
          const color = getHealthColor(tile.avgHealth);
          const bg = getHealthBg(tile.avgHealth);

          return (
            <motion.button
              key={tile.level}
              onClick={() => handleTileClick(tile.level)}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: i * 0.04, ease: [0.22, 1, 0.36, 1] }}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.96 }}
              style={{
                background: bg,
                backdropFilter: 'blur(12px) saturate(150%)',
                WebkitBackdropFilter: 'blur(12px) saturate(150%)',
                border: `1px solid ${bg.replace('0.08', '0.20')}`,
                borderRadius: '12px',
                padding: '14px 8px',
                textAlign: 'center',
                cursor: 'pointer',
                outline: 'none',
                boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06)',
                transition: 'box-shadow 0.15s ease',
              }}
            >
              <div style={{ fontSize: '10px', color: '#8A95A5', marginBottom: '6px' }}>
                L{tile.level}
              </div>
              <div
                style={{
                  fontSize: '22px',
                  fontWeight: 700,
                  color,
                  fontFamily: 'var(--font-display)',
                  lineHeight: 1.1,
                }}
              >
                {tile.avgHealth}
              </div>
              <div style={{ fontSize: '10px', color: '#8A95A5', marginTop: '6px' }}>
                {tile.ahuCount} AHUs
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginTop: '12px' }}>
        {[
          { color: '#00E5A0', label: '≥ 80 Healthy' },
          { color: '#FFB020', label: '50–79 Monitor' },
          { color: '#FF4D6A', label: '< 50 Critical' },
        ].map(({ color, label }) => (
          <div
            key={label}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#8A95A5' }}
          >
            <span style={{ color, fontSize: '10px' }}>●</span>
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}
