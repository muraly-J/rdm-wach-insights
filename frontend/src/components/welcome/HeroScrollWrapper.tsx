import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import WelcomeHero from './WelcomeHero';

const HeroScrollWrapper: React.FC = () => {
  const wrapperRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: wrapperRef,
    offset: ['start start', 'end start'],
  });

  // "Collapse & drift to top-right" transforms
  const scale   = useTransform(scrollYProgress, [0, 0.9], [1, 0.08]);
  const x       = useTransform(scrollYProgress, [0, 0.9], ['0vw', '38vw']);
  const y       = useTransform(scrollYProgress, [0, 0.9], ['0vh', '-40vh']);
  const opacity = useTransform(scrollYProgress, [0.75, 0.95], [1, 0]);

  return (
    <div ref={wrapperRef} id="hero-region" style={{ height: '200vh' }}>
      <div style={{ position: 'sticky', top: 0, height: '100vh', overflow: 'hidden' }}>
        <motion.div
          style={{ scale, x, y, opacity, transformOrigin: 'center center' }}
          className="w-full h-full"
        >
          <WelcomeHero />
        </motion.div>
      </div>
    </div>
  );
};

export default HeroScrollWrapper;
