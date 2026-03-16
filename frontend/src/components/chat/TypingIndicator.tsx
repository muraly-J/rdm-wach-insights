import React from 'react';
import { motion } from 'framer-motion';

/**
 * TypingIndicator - Three bouncing dots animation (Section 6.3)
 */
const TypingIndicator: React.FC = () => {
  return (
    <div className="flex items-center gap-2 px-4 py-3">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-2 h-2 rounded-full bg-[#8A95A5]"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{
            duration: 0.6,
            repeat: Infinity,
            delay: i * 0.15,
          }}
        />
      ))}
    </div>
  );
};

export default TypingIndicator;
