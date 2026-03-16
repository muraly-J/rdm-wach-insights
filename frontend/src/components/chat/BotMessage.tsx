import React from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { NavigateTarget } from '../../api/client';

interface BotMessageProps {
  content: string;
  navigate?: NavigateTarget | null;
  onNavigate?: (target: NavigateTarget) => void;
}

/**
 * BotMessage - Chat message bubble (Section 6.3)
 *
 * bg: var(--bg-secondary), border-radius: 16px 16px 16px 4px
 * left-aligned, max-width 85%
 */
const BotMessage: React.FC<BotMessageProps> = ({ content, navigate, onNavigate }) => {
  const navigateLabel = navigate
    ? navigate.device
      ? `Navigate to ${navigate.device} — Level ${navigate.level}`
      : `Navigate to Level ${navigate.level}`
    : null;

  return (
    <motion.div
      className="flex justify-start mb-4"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
    >
      <div className="max-w-[85%] flex flex-col gap-2">
        <div
          className="
            bg-[#111820]
            rounded-[16px_16px_16px_4px]
            px-4 py-3
          "
        >
          <div className="text-sm text-[#E8ECF1] leading-relaxed prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        </div>

        {navigateLabel && onNavigate && navigate && (
          <button
            onClick={() => onNavigate(navigate)}
            className="
              self-start
              flex items-center gap-1.5
              text-xs font-medium
              text-[#00E5A0]
              border border-[#00E5A0]/30
              rounded-full
              px-3 py-1
              hover:bg-[#00E5A0]/10
              transition-colors duration-150
            "
          >
            <span>↗</span>
            <span>{navigateLabel}</span>
          </button>
        )}
      </div>
    </motion.div>
  );
};

export default BotMessage;
