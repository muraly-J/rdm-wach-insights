import { motion, AnimatePresence } from 'framer-motion';
import { useMemo } from 'react';

// ─────────────────────────────────────────────────────────────────────────────
// HealthGauge Component
// SVG Donut chart for Health Index with dynamic colors and glow effects
//
// Props:
//   - value: Health index (0-100)
//   - size: Optional diameter in pixels
// ─────────────────────────────────────────────────────────────────────────────

const HealthGauge = ({ value = 85, size = 320 }) => {
  const radius = 120;
  const circumference = 2 * Math.PI * radius;
  const progress = useMemo(() => {
    return Math.min(Math.max(value, 0), 100);
  }, [value]);

  const dashOffset = useMemo(() => {
    return circumference - (progress / 100) * circumference;
  }, [circumference, progress]);

  // Dynamic color based on health index
  const getColor = () => {
    if (value >= 80) {
      return '#10b981'; // Emerald
    }
    if (value >= 60) {
      return '#f59e0b'; // Gold
    }
    if (value >= 40) {
      return '#f97316'; // Orange
    }
    return '#ef4444'; // Red
  };

  const getGlowColor = () => {
    if (value >= 80) return 'rgba(16, 185, 129, 0.4)';
    if (value >= 60) return 'rgba(245, 158, 11, 0.3)';
    if (value >= 40) return 'rgba(249, 115, 22, 0.3)';
    return 'rgba(239, 68, 68, 0.4)';
  };

  const getTierLabel = () => {
    if (value >= 80) return 'Healthy';
    if (value >= 60) return 'Monitor';
    if (value >= 40) return 'Maintenance Soon';
    return 'Critical';
  };

  const color = getColor();
  const glowColor = getGlowColor();

  // Animated circle components
  const gaugeCircle = (
    <motion.circle
      cx="160"
      cy="160"
      r={radius}
      fill="none"
      stroke={color}
      strokeWidth="16"
      strokeLinecap="round"
      initial={{ strokeDasharray: `${circumference} ${circumference}`, strokeDashoffset: circumference }}
      animate={{ strokeDasharray: `${circumference} ${circumference}`, strokeDashoffset: dashOffset }}
      transition={{
        type: 'spring',
        damping: 20,
        stiffness: 100,
        mass: 1,
      }}
    />
  );

  const gaugeBackground = (
    <circle
      cx="160"
      cy="160"
      r={radius}
      fill="none"
      stroke="#2A3040"
      strokeWidth="16"
    />
  );

  const gaugeOverlay = (
    <motion.circle
      cx="160"
      cy="160"
      r={radius}
      fill="none"
      stroke="#ffffff"
      strokeWidth="1"
      opacity="0.1"
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      transition={{ delay: 0.8, type: 'spring' }}
    />
  );

  return (
    <div
      className="health-gauge-container"
      style={{
        width: size,
        height: size,
        position: 'relative',
      }}
    >
      {/* Outer Glow Ring */}
      <motion.div
        style={{
          position: 'absolute',
          top: -20,
          left: -20,
          width: size + 40,
          height: size + 40,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${glowColor}, transparent 70%)`,
        }}
        animate={{ opacity: [0.3, 0.5, 0.3] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
      />

      <svg
        className="health-gauge-svg"
        viewBox="0 0 320 320"
        style={{
          width: '100%',
          height: '100%',
        }}
      >
        {/* Background Ring */}
        {gaugeBackground}

        {/* Animated Gauge Ring */}
        <AnimatePresence mode="wait">
          <motion.g key={color}>
            {gaugeCircle}
          </motion.g>
        </AnimatePresence>

        {/* decorative overlay */}
        {gaugeOverlay}
      </svg>

      {/* Center Content */}
      <div className="health-index-value">
        <motion.div
          style={{
            position: 'relative',
            display: 'inline-block',
          }}
        >
          {/* Main Number */}
          <motion.div
            className="health-index-number"
            style={{
              color: color,
              textShadow: `0 0 30px ${glowColor}`,
            }}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', damping: 15, stiffness: 80 }}
          >
            {Math.round(value)}
          </motion.div>

          {/* Tier Label */}
          <motion.div
            className="health-index-label"
            style={{
              color: '#a3aab5',
              textShadow: '0 0 10px rgba(255,255,255,0.1)',
            }}
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.3, type: 'spring' }}
          >
            {getTierLabel()}
          </motion.div>
        </motion.div>
      </div>

      {/* Progress Ring (optional, to show completion) */}
      <motion.div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          pointerEvents: 'none',
        }}
      >
        {[...Array(24)].map((_, i) => {
          const angle = (i / 24) * 360;
          const isActive = (progress / 100) * 24 > i;

          return (
            <motion.div
              key={i}
              style={{
                position: 'absolute',
                top: 0,
                left: '50%',
                width: '2px',
                height: '16px',
                marginLeft: '-1px',
                transformOrigin: '50% 142px',
                background: isActive ? color : '#2A3040',
              }}
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{
                duration: isActive ? 3 : 1,
                repeat: Infinity,
                delay: (i / 24) * 3,
              }}
            />
          );
        })}
      </motion.div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// HealthGaugeRing Component
// Small ring for card headers or compact displays
// ─────────────────────────────────────────────────────────────────────────────

export const HealthGaugeRing = ({ value = 85, size = 40 }) => {
  const radius = 16;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(Math.max(value, 0), 100);
  const dashOffset = circumference - (progress / 100) * circumference;

  const getColor = () => {
    if (value >= 80) return '#10b981';
    if (value >= 60) return '#f59e0b';
    if (value >= 40) return '#f97316';
    return '#ef4444';
  };

  const color = getColor();

  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size * 2} ${size * 2}`}>
        <circle
          cx={size}
          cy={size}
          r={radius}
          fill="none"
          stroke="#2A3040"
          strokeWidth="3"
        />
        <motion.circle
          cx={size}
          cy={size}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
          initial={{ strokeDasharray: `${circumference} ${circumference}`, strokeDashoffset: circumference }}
          animate={{ strokeDasharray: `${circumference} ${circumference}`, strokeDashoffset: dashOffset }}
          transition={{ duration: 1, type: 'spring' }}
        />
      </svg>
    </div>
  );
};

export default HealthGauge;
