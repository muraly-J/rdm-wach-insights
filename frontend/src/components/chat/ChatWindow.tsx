import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import { sendChatMessage } from '../../api/client';
import { useAppStore } from '../../store/useAppStore';
import { ChatMessage, NavigateTarget } from '../../types';

interface ChatWindowProps {
  isOpen: boolean;
  onClose: () => void;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ isOpen, onClose }) => {
  const [isTyping, setIsTyping] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [selectedPersona, setSelectedPersona] = useState<'general' | 'technical' | 'technician' | 'financial' | null>(null);

  const chatMessages = useAppStore((s) => s.chatMessages);
  const addMessage = useAppStore((s) => s.addMessage);
  const selectedLevel = useAppStore((s) => s.selectedLevel);
  const selectedDevice = useAppStore((s) => s.selectedDevice);
  const financialImpact = useAppStore((s) => s.financialImpact);
  const selectLevel = useAppStore((s) => s.selectLevel);
  const selectDevice = useAppStore((s) => s.selectDevice);

  // Generate unique message ID with millisecond + random suffix
  const generateMessageId = (): string => {
    return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  };

  const handleNavigate = (target: NavigateTarget) => {
    selectLevel(target.level);
    selectDevice(target.device ?? null);
    setTimeout(() => {
      const sectionId = target.view === 'prediction' ? 'prediction-section' : 'dashboard';
      document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth' });
    }, 600);
  };

  const handleClearChat = () => {
    const initialMessage: ChatMessage = {
      id: 'init-1',
      role: 'bot',
      content: "Hey! I'm WACH AI. I can help you understand health scores, investigate anomalies, or explain what's driving a specific score. What would you like to know?",
      timestamp: new Date(),
    };
    useAppStore.setState({ chatMessages: [initialMessage] });
  };

  const handlePersonaChange = (persona: 'general' | 'technical' | 'technician' | 'financial' | null) => {
    setSelectedPersona(persona);
    if (persona) {
      const labels: Record<string, string> = {
        general: 'general audience',
        technical: 'an engineering perspective',
        technician: 'a maintenance technician perspective',
        financial: 'a financial perspective',
      };
      const message: ChatMessage = {
        id: generateMessageId(),
        role: 'bot',
        content: `Got it — I'll explain things from ${labels[persona]}.`,
        timestamp: new Date(),
      };
      addMessage(message);
    }
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    try {
      setIsTyping(true);

      // Add user message to store
      const userMessage: ChatMessage = {
        id: generateMessageId(),
        role: 'user',
        content: text,
        timestamp: new Date(),
      };
      addMessage(userMessage);

      // Build history for the API (exclude the initial bot greeting)
      const history = chatMessages
        .slice(1) // skip initial bot message
        .map((m) => ({
          role: m.role === 'bot' ? ('model' as const) : ('user' as const),
          content: m.content,
        }));

      const { reply, navigate } = await sendChatMessage(text, {
        level: selectedLevel ?? undefined,
        device: selectedDevice ?? undefined,
        financial_impact: financialImpact ?? undefined,
        history,
        persona: selectedPersona,
      });

      // Add bot message to store
      const botMessage: ChatMessage = {
        id: generateMessageId(),
        role: 'bot',
        content: reply,
        timestamp: new Date(),
        navigate: navigate || null,
      };
      addMessage(botMessage);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: ChatMessage = {
        id: generateMessageId(),
        role: 'bot',
        content: 'Sorry, I had trouble connecting. Please try again in a moment.',
        timestamp: new Date(),
      };
      addMessage(errorMessage);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <motion.div
      layoutId="chat-window"
      className="
        fixed z-50
        bottom-0 right-0 left-0 sm:bottom-6 sm:right-6 sm:left-auto
        w-full sm:w-[400px]
        bg-[#1c2431]
        rounded-t-[20px] sm:rounded-[20px]
        overflow-hidden max-h-[82dvh]
        shadow-2xl border border-[#2e3f55]
        flex flex-col
      "
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      initial={{ opacity: 0, scale: 0.9 }}
      exit={{ opacity: 0, scale: 0.9 }}
      style={{ height: isMinimized ? 'auto' : 'min(560px, 80dvh)' }}
    >
      <ChatHeader
        isMinimized={isMinimized}
        onMinimize={() => setIsMinimized((v) => !v)}
        onClose={onClose}
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
              messages={chatMessages}
              isTyping={isTyping}
              onNavigate={handleNavigate}
              onClearChat={handleClearChat}
            />
            <ChatInput
              onSendMessage={handleSendMessage}
              onPersonaChange={handlePersonaChange}
              selectedPersona={selectedPersona}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default ChatWindow;
