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
      bg-transparent text-[#6d6e71] border-1 border-[#2e3f55]
      hover:border-[#4fbd95] hover:text-[#6d6e71]
    `,
    active: `
      bg-[#4fbd95] text-[#1c2431]
      shadow-[0_0_20px_rgba(79,189,149,0.5)]
      border-0 hover:bg-[#4fbd95] hover:text-[#1c2431]
    `,
    hover: `
      bg-transparent text-[#6d6e71] border-1 border-[#4fbd95]
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
