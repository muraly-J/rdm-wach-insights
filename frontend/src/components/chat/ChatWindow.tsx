import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import { sendChatMessage, NavigateTarget } from '../../api/client';
import { useAppStore } from '../../store/useAppStore';

export interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  navigate?: NavigateTarget | null;
}

interface ChatWindowProps {
  mode: 'panel' | 'fullscreen';
  onClose: () => void;
  onToggleMode: () => void;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  isMinimized: boolean;
  onMinimize: () => void;
}

const INITIAL_MESSAGE: Message = {
  id: 'init-1',
  role: 'bot',
  content:
    "Hey! I'm RDM-Atlas. I can help you understand health scores, investigate anomalies, or explain what's driving a specific score. What would you like to know?",
};

const ChatWindow: React.FC<ChatWindowProps> = ({
  mode,
  onClose,
  onToggleMode,
  messages,
  setMessages,
  isMinimized,
  onMinimize,
}) => {
  const [isTyping, setIsTyping] = useState(false);
  const [selectedPersona, setSelectedPersona] = useState<
    'general' | 'technical' | 'technician' | 'financial' | null
  >(null);

  const selectedLevel = useAppStore((s) => s.selectedLevel);
  const selectedDevice = useAppStore((s) => s.selectedDevice);
  const financialImpact = useAppStore((s) => s.financialImpact);
  const selectLevel = useAppStore((s) => s.selectLevel);
  const selectDevice = useAppStore((s) => s.selectDevice);

  const handleNavigate = (target: NavigateTarget) => {
    selectLevel(target.level);
    selectDevice(target.device ?? null);
    setTimeout(() => {
      const sectionId = target.view === 'prediction' ? 'prediction-section' : 'dashboard';
      document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth' });
    }, 600);
  };

  const handleClearChat = () => {
    setMessages([INITIAL_MESSAGE]);
  };

  const handlePersonaChange = (
    persona: 'general' | 'technical' | 'technician' | 'financial' | null
  ) => {
    setSelectedPersona(persona);
    if (persona) {
      const labels: Record<string, string> = {
        general: 'general audience',
        technical: 'an engineering perspective',
        technician: 'a maintenance technician perspective',
        financial: 'a financial perspective',
      };
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'bot',
          content: `Got it — I'll explain things from ${labels[persona]}.`,
        },
      ]);
    }
  };

  const handleSendMessage = async (text: string) => {
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    // Build history for the API (exclude the initial bot greeting)
    const history = messages.slice(1).map((m) => ({
      role: m.role === 'bot' ? ('model' as const) : ('user' as const),
      content: m.content,
    }));

    try {
      const { reply, navigate } = await sendChatMessage(text, {
        level: selectedLevel ?? undefined,
        device: selectedDevice ?? undefined,
        financial_impact: financialImpact ?? undefined,
        history,
        persona: selectedPersona,
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
        bg-[#1c2431]
        rounded-[12px]
        overflow-hidden
        shadow-2xl border border-[#2e3f55]
        flex flex-col
      "
      style={{ height: '100%', width: '100%' }}
    >
      <ChatHeader
        mode={mode}
        onClose={onClose}
        onToggleMode={onToggleMode}
        isMinimized={isMinimized}
        onMinimize={onMinimize}
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
