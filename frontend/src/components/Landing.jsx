import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

// ─────────────────────────────────────────────────────────────────────────────
// Landing Page - Golden Thread Design
// The Health Index appears as a subtle background watermark before "Enter"
// ─────────────────────────────────────────────────────────────────────────────

const Landing = ({ onEnter, currentHealthIndex = 85 }) => {
  const [showCTA, setShowCTA] = useState(false);

  useEffect(() => {
    // Staggered reveal animation
    const timer1 = setTimeout(() => setShowCTA(true), 2500);
    return () => clearTimeout(timer1);
  }, []);

  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
        delayChildren: 0.3,
      },
    },
  };

  const titleVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { type: 'spring', damping: 12, stiffness: 100 },
    },
  };

  const subtitleVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { delay: 0.5, duration: 0.8 },
    },
  };

  const ctaVariants = {
    hidden: { opacity: 0, scale: 0.95 },
    visible: {
      opacity: 1,
      scale: 1,
      transition: { type: 'spring', damping: 10, stiffness: 200 },
    },
    hover: {
      scale: 1.03,
      transition: { duration: 0.2 },
    },
    tap: {
      scale: 0.98,
    },
  };

  return (
    <div className="landing-page">
      {/* Mesh Gradient Background */}
      <div className="landing-gradient" />

      {/* Golden Thread: Health Index as subtle background watermark */}
      <motion.div
        className="landing-watermark"
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '120%',
          height: '120%',
          pointerEvents: 'none',
          zIndex: 1,
        }}
        initial={{ opacity: 0.15, scale: 1.2 }}
        animate={{ opacity: 0.25, scale: 1 }}
        transition={{ duration: 1.5 }}
      >
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
          }}
        >
          <div
            style={{
              fontSize: '12rem',
              fontWeight: 800,
              color: '#10b981',
              opacity: 0.05,
              fontFamily: "'Inter', sans-serif",
            }}
          >
            {currentHealthIndex}
          </div>
          <div
            style={{
              position: 'absolute',
              top: '58%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              fontSize: '1.5rem',
              color: '#10b981',
              opacity: 0.03,
              fontWeight: 500,
              letterSpacing: '0.2em',
              textTransform: 'uppercase',
            }}
          >
            Health Index
          </div>
        </div>
      </motion.div>

      {/* Main Landing Content */}
      <motion.div
        className="landing-container"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <motion.h1 className="landing-title" variants={titleVariants}>
          WACH Insight
        </motion.h1>

        <motion.p className="landing-subtitle" variants={subtitleVariants}>
          AHU Analytics Dashboard
        </motion.p>

        <motion.button
          className="landing-cta"
          variants={ctaVariants}
          initial="hidden"
          animate={showCTA ? 'visible' : 'hidden'}
          whileHover="hover"
          whileTap="tap"
          onClick={onEnter}
        >
          <span style={{ marginRight: '8px' }}>Enter Dashboard View</span>
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M5 12h14" />
            <path d="m12 5 7 7-7 7" />
          </svg>
        </motion.button>
      </motion.div>

      {/* Scroll Indicator */}
      <motion.div
        style={{
          position: 'absolute',
          bottom: '40px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 10,
        }}
        animate={{ y: [0, 10, 0] }}
        transition={{ duration: 2, repeat: Infinity }}
      >
        <div
          style={{
            width: '24px',
            height: '40px',
            border: '2px solid rgba(16, 185, 129, 0.3)',
            borderRadius: '16px',
            position: 'relative',
          }}
        >
          <motion.div
            style={{
              width: '4px',
              height: '10px',
              background: '#10b981',
              borderRadius: '2px',
              position: 'absolute',
              left: '50%',
              top: '8px',
              transform: 'translateX(-50%)',
            }}
            animate={{ y: [0, 16] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          />
        </div>
      </motion.div>
    </div>
  );
};

export default Landing;
