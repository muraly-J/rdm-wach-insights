import { motion } from 'framer-motion';
import DashboardControls from '../dashboard/DashboardControls';
import HamburgerMenu from './HamburgerMenu';
import { useAppStore } from '../../store/useAppStore';

interface SiteNavBarProps {
  devices: Array<{ id: string; name: string; label?: string; department?: string }>;
}

function HamburgerIcon() {
  return (
    <svg
      width="18"
      height="14"
      viewBox="0 0 18 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect y="0" width="18" height="2" rx="1" fill="#4fbd95" />
      <rect y="6" width="18" height="2" rx="1" fill="#4fbd95" />
      <rect y="12" width="18" height="2" rx="1" fill="#4fbd95" />
    </svg>
  );
}

export default function SiteNavBar({ devices }: SiteNavBarProps) {
  const toggleHamburger = useAppStore((s) => s.toggleHamburger);

  return (
    <>
      <div
        className="sticky top-0 z-30"
        style={{
          background: 'rgba(11,15,20,0.60)',
          backdropFilter: 'blur(20px) saturate(180%)',
          WebkitBackdropFilter: 'blur(20px) saturate(180%)',
          borderBottom: '1px solid rgba(255,255,255,0.07)',
          boxShadow: 'inset 0 -1px 0 rgba(255,255,255,0.04), 0 4px 24px rgba(0,0,0,0.30)',
        }}
      >
        <div
          style={{
            maxWidth: 1280,
            margin: '0 auto',
          }}
          className="px-4 sm:px-6 py-2.5 flex flex-row items-center justify-between"
        >
          {/* LEFT: Dashboard controls */}
          <DashboardControls devices={devices} />

          {/* RIGHT: Hamburger button */}
          <motion.button
            onClick={toggleHamburger}
            aria-label="Open navigation menu"
            whileHover={{ scale: 1.05, opacity: 0.8 }}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '6px 8px',
              fontSize: 20,
              color: '#4fbd95',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <HamburgerIcon />
          </motion.button>
        </div>
      </div>

      {/* Fixed-positioned drawer — does not affect layout */}
      <HamburgerMenu />
    </>
  );
}
