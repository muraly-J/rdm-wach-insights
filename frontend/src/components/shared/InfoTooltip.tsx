import React from 'react';

interface InfoTooltipProps {
  content: React.ReactNode;
}

/**
 * InfoTooltip — Small ⓘ icon that shows a rich explanation card on hover.
 * Accepts any React content (JSX) for structured, multi-section tooltips.
 */
const InfoTooltip: React.FC<InfoTooltipProps> = ({ content }) => {
  const [visible, setVisible] = React.useState(false);

  return (
    <span
      className="relative inline-flex items-center ml-1.5 align-middle z-[9999]"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      <span
        className="
          w-[18px] h-[18px] rounded-full
          bg-[#1E2A3A] border border-[#2A3A4A]
          hover:border-[#00E5A0]
          text-[#8A95A5] text-[11px] font-bold leading-none
          flex items-center justify-center
          cursor-help transition-colors duration-150 select-none
        "
      >
        i
      </span>

      {visible && (
        <div
          className="
            absolute z-[9999] top-6 left-0
            w-80 p-4 rounded-xl
            bg-[#1A2230] border border-[#1E2A3A] shadow-2xl
            text-xs text-[#8A95A5] leading-relaxed
          "
        >
          {content}
        </div>
      )}
    </span>
  );
};

export default InfoTooltip;
