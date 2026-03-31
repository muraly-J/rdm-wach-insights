import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';

type Persona = 'general' | 'technical' | 'technician' | 'financial' | null;

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  onPersonaChange: (persona: Persona) => void;
  selectedPersona: Persona;
}

const PERSONAS: { value: Persona; label: string }[] = [
  { value: 'general', label: 'General' },
  { value: 'technical', label: 'Engineer' },
  { value: 'technician', label: 'Technician' },
  { value: 'financial', label: 'Financial' },
];

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  onPersonaChange,
  selectedPersona,
}) => {
  const [input, setInput] = useState('');
  const [showRoles, setShowRoles] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

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

  const handlePersonaSelect = (p: Persona) => {
    onPersonaChange(p === selectedPersona ? null : p);
    setShowRoles(false);
  };

  return (
    <div className="bg-[#111820] border-t border-[#1E2A3A]">
      {showRoles && (
        <div className="flex gap-2 px-4 pt-2 pb-1 flex-wrap">
          {PERSONAS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => handlePersonaSelect(value)}
              className={`
                text-xs px-3 py-1 rounded-full border transition-colors
                ${selectedPersona === value
                  ? 'bg-[#00E5A0] text-[#0B0F14] border-[#00E5A0]'
                  : 'bg-transparent text-[#8A95A5] border-[#1E2A3A] hover:border-[#00E5A0] hover:text-[#00E5A0]'}
              `}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 px-4 py-3">
        <button
          onClick={() => setShowRoles((v) => !v)}
          title="Set your role"
          className={`
            w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center transition-colors
            ${selectedPersona
              ? 'bg-[#00E5A0] text-[#0B0F14]'
              : 'text-[#8A95A5] hover:text-[#00E5A0]'}
          `}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="8" r="4" />
            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
          </svg>
        </button>

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
            w-11 h-11 rounded-full flex-shrink-0
            bg-[#00E5A0] text-[#0B0F14]
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
    </div>
  );
};

export default ChatInput;
