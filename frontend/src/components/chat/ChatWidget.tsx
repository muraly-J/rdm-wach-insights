import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import ChatBubbleButton from './ChatBubbleButton';
import ChatWindow from './ChatWindow';

/**
 * ChatWidget - Main chat widget component (Section 6)
 * 
 * Manages collapsed/expanded state
 * Morph animation between circle and rectangle
 */
const ChatWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <ChatWindow isOpen={isOpen} onClose={() => setIsOpen(false)} />
        )}
      </AnimatePresence>

      {!isOpen && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: 0.5 }}
        >
          <ChatBubbleButton onClick={() => setIsOpen(true)} />
          
          {/* Tooltip on hover */}
          <motion.div
            className="
              fixed bottom-[70px] right-6 z-50
              bg-[#2a3649] text-[#E8ECF1]
              px-3 py-1.5 rounded-lg text-sm
              shadow-xl
            "
            initial={{ opacity: 0, y: 8 }}
            whileHover={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
          >
            Chat with WACH AI
          </motion.div>
        </motion.div>
      )}
    </>
  );
};

export default ChatWidget;
