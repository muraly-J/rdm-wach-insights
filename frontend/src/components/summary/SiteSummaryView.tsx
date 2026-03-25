import { motion } from 'framer-motion';
import KPIStrip from './KPIStrip';
import SpotlightCards from './SpotlightCards';
import LevelHeatMap from './LevelHeatMap';
import TrendDeltas from './TrendDeltas';

export default function SiteSummaryView() {
  return (
    <motion.div
      className="max-w-[1280px] mx-auto px-4 sm:px-6 py-8"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Header */}
      <div style={{ marginBottom: '28px' }}>
        <h2
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: '20px',
            fontWeight: 700,
            color: '#E8ECF1',
            marginBottom: '4px',
          }}
        >
          Site Overview
        </h2>
        <p style={{ fontSize: '13px', color: '#8A95A5' }}>
          Select a level from the heat map below to drill into AHU health data.
        </p>
      </div>

      <KPIStrip />
      <SpotlightCards />
      <LevelHeatMap />
      <TrendDeltas />
    </motion.div>
  );
}
