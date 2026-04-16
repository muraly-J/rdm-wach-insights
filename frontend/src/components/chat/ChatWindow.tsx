import React, { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import SuggestedPrompts from './SuggestedPrompts';
import ConversationHistory from './ConversationHistory';
import { NavigateTarget } from '../../api/client';
import { useAppStore } from '../../store/useAppStore';
import { Message } from '../../types/chat';
import { useSSEChat } from '../../hooks/useSSEChat';
import { useConversationHistory } from '../../hooks/useConversationHistory';

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
  const [selectedPersona, setSelectedPersona] = useState<
    'general' | 'technical' | 'technician' | 'financial' | null
  >(null);
  const [latestSuggestions, setLatestSuggestions] = useState<string[]>([]);

  const {
    conversations,
    activeId,
    saveCurrentConversation,
    loadConversation,
    deleteConversation,
    startNewConversation,
  } = useConversationHistory();

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

  // Track suggestions from latest bot message
  useEffect(() => {
    const lastBot = [...messages].reverse().find((m) => m.role === 'bot');
    if (lastBot?.suggestions?.length) {
      setLatestSuggestions(lastBot.suggestions);
    }
  }, [messages]);

  // Auto-save conversation when messages change
  useEffect(() => {
    if (messages.length > 1) {
      saveCurrentConversation(messages);
    }
  }, [messages, saveCurrentConversation]);

  const handleLoadConversation = useCallback(
    (id: string) => {
      const msgs = loadConversation(id);
      if (msgs) setMessages(msgs);
    },
    [loadConversation, setMessages]
  );

  const handleNewChat = useCallback(() => {
    startNewConversation();
    setMessages([{
      id: 'greeting',
      role: 'bot',
      content: "Hello! I'm **RDM-Atlas**, your building health assistant. How can I help you today?",
    }]);
  }, [startNewConversation, setMessages]);

  const { sendStreaming, isStreaming: sseStreaming } = useSSEChat({
    onNavigate: handleNavigate,
  });

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

  const handleSendMessage = useCallback(
    async (text: string) => {
      await sendStreaming(text, messages, setMessages, {
        level: selectedLevel ?? undefined,
        device: selectedDevice,
        financial_impact: financialImpact?.grand_total ?? null,
        persona: selectedPersona,
      });
    },
    [sendStreaming, messages, setMessages, selectedLevel, selectedDevice, financialImpact, selectedPersona]
  );

  const handlePromptSelect = useCallback(
    (prompt: string) => {
      handleSendMessage(prompt);
      setLatestSuggestions([]);
    },
    [handleSendMessage]
  );

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
            <div className="flex flex-1 overflow-hidden min-h-0">
              {mode === 'fullscreen' && (
                <ConversationHistory
                  conversations={conversations}
                  activeId={activeId}
                  onSelect={handleLoadConversation}
                  onDelete={deleteConversation}
                  onNewChat={handleNewChat}
                />
              )}
              <div className="flex flex-1 flex-col overflow-hidden min-h-0">
                <MessageList
                  messages={messages}
                  isTyping={sseStreaming}
                  onNavigate={handleNavigate}
                  onClearChat={handleClearChat}
                />
                <SuggestedPrompts
                  suggestions={latestSuggestions}
                  onSelect={handlePromptSelect}
                  hasMessages={messages.length > 1}
                />
                <ChatInput
                  onSendMessage={handleSendMessage}
                  onPersonaChange={handlePersonaChange}
                  selectedPersona={selectedPersona}
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default ChatWindow;
