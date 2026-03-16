import React from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';

interface BotMessageProps {
  content: string;
}

/**
 * BotMessage - Chat message bubble (Section 6.3)
 * 
 * bg: var(--bg-secondary), border-radius: 16px 16px 16px 4px
 * left-aligned, max-width 85%
 */
const BotMessage: React.FC<BotMessageProps> = ({ content }) => {
  return (
    <motion.div
      className="flex justify-start mb-4"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
    >
      <div
        className="
          max-w-[85%]
          bg-[#111820]
          rounded-[16px_16px_16px_4px]
          px-4 py-3
        "
      >
        <div className="text-sm text-[#E8ECF1] leading-relaxed prose prose-invert prose-sm max-w-none">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      </div>
    </motion.div>
  );
};

export default BotMessage;
