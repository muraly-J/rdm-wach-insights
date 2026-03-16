import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import BotMessage from './BotMessage';
import UserMessage from './UserMessage';
import TypingIndicator from './TypingIndicator';
import { NavigateTarget } from '../../api/client';

interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  navigate?: NavigateTarget | null;
}

interface MessageListProps {
  messages: Message[];
  isTyping: boolean;
  onNavigate: (target: NavigateTarget) => void;
}

/**
 * MessageList - Scrollable message container (Section 6.3)
 */
const MessageList: React.FC<MessageListProps> = ({ messages, isTyping, onNavigate }) => {
  const bottomRef = React.useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-2">
      {messages.length === 0 && (
        <div className="text-center text-[#8A95A5] py-8">
          Start a conversation with WACH AI
        </div>
      )}

      <AnimatePresence initial={false}>
        {messages.map((msg) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {msg.role === 'bot' ? (
              <BotMessage
                content={msg.content}
                navigate={msg.navigate}
                onNavigate={onNavigate}
              />
            ) : (
              <UserMessage content={msg.content} />
            )}
          </motion.div>
        ))}
      </AnimatePresence>

      {isTyping && <TypingIndicator />}

      <div ref={bottomRef} />
    </div>
  );
};

export default MessageList;
