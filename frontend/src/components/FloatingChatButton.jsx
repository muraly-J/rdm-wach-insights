import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// ─────────────────────────────────────────────────────────────────────────────
// FloatingChatButton Component
// Persistent AI chat widget with glass effect and spring animation
//
// Props:
//   - isOpen: Whether chat is open (controlled)
//   - onToggle: Callback when toggle button clicked
//   - chatMessage: Context-aware AI message based on active section
// ─────────────────────────────────────────────────────────────────────────────

const FloatingChatButton = ({
  isOpen,
  onToggle,
  chatMessage = "I see you're exploring the AHU fleet metrics. Which metric would you like to analyze?",
  activeSection = null,
}) => {
  const [isPulsing, setIsPulsing] = useState(false);

  // Pulse effect when chat is closed
  useEffect(() => {
    if (!isOpen) {
      setIsPulsing(true);
      const timer = setTimeout(() => setIsPulsing(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // Chat bubble animation variants
  const chatVariants = {
    closed: {
      opacity: 0,
      scale: 0.8,
      y: 20,
      transition: { type: 'spring', damping: 25, stiffness: 100 },
    },
    open: {
      opacity: 1,
      scale: 1,
      y: 0,
      transition: { type: 'spring', damping: 20, stiffness: 80 },
    },
  };

  // Chat bubble content
  const ChatBubbleContent = () => (
    <div className="chat-bubble-content">
      {/* Header with context-aware greeting */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '16px',
          }}
        >
          <div>
            <div
              style={{
                fontSize: '0.875rem',
                fontWeight: 700,
                color: '#eaf0fb',
              }}
            >
              AI Assistant
            </div>
            {activeSection && (
              <div
                style={{
                  fontSize: '0.75rem',
                  color: '#10b981',
                }}
              >
                Context: {activeSection.replace('_', ' ').toUpperCase()}
              </div>
            )}
          </div>
          <motion.div
            style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              background: '#10b98120',
            }}
            animate={{ rotate: [0, 5, -5, 0] }}
            transition={{ duration: 3, repeat: Infinity }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="#10b981"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </motion.div>
        </div>

        {/* AI Message */}
        <div
          style={{
            padding: '12px 16px',
            background: '#10b9810a',
            borderRadius: '8px',
            borderLeft: '3px solid #10b981',
          }}
        >
          <div
            style={{
              fontSize: '0.9375rem',
              color: '#a3aab5',
              lineHeight: '1.6',
            }}
          >
            {chatMessage}
          </div>
        </div>
      </motion.div>

      {/* Suggested Actions */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        style={{
          marginTop: '20px',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        {[
          'Energy Analysis',
          'Device Comparison',
          'Health Report',
          'Export Data',
        ].map((action, i) => (
          <motion.button
            key={i}
            style={{
              padding: '8px 16px',
              background: '#2A3040',
              border: '1px solid rgba(42, 48, 64, 0.5)',
              borderRadius: '6px',
              color: '#eaf0fb',
              fontSize: '0.75rem',
              cursor: 'pointer',
            }}
            whileHover={{
              background: '#10b98120',
              borderColor: '#10b98140',
            }}
          >
            {action}
          </motion.button>
        ))}
      </motion.div>

      {/* Chat Input Placeholder */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        style={{
          marginTop: '20px',
          padding: '12px 16px',
          background: '#171A21',
          borderRadius: '8px',
          border: '1px solid rgba(42, 48, 64, 0.5)',
        }}
      >
        <div
          style={{
            fontSize: '0.875rem',
            color: '#6b7280',
            paddingLeft: '16px',
          }}
        >
          Type your question...
        </div>
      </motion.div>
    </div>
  );

  return (
    <div className="chat-button-container">
      {/* Chat Bubble */}
      <motion.div
        className="chat-bubble"
        variants={chatVariants}
        initial="closed"
        animate={isOpen ? 'open' : 'closed'}
        style={{
          width: '100%',
          maxWidth: 480,
        }}
      >
        <ChatBubbleContent />
      </motion.div>

      {/* Toggle Button */}
      <motion.button
        className="chat-button"
        onClick={onToggle}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        {/* Chat Icon */}
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H6C5.46957 17 4.96086 16.7893 4.58579 16.4142C4.21071 16.0391 4 15.5304 4 15V6C4 5.46957 4.21071 4.96086 4.58579 4.58579C4.96086 4.21071 5.46957 4 6 4H19C19.5304 4 20.0391 4.21071 20.4142 4.58579C20.7893 4.96086 21 5.46957 21 6V15Z"
            fill="white"
          />
          <path
            d="M7.5 9H16.5"
            stroke="#0F172A"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M7.5 13H12.5"
            stroke="#0F172A"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

        {/* Pulse Effect (only when closed) */}
        {isPulsing && (
          <motion.div
            style={{
              position: 'absolute',
              inset: -6,
              borderRadius: '50%',
            }}
            animate={{
              scale: [1, 1.3],
              opacity: [0.5, 0],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'easeOut',
            }}
          >
            <div
              style={{
                width: '100%',
                height: '100%',
                background: 'linear-gradient(135deg, #10b981, #059669)',
                borderRadius: '50%',
              }}
            />
          </motion.div>
        )}
      </motion.button>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// ChatButton Hook - Simplified wrapper
// ─────────────────────────────────────────────────────────────────────────────

export const useChatButton = () => {
  const [isOpen, setIsOpen] = useState(false);

  const toggleChat = () => {
    setIsOpen(!isOpen);
  };

  return {
    isOpen,
    toggleChat,
  };
};

// ─────────────────────────────────────────────────────────────────────────────
// ChatWidget - Full chat interface component
// ─────────────────────────────────────────────────────────────────────────────

export const ChatWidget = ({ isOpen, onClose }) => {
  return (
    <motion.div
      style={{
        position: 'fixed',
        bottom: '1rem',
        right: '1rem',
        width: '100%',
        maxWidth: 500,
        zIndex: 1000,
      }}
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{
        scale: isOpen ? 1 : 0.8,
        opacity: isOpen ? 1 : 0,
        transition: { type: 'spring', damping: 20, stiffness: 100 },
      }}
    >
      <div
        style={{
          background: '#171A21',
          borderRadius: '24px',
          overflow: 'hidden',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
          border: '1px solid rgba(42, 48, 64, 0.3)',
        }}
      >
        {/* Chat Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '16px 20px',
            background: '#1F232E',
          }}
        >
          <div>
            <div
              style={{
                fontWeight: 700,
                color: '#eaf0fb',
                fontSize: '0.875rem',
              }}
            >
              AI Assistant
            </div>
            <div
              style={{
                fontSize: '0.75rem',
                color: '#10b981',
              }}
            >
              Online
            </div>
          </div>
          <motion.button
            onClick={onClose}
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: '#2A3040',
              border: 'none',
              color: '#a3aab5',
              cursor: 'pointer',
            }}
            whileHover={{ background: '#ef444420', color: '#ef4444' }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path
                d="M18 6L6 18M6 6l12 12"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </motion.button>
        </div>

        {/* Chat Messages */}
        <div
          style={{
            height: 400,
            overflowY: 'auto',
            padding: '20px',
          }}
        >
          <div
            style={{
              marginBottom: '16px',
              padding: '12px 16px',
              background: '#10b98115',
              borderRadius: '8px',
              borderLeft: '3px solid #10b981',
            }}
          >
            <div
              style={{
                fontSize: '0.875rem',
                color: '#eaf0fb',
                lineHeight: '1.6',
              }}
            >
              Hello! I can help you analyze AHU performance, identify energy
              inefficiencies, and compare devices across levels.
            </div>
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '12px',
              marginBottom: '8px',
            }}
          >
            <span
              style={{
                fontSize: '0.75rem',
                color: '#6b7280',
              }}
            >
              10:30 AM
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              gap: '12px',
            }}
          >
            <div
              style={{
                maxWidth: 300,
                padding: '12px 16px',
                background: '#2A3040',
                borderRadius: '8px 8px 8px 0',
              }}
            >
              <div
                style={{
                  fontSize: '0.875rem',
                  color: '#eaf0fb',
                }}
              >
                Can you show me which AHUs have the highest energy consumption?
              </div>
            </div>
          </div>
        </div>

        {/* Chat Input */}
        <div
          style={{
            padding: '16px 20px',
            background: '#1F232E',
          }}
        >
          <div
            style={{
              display: 'flex',
              gap: '12px',
            }}
          >
            <div
              style={{
                flex: 1,
                padding: '12px 16px',
                background: '#0F1115',
                borderRadius: '8px',
                border: '1px solid #2A3040',
              }}
            >
              <div
                style={{
                  fontSize: '0.875rem',
                  color: '#6b7280',
                }}
              >
                Type your question...
              </div>
            </div>
            <motion.button
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '8px',
                background: '#10b981',
                border: 'none',
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              whileHover={{ scale: 1.05, background: '#059669' }}
              whileTap={{ scale: 0.95 }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path
                  d="M22 2L11 13"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
                <path
                  d="M22 2L15 22L11 13L2 9L22 2Z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinejoin="round"
                />
              </svg>
            </motion.button>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default FloatingChatButton;
