import React from 'react';
import { motion } from 'framer-motion';

import FloatingParticles from './FloatingParticles';
import AHUWireframeSVG from './AHUWireframeSVG';
import CapabilityPills from './CapabilityPills';
import AHUCoverageDisclaimer from './AHUCoverageDisclaimer';

/**
 * WelcomeHero - Full-viewport section (Section 3.1)
 *
 * Liquid glass aesthetic: centered frosted glass panel over radial-gradient
 * mesh background with noise texture, wireframe AHU, and floating particles.
 *
 * Background: CSS radial-gradient mesh
 * Animated noise overlay with mix-blend-mode: overlay; opacity: 0.03
 */
export default function WelcomeHero({ onContinue }: { onContinue: () => void }) {
  return (
    <section className="relative h-full flex items-center justify-center overflow-hidden">
      {/* Radial gradient background mesh (Section 3.1) — z-index 0 */}
      <div
        className="absolute inset-0 z-0"
        style={{
          background: `radial-gradient(ellipse 60% 50% at 20% 30%, rgba(79,189,149,0.06), transparent),
                       radial-gradient(ellipse 50% 60% at 80% 70%, rgba(0,184,212,0.05), transparent),
                       #1c2431`,
        }}
      />

      {/* Noise texture overlay (Section 3.1) — z-index 0 */}
      <div className="noise-texture z-0" />

      {/* Faint wireframe AHU outline (Section 3.3) — behind glass */}
      <AHUWireframeSVG />

      {/* Floating particles (Section 3.3) — behind glass */}
      <FloatingParticles />

      {/* ── Centered glass panel ────────────────────────────────────────────── */}
      <div
        style={{
          position: 'relative',
          zIndex: 10,
          background: 'rgba(255,255,255,0.04)',
          backdropFilter: 'blur(40px) saturate(180%)',
          WebkitBackdropFilter: 'blur(40px) saturate(180%)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '28px',
          boxShadow:
            'inset 0 1px 0 rgba(255,255,255,0.10), inset 0 -1px 0 rgba(0,0,0,0.20), 0 32px 80px rgba(0,0,0,0.40), 0 0 0 1px rgba(79,189,149,0.06)',
          padding: '56px 64px',
          maxWidth: '680px',
          width: '90%',
        }}
      >
        {/* Iridescent caustic overlay — absolute, pointer-events none */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: 'inherit',
            background:
              'radial-gradient(ellipse 120% 60% at 10% 0%, rgba(124,92,252,0.08), transparent 50%), radial-gradient(ellipse 80% 80% at 90% 100%, rgba(0,184,212,0.06), transparent 50%)',
            pointerEvents: 'none',
          }}
        />

        {/* Content — positioned relative so it sits above the caustic overlay */}
        <div className="relative flex flex-col items-center text-center">
          {/* Logo / wordmark (Section 3.2) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="mb-6"
          >
            <span
              className="font-display text-[20px] uppercase tracking-[0.15em] text-[#4fbd95]"
            >
              ✦ WACH-INSIGHT
            </span>
          </motion.div>

          {/* Main heading (Section 3.2) */}
          <motion.h1
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
            className="font-display text-[32px] sm:text-[56px] font-bold leading-tight tracking-[-0.02em]"
          >
            Intelligent AHU Health <br className="hidden sm:block" />
            Monitoring
          </motion.h1>

          {/* Sub-heading (Section 3.2) */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="mt-4 text-[15px] sm:text-[18px] text-[#6d6e71] max-w-[600px] mx-auto"
          >
            Real-time health scoring, trend analysis, and anomaly detection for your air handling units —
            across every level of your building.
          </motion.p>

          {/* Capability pills (Section 3.2) */}
          <CapabilityPills />

          {/* Limitations disclaimer (Section 3.2) */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="mt-8 text-[14px] text-[#6d6e71] italic"
          >
            Note: Scores are model-derived estimates and should complement — not replace — physical inspections.
          </motion.p>

          {/* AHU coverage gap disclaimer */}
          <AHUCoverageDisclaimer />

          {/* Continue glass pill button (replaces ScrollCTA) */}
          <motion.button
            onClick={onContinue}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            className="welcome-cta-btn"
            style={{
              marginTop: '40px',
              padding: '14px 40px',
              background: 'rgba(79,189,149,0.12)',
              border: '1px solid rgba(79,189,149,0.40)',
              borderRadius: '999px',
              color: '#4fbd95',
              fontSize: '15px',
              fontWeight: 600,
              fontFamily: 'var(--font-display)',
              letterSpacing: '0.04em',
              backdropFilter: 'blur(8px)',
              WebkitBackdropFilter: 'blur(8px)',
              cursor: 'pointer',
              boxShadow: '0 0 0px rgba(79,189,149,0)',
              transition: 'box-shadow 0.2s ease',
            }}
          >
            Continue →
          </motion.button>
        </div>
      </div>
    </section>
  );
}
