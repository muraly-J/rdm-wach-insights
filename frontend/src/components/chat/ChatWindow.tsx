import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import { simulateBotResponse } from '../../mocks/generateMockData';

interface ChatWindowProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * ChatWindow - Expanded chat widget (Section 6.3)
 * 
 * Structure:
 *   Header bar (48px tall)
 *   Message area (flex-1, scrollable)
 *   Input bar (56px tall)
 */
const ChatWindow: React.FC<ChatWindowProps> = ({ isOpen, onClose }) => {
  const [messages, setMessages] = useState([
    {
      id: 'init-1',
      role: 'bot' as const,
      content: "Hey! I'm WACH AI. I can help you understand health scores, investigate anomalies, or explain what's driving a specific score. What would you like to know?",
    },
  ]);
  const [isTyping, setIsTyping] = useState(false);

  const handleSendMessage = async (text: string) => {
    const newMessage = { id: Date.now().toString(), role: 'user' as const, content: text };
    setMessages((prev) => [...prev, newMessage]);
    setIsTyping(true);

    // Simulate bot response
    const response = await simulateBotResponse(text);
    
    setIsTyping(false);
    setMessages((prev) => [
      ...prev,
      { id: (Date.now() + 1).toString(), role: 'bot' as const, content: response },
    ]);
  };

  return (
    <motion.div
      layoutId="chat-window"
      className="
        fixed bottom-6 right-6 z-50
        w-[400px] h-[560px]
        bg-[#0B0F14]
        rounded-[20px]
        overflow-hidden
        shadow-2xl border border-[#1E2A3A]
        flex flex-col
      "
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{
        layout: { duration: 0.45, ease: [0.22, 1, 0.36, 1] },
        opacity: { duration: 0.45, ease: [0.22, 1, 0.36, 1] },
      }}
    >
      <ChatHeader isOpen={isOpen} onClose={onClose} />

      <MessageList
        messages={messages}
        isTyping={isTyping}
      />

      <ChatInput onSendMessage={handleSendMessage} />
    </motion.div>
  );
};

export default ChatWindow;
