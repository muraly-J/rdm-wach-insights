import React from 'react';
import { motion } from 'framer-motion';

/**
 * CapabilityPills - Horizontal row of small rounded pills (Section 3.2)
 * 
 * Pills: Health Index, 5-Score Breakdown, Device Drill-down, AI Chat Assistant
 * 
 * Spec: bg var(--bg-secondary), border 1px solid var(--border-subtle),
 *       color var(--text-secondary), font-size 13px, padding 6px 16px
 */
const CAPABILITIES = [
  'Health Index',
  '5-Score Breakdown',
  'Device Drill-down',
  'AI Chat Assistant',
] as const;

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { 
    opacity: 1, 
    y: 0,
    transition: {
      duration: 0.4,
      ease: [0.22, 1, 0.36, 1],
    },
  },
};

const CapabilityPills: React.FC = () => {
  return (
    <motion.div
      className="flex flex-wrap justify-center gap-3 mt-8"
      variants={container}
      initial="hidden"
      animate="show"
    >
      {CAPABILITIES.map((cap, idx) => (
        <motion.span
          key={idx}
          variants={item}
          className="
            inline-flex items-center px-4 py-1.5
            bg-[#222d3d]
            border border-[#2e3f55]
            text-[#6d6e71]
            text-[13px]
            rounded-full
          "
        >
          {cap}
        </motion.span>
      ))}
    </motion.div>
  );
};

export default CapabilityPills;
