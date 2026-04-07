import type { Config } from 'tailwindcss';

export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#1c2431',
          secondary: '#222d3d',
          tertiary: '#2a3649',
        },
        border: {
          subtle: '#2e3f55',
          accent: '#4fbd95',
        },
        text: {
          primary: '#E8ECF1',
          secondary: '#6d6e71',
        },
        accent: {
          DEFAULT: '#4fbd95',
          glow: 'rgba(79, 189, 149, 0.15)',
          secondary: '#00a9a5',
        },
        danger: '#e96852',
        warning: '#f9a020',
        success: '#4fbd95',
        chart: {
          1: '#4fbd95',
          2: '#00a9a5',
          3: '#00aeef',
          4: '#9ccb3d',
          5: '#f9a020',
        },
        // Brand palette
        brand: {
          teal: '#4fbd95',
          grey: '#6d6e71',
          lime: '#9ccb3d',
          aqua: '#00a9a5',
          cyan: '#00aeef',
          navy: '#1c2431',
          amber: '#f9a020',
          coral: '#e96852',
        },
      },
      fontFamily: {
        display: ['Montserrat', 'Verdana', 'sans-serif'],
        headings: ['Montserrat', 'Verdana', 'sans-serif'],
        body: ['Montserrat', 'Verdana', 'sans-serif'],
        mono: ['Oswald', 'Verdana', 'monospace'],
      },
      fontSize: {
        display: ['64px', { lineHeight: '1.2', letterSpacing: '0' }],
        h1: ['56px', { lineHeight: '1.2', letterSpacing: '0.025em' }],
        h2: ['36px', { lineHeight: '1.3', letterSpacing: '0.15em' }],
        h3: ['24px', { lineHeight: '1.4', letterSpacing: '0' }],
        h4: ['20px', { lineHeight: '1.5', letterSpacing: '0' }],
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
