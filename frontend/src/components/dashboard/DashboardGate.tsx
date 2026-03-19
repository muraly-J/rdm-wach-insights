import React from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';

/**
 * DashboardGate - Scroll-triggered gate animation (Section 4.1)
 * 
 * As user scrolls past the hero, a thin horizontal line expands from centre outward.
 * Simultaneously, text below fades in: "Dashboard"
 */
const DashboardGate: React.FC = () => {
  const { scrollYProgress } = useScroll();
  
  // Animate line expansion when scrolled past hero (roughly after 100vh)
  const lineScaleX = useTransform(
    scrollYProgress,
    [0.2, 0.3], // Trigger after ~1/5 of scroll
    [0, 1]
  );
  
  const textOpacity = useTransform(
    scrollYProgress,
    [0.25, 0.35],
    [0, 1]
  );

  return (
    <div className="py-16 flex flex-col items-center gap-8">
      {/* Animated expanding line (Section 4.1) */}
      <motion.div
        className="h-[2px] w-32 bg-[#00E5A0]"
        style={{ scaleX: lineScaleX }}
      />

      {/* Gate text (Section 4.1) */}
      <motion.div
        className="flex flex-col items-center gap-2"
        style={{ opacity: textOpacity }}
      >
        <span
          className="
            font-display uppercase tracking-[0.2em]
            text-[14px] text-[#8A95A5]
          "
        >
          DASHBOARD
        </span>
        
        <motion.h2
          className="font-display text-[24px] sm:text-[36px] font-bold leading-tight tracking-[-0.02em]"
          style={{ opacity: textOpacity }}
        >
          AHU Health Overview
        </motion.h2>
      </motion.div>

      {/* Sub-header instruction (Section 4.2) */}
      <motion.p
        className="text-[#8A95A5] max-w-2xl text-center"
        style={{ opacity: textOpacity }}
      >
        Select a building level to begin exploring AHU health data.
      </motion.p>
    </div>
  );
};

export default DashboardGate;
