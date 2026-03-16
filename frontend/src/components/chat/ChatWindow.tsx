import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import { sendChatMessage, NavigateTarget } from '../../api/client';
import { useAppStore } from '../../store/useAppStore';

interface ChatWindowProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  navigate?: NavigateTarget | null;
}

const INITIAL_MESSAGE: Message = {
  id: 'init-1',
  role: 'bot',
  content: "Hey! I'm WACH AI. I can help you understand health scores, investigate anomalies, or explain what's driving a specific score. What would you like to know?",
};

const ChatWindow: React.FC<ChatWindowProps> = ({ isOpen, onClose }) => {
  const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);
  const [isTyping, setIsTyping] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);

  const selectedLevel = useAppStore((s) => s.selectedLevel);
  const selectedDevice = useAppStore((s) => s.selectedDevice);
  const selectLevel = useAppStore((s) => s.selectLevel);
  const selectDevice = useAppStore((s) => s.selectDevice);

  const handleNavigate = (target: NavigateTarget) => {
    selectLevel(target.level);
    selectDevice(target.device ?? null);
  };

  const handleClearChat = () => {
    setMessages([INITIAL_MESSAGE]);
  };

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
      const { reply, navigate } = await sendChatMessage(text, {
        level: selectedLevel ?? undefined,
        device: selectedDevice ?? undefined,
        history,
      });
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: 'bot', content: reply, navigate },
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
        w-[400px]
        bg-[#0B0F14]
        rounded-[20px]
        overflow-hidden
        shadow-2xl border border-[#1E2A3A]
        flex flex-col
      "
      animate={{ height: isMinimized ? 'auto' : 560 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      initial={{ opacity: 0, scale: 0.9 }}
      exit={{ opacity: 0, scale: 0.9 }}
    >
      <ChatHeader
        isOpen={isOpen}
        onClose={onClose}
        isMinimized={isMinimized}
        onMinimize={() => setIsMinimized((v) => !v)}
      />

      <AnimatePresence initial={false}>
        {!isMinimized && (
          <motion.div
            key="chat-body"
            className="flex flex-col flex-1 min-h-0"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            <MessageList
              messages={messages}
              isTyping={isTyping}
              onNavigate={handleNavigate}
              onClearChat={handleClearChat}
            />
            <ChatInput onSendMessage={handleSendMessage} />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default ChatWindow;
