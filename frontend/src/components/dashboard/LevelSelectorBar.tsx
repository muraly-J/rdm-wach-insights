import React from 'react';
import { motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';

/**
 * LevelSelectorBar - Sticky level selector with backdrop-blur (Section 5.1)
 *
 * Position: sticky top-0 z-30 with backdrop-blur-xl
 * Content: [Level 1] [Level 2] ... (pill buttons)
 * State: reads/writes from Zustand store directly
 */
const LEVELS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];

const LevelSelectorBar: React.FC = () => {
  const { selectedLevel, selectLevel } = useAppStore();

  return (
    <motion.div
      className="sticky top-0 z-30 backdrop-blur-xl bg-[rgba(11,15,20,0.85)] border-b border-[#1E2A3A]"
    >
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 py-3 sm:py-4">
        {/* Header */}
        <div className="mb-4 flex items-center gap-3">
          <span className="font-display uppercase tracking-[0.2em] text-[14px] text-[#8A95A5]">
            LEVEL
          </span>
          <div className="h-px flex-1 bg-[#1E2A3A]" />
        </div>

        {/* Level pills */}
        <div className="flex flex-wrap items-center gap-3 overflow-x-auto scrollbar-hidden">
          {LEVELS.map((level) => (
            <motion.button
              key={level}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => selectLevel(level)}
              className={`
                relative px-3 sm:px-5 py-1.5 sm:py-2.5 rounded-full text-xs sm:text-sm font-medium
                transition-colors duration-200 border whitespace-nowrap
                ${
                  selectedLevel === level
                    ? 'bg-[#00E5A0] text-[#0B0F14] border-transparent shadow-[0_0_20px_rgba(0,229,160,0.4)]'
                    : 'bg-transparent text-[#8A95A5] border-[#1E2A3A] hover:border-[#00E5A0] hover:text-[#E8ECF1]'
                }
              `}
            >
              Level {level}
            </motion.button>
          ))}
        </div>
      </div>
    </motion.div>
  );
};

export default LevelSelectorBar;
