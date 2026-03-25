import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';

interface NavItem {
  label: string;
  sectionId: string;
  alwaysVisible?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Home', sectionId: 'hero-region', alwaysVisible: true },
  { label: 'Health Index', sectionId: 'section-health-index' },
  { label: 'Health Rankings', sectionId: 'section-rankings' },
  { label: 'Score Derivation', sectionId: 'section-score-derivation' },
  { label: 'Predicted Hourly Consumption', sectionId: 'section-predictions' },
  { label: 'Financial Impact', sectionId: 'section-financial' },
];

const drawerEase = [0.22, 1, 0.36, 1] as const;

export default function HamburgerMenu() {
  const hamburgerOpen = useAppStore((s) => s.hamburgerOpen);
  const toggleHamburger = useAppStore((s) => s.toggleHamburger);
  const selectedLevel = useAppStore((s) => s.selectedLevel);

  React.useEffect(() => {
    if (!hamburgerOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') toggleHamburger();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [hamburgerOpen, toggleHamburger]);

  function handleNavClick(sectionId: string) {
    document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    toggleHamburger();
  }

  const visibleItems = NAV_ITEMS.filter(
    (item) => item.alwaysVisible || selectedLevel !== null,
  );

  return (
    <AnimatePresence>
      {hamburgerOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            key="hamburger-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={toggleHamburger}
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 40,
              background: 'rgba(0,0,0,0.5)',
            }}
          />

          {/* Drawer */}
          <motion.aside
            key="hamburger-drawer"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.3, ease: drawerEase }}
            role="dialog"
            aria-modal={true}
            aria-label="Navigation menu"
            style={{
              position: 'fixed',
              top: 0,
              right: 0,
              bottom: 0,
              zIndex: 50,
              width: 260,
              background: 'rgba(11,15,20,0.97)',
              backdropFilter: 'blur(20px)',
              borderLeft: '1px solid #1E2A3A',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Accent line at top */}
            <div
              style={{
                height: 2,
                background: '#00E5A0',
                flexShrink: 0,
              }}
            />

            {/* Header row with close button */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                padding: '16px 16px 8px',
                flexShrink: 0,
              }}
            >
              <motion.button
                onClick={toggleHamburger}
                aria-label="Close menu"
                whileHover={{ color: '#E8ECF1', scale: 1.1 }}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#8A95A5',
                  fontSize: 20,
                  lineHeight: 1,
                  padding: '4px 6px',
                  borderRadius: 6,
                }}
              >
                ✕
              </motion.button>
            </div>

            {/* Nav items */}
            <nav
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: '4px 12px 16px',
                display: 'flex',
                flexDirection: 'column',
                gap: 2,
              }}
            >
              {visibleItems.map((item, index) => (
                <motion.button
                  key={item.sectionId}
                  initial={{ opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05, duration: 0.2 }}
                  onClick={() => handleNavClick(item.sectionId)}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: '12px 12px',
                    borderRadius: 8,
                    fontSize: 14,
                    fontWeight: 500,
                    color: '#E8ECF1',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    fontFamily: 'DM Sans, sans-serif',
                  }}
                  whileHover={{ backgroundColor: '#1A2230', color: '#00E5A0' }}
                >
                  {item.label}
                </motion.button>
              ))}
            </nav>

            {/* Bottom wordmark */}
            <div
              style={{
                padding: '12px 16px 20px',
                flexShrink: 0,
                borderTop: '1px solid #1E2A3A',
              }}
            >
              <span
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 11,
                  fontWeight: 600,
                  letterSpacing: '0.12em',
                  color: '#1E2A3A',
                  userSelect: 'none',
                }}
              >
                WACH-INSIGHT
              </span>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
