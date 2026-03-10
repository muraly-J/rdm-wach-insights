import type { Config } from 'tailwindcss';

export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Design tokens from WACH_INSIGHT_UI_REVAMP_PLAN.md
        bg: {
          primary: '#0B0F14',
          secondary: '#111820',
          tertiary: '#1A2230',
        },
        border: {
          subtle: '#1E2A3A',
          accent: '#00E5A0',
        },
        text: {
          primary: '#E8ECF1',
          secondary: '#8A95A5',
        },
        accent: {
          DEFAULT: '#00E5A0',
          glow: 'rgba(0, 229, 160, 0.15)',
          secondary: '#00B8D4',
        },
        danger: '#FF4D6A',
        warning: '#FFB020',
        success: '#00E5A0',
        chart: {
          1: '#00E5A0',
          2: '#00B8D4',
          3: '#7C5CFC',
          4: '#FF6B8A',
          5: '#FFB020',
        },
      },
      fontFamily: {
        display: ['Plus Jakarta Sans', 'sans-serif'],
        headings: ['Plus Jakarta Sans', 'sans-serif'],
        body: ['DM Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      fontSize: {
        // Display headings
        display: ['64px', { lineHeight: '1.2', letterSpacing: '-0.02em' }],
        h1: ['56px', { lineHeight: '1.2', letterSpacing: '-0.02em' }],
        h2: ['36px', { lineHeight: '1.3', letterSpacing: '-0.02em' }],
        h3: ['24px', { lineHeight: '1.4', letterSpacing: '-0.01em' }],
        h4: ['20px', { lineHeight: '1.5' }],
        // Body text
        body: ['16px', { lineHeight: '1.65' }],
        small: ['14px', { lineHeight: '1.5' }],
        micro: ['13px', { lineHeight: '1.4' }],
      },
      spacing: {
        0: '0',
        1: '4px',
        2: '8px',
        3: '12px',
        4: '16px',
        5: '20px',
        6: '24px',
        8: '32px',
        10: '40px',
        12: '48px',
        16: '64px',
        20: '80px',
        24: '96px',
        32: '128px',
      },
      borderRadius: {
        card: '16px',
        pill: '999px',
        modal: '20px',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-glow': 'pulseGlow 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 1.5s infinite linear',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        pulseGlow: {
          '0%': { boxShadow: '0 0 0 0 var(--accent-glow)' },
          '70%': { boxShadow: '0 0 0 12px var(--accent-glow)' },
          '100%': { boxShadow: '0 0 0 0 var(--accent-glow)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
