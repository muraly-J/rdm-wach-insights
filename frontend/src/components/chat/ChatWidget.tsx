import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import ChatBubbleButton from './ChatBubbleButton';
import ChatWindow from './ChatWindow';

const ChatWidget: React.FC = () => {
  const { chatOpen, openChat, closeChat, chatMode, setChatMode } = useAppStore();

  const toggleFullscreen = () => setChatMode(chatMode === 'fullscreen' ? 'sidebar' : 'fullscreen');

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

      {/* Sidebar */}
      <AnimatePresence>
        {chatOpen && chatMode === 'sidebar' && (
          <motion.div
            key="chat-sidebar"
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            style={{
              position: 'fixed', top: 0, right: 0, bottom: 0,
              width: 380, zIndex: 70,
              background: '#0f1923',
              borderLeft: '1px solid rgba(0,229,160,0.2)',
              boxShadow: '-8px 0 40px rgba(0,0,0,0.5)',
              display: 'flex', flexDirection: 'column',
            }}
          >
            <ChatWindow
              mode="sidebar"
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
