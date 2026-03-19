import React from 'react';
import { motion } from 'framer-motion';

import FloatingParticles from './FloatingParticles';
import AHUWireframeSVG from './AHUWireframeSVG';
import CapabilityPills from './CapabilityPills';
import ScrollCTA from './ScrollCTA';

/**
 * WelcomeHero - Full-viewport section (Section 3.1)
 * 
 * Background: CSS radial-gradient mesh
 * Animated noise overlay with mix-blend-mode: overlay; opacity: 0.03
 */
const WelcomeHero: React.FC = () => {
  return (
    <section className="relative h-screen flex items-center justify-center overflow-hidden">
      {/* Radial gradient background mesh (Section 3.1) */}
      <div
        className="absolute inset-0 z-0"
        style={{
          background: `radial-gradient(ellipse 60% 50% at 20% 30%, rgba(0,229,160,0.06), transparent),
                       radial-gradient(ellipse 50% 60% at 80% 70%, rgba(0,184,212,0.05), transparent),
                       #0B0F14`,
        }}
      />

      {/* Noise texture overlay (Section 3.1) */}
      <div className="noise-texture z-0" />

      {/* Faint wireframe AHU outline (Section 3.3) */}
      <AHUWireframeSVG />

      {/* Floating particles (Section 3.3) */}
      <FloatingParticles />

      {/* Content container */}
      <div className="relative z-10 flex flex-col items-center text-center px-4 max-w-5xl">
        {/* Logo / wordmark (Section 3.2) */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="mb-6"
        >
          <span
            className="
              font-display text-[20px] uppercase tracking-[0.15em]
              text-[#00E5A0]
            "
          >
            WACH-INSIGHT
          </span>
        </motion.div>

        {/* Main heading (Section 3.2) */}
        <motion.h1
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="
            font-display text-[56px] font-bold leading-tight
            tracking-[-0.02em]
          "
        >
          Intelligent AHU Health <br className="hidden sm:block" />
          Monitoring
        </motion.h1>

        {/* Sub-heading (Section 3.2) */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="
            mt-4 text-[18px]
            text-[#8A95A5]
            max-w-[600px] mx-auto
          "
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
          className="
            mt-8 text-[14px]
            text-[#8A95A5] italic
          "
        >
          Note: Scores are model-derived estimates and should complement — not replace — physical inspections.
        </motion.p>
      </div>

      {/* Scroll CTA (Section 3.2) */}
      <ScrollCTA />
    </section>
  );
};

export default WelcomeHero;
