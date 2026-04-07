import React from 'react';
import { createPortal } from 'react-dom';

interface InfoTooltipProps {
  content: React.ReactNode;
}

/**
 * InfoTooltip — Small ⓘ icon that shows a rich explanation card on hover.
 * Renders via a portal to document.body so it always sits above every
 * stacking context (transforms, opacity layers, chart SVGs, etc.).
 */
const InfoTooltip: React.FC<InfoTooltipProps> = ({ content }) => {
  const [visible, setVisible] = React.useState(false);
  const [pos, setPos] = React.useState({ top: 0, left: 0 });
  const triggerRef = React.useRef<HTMLSpanElement>(null);

  const handleMouseEnter = () => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPos({ top: rect.bottom + 6, left: rect.left });
    }
    setVisible(true);
  };

  return (
    <span className="inline-flex items-center ml-1.5 align-middle">
      <span
        ref={triggerRef}
        className="
          w-[18px] h-[18px] rounded-full
          bg-[#2e3f55] border border-[#2A3A4A]
          hover:border-[#4fbd95]
          text-[#6d6e71] text-[11px] font-bold leading-none
          flex items-center justify-center
          cursor-help transition-colors duration-150 select-none
        "
        onMouseEnter={handleMouseEnter}
        onMouseLeave={() => setVisible(false)}
      >
        i
      </span>

      {visible && createPortal(
        <div
          style={{ position: 'fixed', top: pos.top, left: pos.left, zIndex: 99999 }}
          className="
            w-80 p-4 rounded-xl
            bg-[#2a3649] border border-[#2e3f55] shadow-2xl
            text-xs text-[#6d6e71] leading-relaxed
          "
          onMouseEnter={() => setVisible(true)}
          onMouseLeave={() => setVisible(false)}
        >
          {content}
        </div>,
        document.body,
      )}
    </span>
  );
};

export default InfoTooltip;
