import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import ChatBubbleButton from './ChatBubbleButton';
import ChatWindow from './ChatWindow';

const ChatWidget: React.FC = () => {
  const { chatOpen, openChat, closeChat, chatMode, setChatMode } = useAppStore();

  const toggleFullscreen = () => setChatMode(chatMode === 'fullscreen' ? 'panel' : 'fullscreen');

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
              onClose={closeChat}
              onToggleMode={toggleFullscreen}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bottom panel — lower half of screen */}
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
              height: '50dvh', zIndex: 70,
              background: '#0f1923',
              borderTop: '1px solid rgba(0,229,160,0.2)',
              boxShadow: '0 -8px 40px rgba(0,0,0,0.5)',
              display: 'flex', flexDirection: 'column',
            }}
          >
            <ChatWindow
              mode="panel"
              onClose={closeChat}
              onToggleMode={toggleFullscreen}
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
