import { motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import { SpotlightAHU } from '../../types';

interface CardProps {
  ahu: SpotlightAHU;
  type: 'star' | 'critical';
  index: number;
}

function SpotlightCard({ ahu, type, index }: CardProps) {
  const isStar = type === 'star';
  const accentColor = isStar ? '#00E5A0' : '#FF4D6A';
  const icon = isStar ? '★' : '⚠';
  const title = isStar ? 'Star AHU' : 'Most Critical AHU';
  const subtitle = isStar
    ? 'Most efficient · Lowest cost'
    : 'Lowest health · Highest risk';

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: 0.1 + index * 0.08, ease: [0.22, 1, 0.36, 1] }}
      style={{
        flex: '1 1 280px',
        background: 'rgba(255,255,255,0.04)',
        backdropFilter: 'blur(24px) saturate(180%)',
        WebkitBackdropFilter: 'blur(24px) saturate(180%)',
        border: `1px solid ${accentColor}22`,
        borderRadius: '16px',
        padding: '20px 24px',
        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.07), 0 8px 32px rgba(0,0,0,0.24)',
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
        <span style={{ fontSize: '20px', color: accentColor, lineHeight: 1 }}>{icon}</span>
        <div>
          <div
            style={{
              fontSize: '12px',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: accentColor,
            }}
          >
            {title}
          </div>
          <div style={{ fontSize: '11px', color: '#8A95A5', marginTop: '1px' }}>{subtitle}</div>
        </div>
      </div>

      {/* AHU name + level */}
      <div style={{ marginBottom: '16px' }}>
        <div
          style={{
            fontSize: '22px',
            fontWeight: 700,
            color: '#E8ECF1',
            fontFamily: 'var(--font-display)',
            lineHeight: 1.2,
          }}
        >
          {ahu.name}
        </div>
        <div style={{ fontSize: '12px', color: '#8A95A5', marginTop: '3px' }}>
          Level {ahu.level}
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '11px', color: '#8A95A5', marginBottom: '3px' }}>
            Health Score
          </div>
          <div
            style={{
              fontSize: '20px',
              fontWeight: 700,
              color: accentColor,
              fontFamily: 'var(--font-display)',
            }}
          >
            {ahu.healthScore}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '11px', color: '#8A95A5', marginBottom: '3px' }}>
            Monthly Cost
          </div>
          <div
            style={{
              fontSize: '20px',
              fontWeight: 700,
              color: '#E8ECF1',
              fontFamily: 'var(--font-display)',
            }}
          >
            RM {ahu.monthlyCostMYR.toLocaleString()}
          </div>
        </div>

        {ahu.safetyFlags > 0 && (
          <div>
            <div style={{ fontSize: '11px', color: '#8A95A5', marginBottom: '3px' }}>
              Safety Flags
            </div>
            <div
              style={{
                fontSize: '20px',
                fontWeight: 700,
                color: '#FFB020',
                fontFamily: 'var(--font-display)',
              }}
            >
              {ahu.safetyFlags}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default function SpotlightCards() {
  const data = useAppStore((s) => s.siteSummaryData);
  if (!data) return null;

  return (
    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '2rem' }}>
      <SpotlightCard ahu={data.starAHU} type="star" index={0} />
      <SpotlightCard ahu={data.criticalAHU} type="critical" index={1} />
    </div>
  );
}
