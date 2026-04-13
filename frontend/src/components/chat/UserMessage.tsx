import React from 'react';
import { motion } from 'framer-motion';

interface UserMessageProps {
  content: string;
}

/**
 * UserMessage - Chat message bubble (Section 6.3)
 *
 * bg: var(--accent), color: var(--bg-primary)
 * border-radius: 16px 16px 4px 16px
 * right-aligned, max-width 85%
 */
const UserMessage: React.FC<UserMessageProps> = ({ content }) => {
  return (
    <motion.div
      className="flex justify-end mb-4"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
    >
      <div
        className="
          max-w-[85%]
          bg-[#4fbd95]
          text-[#1c2431]
          rounded-[16px_16px_4px_16px]
          px-4 py-3
        "
      >
        <p className="text-sm leading-relaxed">{content}</p>
      </div>
    </motion.div>
  );
};

export default UserMessage;
