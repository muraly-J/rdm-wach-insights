import React, { useState } from 'react';
import { motion } from 'framer-motion';

import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import { sendChatMessage } from '../../api/client';
import { useAppStore } from '../../store/useAppStore';

interface ChatWindowProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
}

const INITIAL_MESSAGE: Message = {
  id: 'init-1',
  role: 'bot',
  content: "Hey! I'm WACH AI. I can help you understand health scores, investigate anomalies, or explain what's driving a specific score. What would you like to know?",
};

const ChatWindow: React.FC<ChatWindowProps> = ({ isOpen, onClose }) => {
  const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);
  const [isTyping, setIsTyping] = useState(false);

  const selectedLevel = useAppStore((s) => s.selectedLevel);
  const selectedDevice = useAppStore((s) => s.selectedDevice);

  const handleSendMessage = async (text: string) => {
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    // Build history for the API (exclude the initial bot greeting)
    const history = messages
      .slice(1) // skip initial bot message
      .map((m) => ({
        role: m.role === 'bot' ? ('model' as const) : ('user' as const),
        content: m.content,
      }));

    try {
      const { reply } = await sendChatMessage(text, {
        level: selectedLevel ?? undefined,
        device: selectedDevice ?? undefined,
        history,
      });
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: 'bot', content: reply },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'bot',
          content: 'Sorry, I had trouble connecting. Please try again in a moment.',
        },
      ]);
    } finally {
      setIsTyping(false);
    }
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
      <MessageList messages={messages} isTyping={isTyping} />
      <ChatInput onSendMessage={handleSendMessage} />
    </motion.div>
  );
};

export default ChatWindow;
