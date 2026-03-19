import React from 'react';

type PillVariant = 'idle' | 'active' | 'hover';
type PillSize = 'sm' | 'md';

interface PillButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: PillVariant;
  size?: PillSize;
}

/**
 * PillButton - A circular/rounded pill-shaped button component
 * 
 * Idle state: transparent bg, text-secondary text, 1px border
 * Active state: accent bg, primary text, glow shadow
 * Hover state: border transitions to accent
 */
const PillButton: React.FC<PillButtonProps> = ({
  children,
  variant = 'idle',
  size = 'md',
  className = '',
  ...props
}) => {
  // Base styles from spec: pill-shaped, smooth transitions
  const baseStyles = `
    inline-flex items-center justify-center transition-all duration-0.25s ease
    border rounded-full font-medium
  `;

  // Size variants
  const sizeStyles: Record<PillSize, string> = {
    sm: 'px-4 py-2 text-[13px]',
    md: 'px-5 py-2.5 text-sm',
  };

  // Variant styles (matches WACH_INSIGHT_UI_REVAMP_PLAN.md Section 5.1)
  const variantStyles: Record<PillVariant, string> = {
    idle: `
      bg-transparent text-[#8A95A5] border-1 border-[#1E2A3A]
      hover:border-[#00E5A0] hover:text-[#8A95A5]
    `,
    active: `
      bg-[#00E5A0] text-[#0B0F14]
      shadow-[0_0_20px_rgba(0,229,160,0.5)]
      border-0 hover:bg-[#00E5A0] hover:text-[#0B0F14]
    `,
    hover: `
      bg-transparent text-[#8A95A5] border-1 border-[#00E5A0]
    `,
  };

  return (
    <button
      className={`
        ${baseStyles}
        ${sizeStyles[size]}
        ${variantStyles[variant]}
        ${className}
      `}
      {...props}
    >
      {children}
    </button>
  );
};

export default PillButton;
