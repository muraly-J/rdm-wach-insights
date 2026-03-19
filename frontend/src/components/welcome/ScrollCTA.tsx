import React from 'react';
import { motion } from 'framer-motion';

/**
 * ScrollCTA - Downward-pointing animated chevron with "Scroll to explore" (Section 3.2)
 * 
 * Animation: y: [0,8,0] loop
 * Text: 13px mono
 */
const ScrollCTA: React.FC = () => {
  return (
    <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-3">
      <motion.div
        animate={{ y: [0, 8, 0] }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        className="w-6 h-8 flex flex-col items-center justify-start gap-1"
      >
        <div className="w-1 h-3 bg-[#8A95A5] rounded-full" />
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#8A95A5"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </motion.div>
      
      <span className="text-[13px] font-mono text-[#8A95A5] tracking-wide">
        Scroll to explore
      </span>
    </div>
  );
};

export default ScrollCTA;
