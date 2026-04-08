import React from 'react';

interface ChatHeaderProps {
  mode: 'sidebar' | 'fullscreen';
  onClose: () => void;
  onToggleMode: () => void;
  isMinimized?: boolean;
  onMinimize?: () => void;
}

/**
 * ChatHeader - Header bar for chat window (Section 6.3)
 *
 * bg: var(--bg-tertiary), border-bottom: 1px solid var(--border-subtle)
 * Left: accent dot + "RDM-Atlas"
 * Right: toggle mode button + close button (✕)
 */
const ChatHeader: React.FC<ChatHeaderProps> = ({ mode, onClose, onToggleMode, isMinimized, onMinimize }) => {
  return (
    <div
      className="
        flex items-center justify-between px-4 py-3
        bg-[#2a3649]
        border-b border-[#2e3f55]
      "
    >
      <div className="flex items-center gap-2">
        <div
          className="w-3 h-3 rounded-full bg-[#00E5A0]"
          style={{ boxShadow: '0 0 8px rgba(0,229,160,0.5)' }}
        />
        <span className="font-semibold text-sm text-[#00E5A0]">RDM-Atlas</span>
        <span className="inline-block w-2 h-2 rounded-full bg-[#00E5A0] ml-1.5" />
      </div>

      <div className="flex items-center gap-1">
        {/* Toggle fullscreen/sidebar button */}
        <button
          onClick={onToggleMode}
          title={mode === 'sidebar' ? 'Expand to fullscreen' : 'Collapse to sidebar'}
          className="
            w-11 h-11 rounded-full hover:bg-[#2e3f55]
            flex items-center justify-center
          "
        >
          {mode === 'sidebar' ? (
            /* Expand icon — diagonal arrow up-right */
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#E8ECF1" strokeWidth="2">
              <polyline points="7 17 17 7" />
              <polyline points="7 7 17 7 17 17" />
            </svg>
          ) : (
            /* Collapse icon — diagonal arrow down-left */
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#E8ECF1" strokeWidth="2">
              <polyline points="17 7 7 17" />
              <polyline points="17 17 7 17 7 7" />
            </svg>
          )}
        </button>

        {/* Close button */}
        <button
          onClick={onClose}
          title="Close chat"
          className="
            w-11 h-11 rounded-full hover:bg-[#2e3f55]
            flex items-center justify-center
          "
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#E8ECF1" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default ChatHeader;
