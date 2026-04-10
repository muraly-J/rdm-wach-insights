import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import ChatBubbleButton from './ChatBubbleButton';
import ChatWindow from './ChatWindow';
import { NavigateTarget } from '../../api/client';

interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  navigate?: NavigateTarget | null;
}

const INITIAL_MESSAGE: Message = {
  id: 'init-1',
  role: 'bot',
  content: "Hey! I'm RDM-Atlas. I can help you understand health scores, investigate anomalies, or explain what's driving a specific score. What would you like to know?",
};

const ChatWidget: React.FC = () => {
  const { chatOpen, openChat, closeChat, chatMode, setChatMode } = useAppStore();

  // Lifted state — persists across panel ↔ fullscreen ↔ minimized transitions
  const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);
  const [isMinimized, setIsMinimized] = useState(false);

  const toggleFullscreen = () => {
    setChatMode(chatMode === 'fullscreen' ? 'panel' : 'fullscreen');
    // Un-minimize when switching to fullscreen
    if (chatMode !== 'fullscreen') setIsMinimized(false);
  };

  const handleClose = () => {
    closeChat();
    setIsMinimized(false);
  };

  const panelHeight = isMinimized ? 52 : '50dvh';

  return (
    <>
      {/* Fullscreen overlay */}
      <AnimatePresence>
        {chatOpen && chatMode === 'fullscreen' && (
          <motion.div
            key="chat-fullscreen"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{
              position: 'fixed', inset: 0, zIndex: 80,
              background: '#0B0F14',
              display: 'flex', flexDirection: 'column',
            }}
          >
            <ChatWindow
              mode="fullscreen"
              onClose={handleClose}
              onToggleMode={toggleFullscreen}
              messages={messages}
              setMessages={setMessages}
              isMinimized={false}
              onMinimize={() => {
                // Switching from fullscreen to panel when user clicks minimize
                setChatMode('panel');
                setIsMinimized(true);
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bottom panel */}
      <AnimatePresence>
        {chatOpen && chatMode === 'panel' && (
          <motion.div
            key="chat-panel"
            initial={{ y: '100%', opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: '100%', opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            style={{
              position: 'fixed', bottom: 0, left: 0, right: 0,
              height: panelHeight,
              zIndex: 70,
              background: '#0f1923',
              borderTop: '1px solid rgba(0,229,160,0.2)',
              boxShadow: '0 -8px 40px rgba(0,0,0,0.5)',
              display: 'flex', flexDirection: 'column',
              overflow: 'hidden',
              transition: 'height 0.25s ease',
            }}
          >
            <ChatWindow
              mode="panel"
              onClose={handleClose}
              onToggleMode={toggleFullscreen}
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
