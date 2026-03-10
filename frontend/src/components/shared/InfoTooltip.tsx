import React from 'react';

interface InfoTooltipProps {
  text: string;
}

/**
 * InfoTooltip — Small ⓘ icon that shows an explanation card on hover.
 * Place inline next to headings or labels.
 */
const InfoTooltip: React.FC<InfoTooltipProps> = ({ text }) => {
  const [visible, setVisible] = React.useState(false);

  return (
    <span
      className="relative inline-flex items-center ml-1.5 align-middle"
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
            absolute z-50 top-6 left-0
            w-72 p-3 rounded-xl
            bg-[#1A2230] border border-[#1E2A3A] shadow-2xl
            text-xs text-[#8A95A5] leading-relaxed
          "
        >
          {text}
        </div>
      )}
    </span>
  );
};

export default InfoTooltip;
