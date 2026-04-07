import React from 'react';

/**
 * FloatingParticles - Decorative background particles (Section 3.3)
 * 
 * 15-20 tiny circles (2-4px) scattered, each with slow CSS float animation
 * Color: accent at 20% opacity
 */
const FloatingParticles: React.FC = () => {
  // Generate static particle positions for consistent rendering
  const particles = React.useMemo(() => {
    return Array.from({ length: 18 }).map((_, i) => ({
      id: `particle-${i}`,
      top: `${10 + Math.random() * 80}%`,
      left: `${Math.random() * 100}%`,
      size: `${2 + Math.random() * 2}px`,
      delay: `${Math.random() * 5}s`,
      duration: `${6 + Math.random() * 4}s`,
    }));
  }, []);

  return (
    <>
      {particles.map((particle) => (
        <div
          key={particle.id}
          className="absolute rounded-full bg-[#4fbd95]"
          style={{
            top: particle.top,
            left: particle.left,
            width: particle.size,
            height: particle.size,
            opacity: 0.2,
            animation: `float ${particle.duration} ease-in-out infinite`,
            animationDelay: particle.delay,
          }}
        />
      ))}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
      `}</style>
    </>
  );
};

export default FloatingParticles;
