import { motion } from 'framer-motion';
import HealthGauge, { HealthGaugeRing } from './HealthGauge';

// ─────────────────────────────────────────────────────────────────────────────
// BentoCards Component
// Strategic Overview with Health Index in center and summary cards on sides
//
// Props:
//   - healthIndex: Current health index value (0-100)
//   - tier: Health tier label ('Healthy', 'Monitor', etc.)
//   - summaryText: AI-generated health summary
//   - latestInsight: Most recent data insight
// ─────────────────────────────────────────────────────────────────────────────

const BentoCards = ({
  healthIndex = 85,
  tier = 'Healthy',
  summaryText = '',
  latestInsight = '',
}) => {
  // Get tier colors
  const getTierColors = () => {
    switch (tier) {
      case 'Healthy':
        return { accent: '#10b981', label: 'HEALTHY' };
      case 'Monitor':
        return { accent: '#f59e0b', label: 'MONITOR' };
      case 'Maintenance Soon':
        return { accent: '#f97316', label: 'MAINTENANCE' };
      default:
        return { accent: '#ef4444', label: 'CRITICAL' };
    }
  };

  const { accent, label } = getTierColors();

  // Animation variants
  const cardVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: (i) => ({
      opacity: 1,
      y: 0,
      transition: {
        type: 'spring',
        damping: 15,
        stiffness: 80,
        delay: i * 0.15,
      },
    }),
  };

  return (
    <div className="strategic-overview">
      {/* Health Gauge - Center Piece */}
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', damping: 20, stiffness: 100 }}
      >
        <HealthGauge value={healthIndex} size={360} />
      </motion.div>

      {/* Bento Cards - Left & Right */}
      <div className="bento-grid">
        {/* Left Card: Health Summary */}
        <motion.div
          className="bento-card left"
          variants={cardVariants}
          initial="hidden"
          animate="visible"
          custom={0}
        >
          <div className="bento-title">HEALTH SUMMARY</div>
          <div
            className="bento-content"
            style={{
              color: '#eaf0fb',
              fontSize: '1.5rem',
            }}
          >
            {summaryText || 'System operating within normal parameters.'}
          </div>
          <div className="bento-subtext">
            {latestInsight
              ? `Latest: ${latestInsight}`
              : 'Data updated within the last hour.'}
          </div>
        </motion.div>

        {/* Right Card: Latest Insight */}
        <motion.div
          className="bento-card right"
          variants={cardVariants}
          initial="hidden"
          animate="visible"
          custom={1}
        >
          <div className="bento-title">
            LATEST INSIGHT
            <span style={{ float: 'right', color: accent }}>
              <HealthGaugeRing value={healthIndex} size={32} />
            </span>
          </div>
          <div
            className="bento-content"
            style={{
              color: '#eaf0fb',
              fontSize: '1.25rem',
            }}
          >
            {latestInsight || (
              <span style={{ opacity: 0.7 }}>
                Waiting for new data points...
              </span>
            )}
          </div>
        </motion.div>
      </div>

      {/* Decorative Element - Dynamic Gradient Border */}
      <motion.div
        style={{
          marginTop: '40px',
          height: '2px',
          width: '100%',
          maxWidth: 960,
          margin: '40px auto',
          background: `linear-gradient(90deg, transparent, ${accent}, transparent)`,
          opacity: 0.4,
        }}
        animate={{ opacity: [0.3, 0.5, 0.3] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
      />
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// BentoCard Component - Reusable card for metrics section
// ─────────────────────────────────────────────────────────────────────────────

export const BentoCard = ({
  title,
  value,
  description,
  accentColor = '#10b981',
  icon,
  onClick,
}) => {
  return (
    <motion.div
      className="bento-card"
      onClick={onClick}
      style={{
        cursor: onClick ? 'pointer' : 'default',
        borderLeft: `3px solid ${accentColor}`,
      }}
      whileHover={{ scale: 1.02, transition: { duration: 0.2 } }}
    >
      <div className="bento-title">{title}</div>
      <div
        className="bento-content"
        style={{
          fontSize: '2rem',
          fontWeight: 700,
          marginBottom: '12px',
        }}
      >
        {value}
      </div>
      <div className="bento-subtext">{description}</div>
    </motion.div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Mini Bento Card - Compact version for lists
// ─────────────────────────────────────────────────────────────────────────────

export const MiniBentoCard = ({
  title,
  value,
  subtext,
  accentColor = '#10b981',
}) => {
  return (
    <div
      style={{
        background: 'rgba(31, 35, 46, 0.7)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(42, 48, 64, 0.3)',
        borderLeft: `3px solid ${accentColor}`,
        borderRadius: '16px',
        padding: '20px 24px',
      }}
    >
      <div
        style={{
          fontSize: '0.75rem',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: '#a3aab5',
          marginBottom: '8px',
        }}
      >
        {title}
      </div>
      <div
        style={{
          fontSize: '1.5rem',
          fontWeight: 700,
          color: '#eaf0fb',
          marginBottom: '4px',
        }}
      >
        {value}
      </div>
      <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>{subtext}</div>
    </div>
  );
};

export default BentoCards;
