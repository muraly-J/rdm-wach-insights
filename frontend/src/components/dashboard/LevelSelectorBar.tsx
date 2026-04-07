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
      className="sticky top-0 z-30 backdrop-blur-xl bg-[rgba(11,15,20,0.85)] border-b border-[#2e3f55]"
    >
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 py-3 sm:py-4">
        {/* Header */}
        <div className="mb-4 flex items-center gap-3">
          <span className="font-display uppercase tracking-[0.2em] text-xs sm:text-sm text-[#6d6e71]">
            LEVEL
          </span>
          <div className="h-px flex-1 bg-[#2e3f55]" />
        </div>

        {/* Level pills */}
        <div className="flex flex-nowrap sm:flex-wrap items-center gap-2 sm:gap-3 overflow-x-auto scrollbar-hidden">
          {LEVELS.map((level) => (
            <motion.button
              key={level}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => selectLevel(level)}
              className={`
                relative px-3 sm:px-5 py-3 sm:py-2.5 min-h-[44px] sm:min-h-0 rounded-full text-xs sm:text-sm font-medium flex items-center justify-center
                transition-colors duration-200 border whitespace-nowrap
                ${
                  selectedLevel === level
                    ? 'bg-[#4fbd95] text-[#1c2431] border-transparent shadow-[0_0_20px_rgba(79,189,149,0.4)]'
                    : 'bg-transparent text-[#6d6e71] border-[#2e3f55] hover:border-[#4fbd95] hover:text-[#E8ECF1]'
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
