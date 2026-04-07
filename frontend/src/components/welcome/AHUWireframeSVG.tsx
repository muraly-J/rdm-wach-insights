import React from 'react';

/**
 * AHUWireframeSVG - Faint wireframe outline of an AHU unit (Section 3.3)
 * 
 * Positioned absolute behind hero content, slightly rotated
 * Stroke: border-subtle, strokeWidth: 0.5, opacity: 20%
 */
const AHUWireframeSVG: React.FC = () => {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <svg
        viewBox="0 0 800 400"
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px]"
        style={{
          transform: 'rotate(-15deg) translate(-20%, -30%)',
          opacity: 0.2,
        }}
      >
        {/* AHU housing */}
        <rect
          x="100"
          y="100"
          width="600"
          height="200"
          fill="none"
          stroke="#2e3f55"
          strokeWidth="0.5"
        />
        
        {/* Internal components - fan section */}
        <circle cx="200" cy="200" r="40" fill="none" stroke="#2e3f55" strokeWidth="0.5" />
        <line x1="160" y1="200" x2="240" y2="200" stroke="#2e3f55" strokeWidth="0.5" />
        <line x1="200" y1="160" x2="200" y2="240" stroke="#2e3f55" strokeWidth="0.5" />
        
        {/* Filter section */}
        <rect
          x="320"
          y="120"
          width="80"
          height="160"
          fill="none"
          stroke="#2e3f55"
          strokeWidth="0.5"
        />
        
        {/* Coil section */}
        <rect
          x="480"
          y="130"
          width="60"
          height="140"
          fill="none"
          stroke="#2e3f55"
          strokeWidth="0.5"
        />
        
        {/* Duct connections */}
        <path
          d="M40 200 L100 200"
          fill="none"
          stroke="#2e3f55"
          strokeWidth="0.5"
        />
        <path
          d="M700 200 L760 200"
          fill="none"
          stroke="#2e3f55"
          strokeWidth="0.5"
        />
        
        {/* Labels */}
        <text
          x="400"
          y="80"
          textAnchor="middle"
          fill="#2e3f55"
          fontSize="14"
          fontFamily="monospace"
        >
          AHU UNIT
        </text>
      </svg>
    </div>
  );
};

export default AHUWireframeSVG;
