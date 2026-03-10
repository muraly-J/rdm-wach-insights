import React from 'react';

interface ChatHeaderProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * ChatHeader - Header bar for chat window (Section 6.3)
 * 
 * bg: var(--bg-tertiary), border-bottom: 1px solid var(--border-subtle)
 * Left: accent dot + "WACH AI"
 * Right: close button (✕)
 */
const ChatHeader: React.FC<ChatHeaderProps> = ({ isOpen, onClose }) => {
  return (
    <div
      className="
        flex items-center justify-between px-4 py-3
        bg-[#1A2230]
        border-b border-[#1E2A3A]
      "
    >
      <div className="flex items-center gap-2">
        <div
          className="w-3 h-3 rounded-full bg-[#00E5A0]"
          style={{ boxShadow: '0 0 8px rgba(0,229,160,0.5)' }}
        />
        <span className="font-semibold text-sm">WACH AI</span>
        <span
          className="
            inline-block w-2 h-2 rounded-full bg-[#00E5A0]
            ml-1.5
          "
        />
      </div>

      <button
        onClick={onClose}
        className="
          w-8 h-8 rounded-full hover:bg-[#1E2A3A]
          flex items-center justify-center
        "
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#E8ECF1" strokeWidth="2">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  );
};

export default ChatHeader;
