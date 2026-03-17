import React from 'react';
import { motion } from 'framer-motion';

import ScoreCardWithSelector from './ScoreCardWithSelector';
import { SCORE_METRIC_GROUPS } from '../../../constants/metricGroups';
import { ScoreName } from '../../../types';

interface ScoreDerivationSectionProps {
  deviceName: string;
  deviceId: string;
  rawData: Record<string, any>;
  timeRange: '24h' | '7d' | '30d';
}

/**
 * ScoreDerivationSection - Shows raw data ↔ score relationship charts (Section 5.5)
 *
 * Only renders in single-device mode
 * Lazy-loaded component
 * Netflix-style horizontal shelf layout for larger, more prominent charts
 */
const SCORE_NAMES: ScoreName[] = ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload'];

const SCORE_COLORS = ['#3B82F6', '#8B5CF6', '#F59E0B', '#10B981', '#EF4444'];

const ScoreDerivationSection: React.FC<ScoreDerivationSectionProps> = ({
  deviceName,
  deviceId,
  rawData,
  timeRange,
}) => {
  // Raw metric mappings (matching FAIR score names)
  // For energy_anomaly: raw_hourly_delta is the hourly energy consumption
  const rawMetrics: Record<string, { name: string; unit: string }> = {
    energy_anomaly:  { name: 'raw_hourly_delta',      unit: 'kWh' },
    pf_degradation:  { name: 'raw_power_factor_avg',   unit: ''    },
    phase_imbalance: { name: 'raw_current_unbalance',  unit: '%'   },
    thd_drift:       { name: 'raw_composite_thd',      unit: '%'   },
    overload:        { name: 'raw_power_total',         unit: 'kW'  },
  };

  return (
    <motion.div
      className="mb-12"
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Header (Section 5.5) */}
      <div className="mb-6">
        <h3
          className="
            font-display text-[28px] font-bold
            tracking-[-0.01em]
          "
        >
          Score Derivation — {deviceName}
        </h3>
        <p className="text-[#8A95A5] mt-2">
          Visualising how raw sensor data maps to computed scores over time.
        </p>
      </div>

      {/* Netflix-style Horizontal Shelf */}
      <div className="relative">
        {/* Scrollable Container */}
        <div
          className="
            flex gap-6 overflow-x-auto scrollbar-hidden
            px-4 md:px-8 lg:px-12
          "
        >
          {SCORE_NAMES.map((score, index) => {
            const scoreData = rawData[score];

            if (!scoreData) {
              return null;
            }

            return (
              <React.Suspense
                key={score}
                fallback={
                  <div className="min-w-[400px] w-[400px] md:min-w-[500px] md:w-[500px] card p-6 flex items-center justify-center h-[320px]">
                    <span className="text-[#8A95A5]">Loading...</span>
                  </div>
                }
              >
                {/* Check if data is empty and show appropriate UI */}
                {(() => {
                  const isEmpty = !scoreData?.rawData?.length || !scoreData?.scoreData?.length;
                  const group = SCORE_METRIC_GROUPS.find((g) => g.scoreKey === score);

                  if (isEmpty) {
                    return (
                      <div className="min-w-[400px] w-[400px] md:min-w-[500px] md:w-[500px] card p-6 flex items-center justify-center bg-yellow-900/10 border border-yellow-700/30">
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
                            {rawMetrics[score]?.name || score}: No valid data points
                          </p>
                        </div>
                      </div>
                    );
                  }

                  return (
                    <ScoreCardWithSelector
                      deviceId={deviceId}
                      scoreName={score.charAt(0).toUpperCase() + score.slice(1).replace(/_/g, ' ')}
                      scoreKey={score}
                      rawMetric={rawMetrics[score]?.name || 'unknown'}
                      rawUnit={rawMetrics[score]?.unit || ''}
                      rawData={scoreData.rawData}
                      predictedData={scoreData.predictedData}
                      scoreData={scoreData.scoreData}
                      chartColor={SCORE_COLORS[index]}
                      timeRange={timeRange}
                      availableMetrics={group?.availableMetrics ?? []}
                    />
                  );
                })()}
              </React.Suspense>
            );
          })}
        </div>
      </div>

      {/* Scroll Hint */}
      <p className="text-center text-[#8A95A5] text-xs mt-6 opacity-70">
        Scroll horizontally to explore all score derivation charts
      </p>
    </motion.div>
  );
};

export default ScoreDerivationSection;
