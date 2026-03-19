import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
}

/**
 * ChatInput - Input bar for chat widget (Section 6.3)
 * 
 * Text input with send button
 */
const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage }) => {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = () => {
    if (!input.trim()) return;
    
    onSendMessage(input);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex items-center gap-2 px-4 py-3 bg-[#111820] border-t border-[#1E2A3A]">
      <input
        ref={inputRef}
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your AHUs…"
        className="
          flex-1 bg-transparent border-none outline-none
          text-[#E8ECF1] placeholder-[#8A95A5]
          text-sm
        "
      />
      
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={handleSend}
        disabled={!input.trim()}
        className="
          w-8 h-8 rounded-full
          bg-[#00E5A0]
          text-[#0B0F14]
          flex items-center justify-center
          disabled:opacity-30 disabled:cursor-not-allowed
        "
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="22" y1="2" x2="11" y2="13" />
          <polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
      </motion.button>
    </div>
  );
};

export default ChatInput;
