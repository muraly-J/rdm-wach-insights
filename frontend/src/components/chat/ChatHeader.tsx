import React from 'react';

interface ChatHeaderProps {
  mode: 'panel' | 'fullscreen' | 'split';
  onClose: () => void;
  onToggleMode: () => void;
  onSplitMode?: () => void;
  isMinimized?: boolean;
  onMinimize?: () => void;
}

const ChatHeader: React.FC<ChatHeaderProps> = ({
  mode,
  onClose,
  onToggleMode,
  onSplitMode,
  isMinimized,
  onMinimize,
}) => {
  return (
    <div
      className="
        flex items-center justify-between px-4 py-3
        bg-[#2a3649]
        border-b border-[#2e3f55]
      "
      style={{ flexShrink: 0 }}
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
        {/* Minimize button — collapses panel to header bar */}
        {onMinimize && (
          <button
            onClick={onMinimize}
            title={isMinimized ? 'Restore Chat' : 'Minimize Chat'}
            className="
              w-11 h-11 rounded-full hover:bg-[#2e3f55]
              flex items-center justify-center
            "
          >
            {isMinimized ? (
              /* Restore icon — chevron up */
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#E8ECF1"
                strokeWidth="2"
              >
                <polyline points="18 15 12 9 6 15" />
              </svg>
            ) : (
              /* Minimize icon — dash */
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#E8ECF1"
                strokeWidth="2"
              >
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            )}
          </button>
        )}

        {/* Toggle fullscreen/panel button */}
        <button
          onClick={onToggleMode}
          title={mode === 'panel' ? 'Expand to Fullscreen' : 'Collapse to Panel'}
          className="
            w-11 h-11 rounded-full hover:bg-[#2e3f55]
            flex items-center justify-center
          "
        >
          {mode === 'panel' ? (
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#E8ECF1"
              strokeWidth="2"
            >
              <polyline points="15 3 21 3 21 9" />
              <polyline points="9 21 3 21 3 15" />
              <line x1="21" y1="3" x2="14" y2="10" />
              <line x1="3" y1="21" x2="10" y2="14" />
            </svg>
          ) : (
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#E8ECF1"
              strokeWidth="2"
            >
              <polyline points="4 14 10 14 10 20" />
              <polyline points="20 10 14 10 14 4" />
              <line x1="14" y1="10" x2="21" y2="3" />
              <line x1="3" y1="21" x2="10" y2="14" />
            </svg>
          )}
        </button>

        {/* Split view toggle */}
        {onSplitMode && (
          <button
            onClick={onSplitMode}
            title="Split view"
            className="w-11 h-11 rounded-full hover:bg-[#2e3f55] flex items-center justify-center"
            style={mode === 'split' ? { border: '1px solid #00E5A0', background: 'rgba(0,229,160,0.1)' } : undefined}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <rect x="1" y="1" width="5" height="12" rx="1" stroke={mode === 'split' ? '#00E5A0' : '#8899aa'} strokeWidth="1.5" />
              <rect x="8" y="1" width="5" height="12" rx="1" stroke={mode === 'split' ? '#00E5A0' : '#8899aa'} strokeWidth="1.5" />
            </svg>
          </button>
        )}

        {/* Close button */}
        <button
          onClick={onClose}
          title="Close Chat"
          className="
            w-11 h-11 rounded-full hover:bg-[#2e3f55]
            flex items-center justify-center
          "
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#E8ECF1"
            strokeWidth="2"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default ChatHeader;
