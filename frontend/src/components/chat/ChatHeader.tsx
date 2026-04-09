import React from 'react';

interface ChatHeaderProps {
  mode: 'panel' | 'fullscreen';
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
        {/* Toggle fullscreen/panel button */}
        <button
          onClick={onToggleMode}
          title={mode === 'panel' ? 'Expand to fullscreen' : 'Collapse to panel'}
          className="
            w-11 h-11 rounded-full hover:bg-[#2e3f55]
            flex items-center justify-center
          "
        >
          {mode === 'panel' ? (
            /* Expand icon — arrows pointing outward */
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#E8ECF1" strokeWidth="2">
              <polyline points="15 3 21 3 21 9" />
              <polyline points="9 21 3 21 3 15" />
              <line x1="21" y1="3" x2="14" y2="10" />
              <line x1="3" y1="21" x2="10" y2="14" />
            </svg>
          ) : (
            /* Collapse icon — arrows pointing inward */
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#E8ECF1" strokeWidth="2">
              <polyline points="4 14 10 14 10 20" />
              <polyline points="20 10 14 10 14 4" />
              <line x1="14" y1="10" x2="21" y2="3" />
              <line x1="3" y1="21" x2="10" y2="14" />
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
