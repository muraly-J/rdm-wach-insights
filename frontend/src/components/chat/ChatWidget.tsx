import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import ChatBubbleButton from './ChatBubbleButton';
import ChatWindow from './ChatWindow';
import { NavigateTarget, ActionItem } from '../../api/client';

interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  navigate?: NavigateTarget | null;
  actions?: ActionItem[];
}

const INITIAL_MESSAGE: Message = {
  id: 'init-1',
  role: 'bot',
  content:
    "Hey! I'm RDM-Atlas. I can help you understand health scores, investigate anomalies, or explain what's driving a specific score. What would you like to know?",
};

const PANEL_WIDTH = 380;

const ChatWidget: React.FC = () => {
  const { chatOpen, openChat, closeChat, chatMode, setChatMode } = useAppStore();

  const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);
  const [isMinimized, setIsMinimized] = useState(false);

  // "fullscreen" in this widget means: expand to fill full height on the right side
  const isExpanded = chatMode === 'fullscreen';

  const toggleExpanded = () => {
    setChatMode(isExpanded ? 'panel' : 'fullscreen');
    if (!isExpanded) setIsMinimized(false);
  };

  const handleClose = () => {
    closeChat();
    setIsMinimized(false);
    setChatMode('panel');
  };

  // Height: minimized = header bar only, normal = 520px, expanded = fills up to top
  const panelHeight = isMinimized ? 52 : isExpanded ? 'calc(100vh - 32px)' : 520;

  return (
    <>
      {/* Right-side corner panel */}
      <AnimatePresence>
        {chatOpen && (
          <motion.div
            key="chat-panel"
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.96 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            style={{
              position: 'fixed',
              bottom: 16,
              right: 24,
              width: PANEL_WIDTH,
              height: panelHeight,
              zIndex: 70,
              display: 'flex',
              flexDirection: 'column',
              transition: 'height 0.3s cubic-bezier(0.22,1,0.36,1)',
            }}
          >
            <ChatWindow
              mode={isExpanded ? 'fullscreen' : 'panel'}
              onClose={handleClose}
              onToggleMode={toggleExpanded}
              messages={messages}
              setMessages={setMessages}
              isMinimized={isMinimized}
              onMinimize={() => setIsMinimized((v) => !v)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* FAB — hidden when chat is open */}
      {!chatOpen && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.2 }}
          style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 60 }}
        >
          <ChatBubbleButton onClick={openChat} />
        </motion.div>
      )}
    </>
  );
};

export default ChatWidget;
