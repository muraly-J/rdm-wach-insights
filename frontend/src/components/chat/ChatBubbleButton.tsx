import React from 'react';
import { motion } from 'framer-motion';

interface ChatBubbleButtonProps {
  onClick: () => void;
}

/**
 * ChatBubbleButton - Collapsed chat widget button (Section 6.1)
 *
 * Position: fixed bottom-6 right-6 z-50
 * Appearance: circular 56px × 56px, accent bg, chat icon
 * Animation: box-shadow pulses with accent-glow (3s loop via CSS keyframes)
 */
const ChatBubbleButton: React.FC<ChatBubbleButtonProps> = ({ onClick }) => {
  return (
    <motion.button
      onClick={onClick}
      className="
        fixed bottom-6 right-6 z-50
        w-[56px] h-[56px]
        bg-[#4fbd95]
        rounded-full
        flex items-center justify-center
        chat-bubble-glow
      "
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Chat icon */}
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#1c2431"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    </motion.button>
  );
};

export default ChatBubbleButton;
