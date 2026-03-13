import React from 'react';
import { motion } from 'framer-motion';

import RawScoreRelationChart from './RawScoreRelationChart';
import { ScoreName } from '../../../types';

interface ScoreDerivationSectionProps {
  deviceName: string;
  rawData: Record<string, any>;
}

/**
 * ScoreDerivationSection - Shows raw data ↔ score relationship charts (Section 5.5)
 * 
 * Only renders in single-device mode
 * Lazy-loaded component
 */
const SCORE_NAMES: ScoreName[] = ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload'];

const SCORE_COLORS = ['#3B82F6', '#8B5CF6', '#F59E0B', '#10B981', '#EF4444'];

const RawScoreRelationChartLazy = React.lazy(async () => ({
  default: RawScoreRelationChart,
}));

const ScoreDerivationSection: React.FC<ScoreDerivationSectionProps> = ({
  deviceName,
  rawData,
}) => {
  // Raw metric mappings (matching FAIR score names)
  const rawMetrics: Record<string, { name: string; unit: string }> = {
    energy_anomaly:  { name: 'raw_energy_import',     unit: 'kWh' },
    pf_degradation:  { name: 'raw_power_factor_avg',   unit: ''    },
    phase_imbalance: { name: 'raw_current_unbalance',  unit: '%'   },
    thd_drift:       { name: 'raw_composite_thd',      unit: '%'   },
    overload:        { name: 'raw_power_total',         unit: 'kW'  },
  };

  return (
    <motion.div
      className="mb-8"
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Header (Section 5.5) */}
      <div className="mb-6">
        <h3
          className="
            font-display text-[24px] font-bold
            tracking-[-0.01em]
          "
        >
          Score Derivation — {deviceName}
        </h3>
        
        <p className="text-[#8A95A5] mt-2">
          Visualising how raw sensor data maps to computed scores over time.
        </p>
      </div>

      {/* Five chart panels (Section 5.5) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {SCORE_NAMES.map((score, index) => {
          const scoreData = rawData[score];
          
          if (!scoreData) {
            return null;
          }

          return (
            <React.Suspense
              key={score}
              fallback={
                <div className="card p-6 h-[240px] flex items-center justify-center">
                  <span className="text-[#8A95A5]">Loading relationship chart...</span>
                </div>
              }
            >
              {/* Check if data is empty and show appropriate UI */}
              {(() => {
                const isEmpty = !scoreData?.rawData?.length || !scoreData?.scoreData?.length;
                
                if (isEmpty) {
                  return (
                    <div className="card p-6 h-[240px] flex items-center justify-center bg-yellow-900/10 border border-yellow-700/30">
                      <div className="text-center max-w-[280px]">
                        <svg
                          className="w-10 h-10 mx-auto mb-2 text-yellow-500"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                          />
                        </svg>
                        <p className="text-yellow-500 font-semibold mb-1 text-sm">
                          No Data Available
                        </p>
                        <p className="text-[#8A95A5] text-xs leading-tight">
                          {rawMetrics[score]?.name || score}: No valid data points for the selected time range
                        </p>
                      </div>
                    </div>
                  );
                }

                return (
                  <RawScoreRelationChartLazy
                    scoreName={score.charAt(0).toUpperCase() + score.slice(1)}
                    rawMetric={rawMetrics[score]?.name || 'unknown'}
                    rawUnit={rawMetrics[score]?.unit || ''}
                    rawData={scoreData.rawData}
                    scoreData={scoreData.scoreData}
                    chartColor={SCORE_COLORS[index]}
                  />
                );
              })()}
            </React.Suspense>
          );
        })}
      </div>
    </motion.div>
  );
};

export default ScoreDerivationSection;
