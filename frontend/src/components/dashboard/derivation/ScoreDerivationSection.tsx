import { motion } from 'framer-motion';
import React from 'react';

import { SCORE_METRIC_GROUPS } from '../../../constants/metricGroups';
import { ScoreName } from '../../../types';
import ScoreCardWithSelector from './ScoreCardWithSelector';

interface ScoreDerivationSectionProps {
  deviceName: string;
  deviceId: string;
  rawData: Record<string, any>;
  timeRange: '24h' | '7d' | '30d';
  healthChartData?: Array<{ timestamp?: string; is_on?: boolean; [key: string]: any }>;
}

/**
 * ScoreDerivationSection - Shows raw data ↔ score relationship charts (Section 5.5)
 *
 * Only renders in single-device mode
 * Lazy-loaded component
 * Netflix-style horizontal shelf layout for larger, more prominent charts
 */
const SCORE_NAMES: ScoreName[] = [
  'energy_anomaly',
  'pf_degradation',
  'phase_imbalance',
  'thd_drift',
  'overload',
];

const SCORE_COLORS = ['#3B82F6', '#8B5CF6', '#F59E0B', '#10B981', '#EF4444'];

const REFERENCE_LINES: Record<string, Array<{ value: number; label: string; color: string }>> = {
  thd_drift: [{ value: 5.0, label: 'IEEE 519: 5%', color: '#f9a020' }],
};

const ScoreDerivationSection: React.FC<ScoreDerivationSectionProps> = ({
  deviceName,
  deviceId,
  rawData,
  timeRange,
  healthChartData,
}) => {
  // Enrich all scoreData with is_on flags from healthChartData
  const enrichedRawData = React.useMemo(() => {
    if (!healthChartData?.length || !rawData) return rawData;

    const enriched: Record<string, any> = {};
    Object.entries(rawData).forEach(([key, value]) => {
      if (value && typeof value === 'object' && 'scoreData' in value) {
        enriched[key] = {
          ...value,
          scoreData: (value as any).scoreData.map((point: any, i: number) => ({
            ...point,
            is_on: healthChartData[i]?.is_on ?? true,
          })),
        };
      } else {
        enriched[key] = value;
      }
    });
    return enriched;
  }, [rawData, healthChartData]);

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
        <p className="text-[#6d6e71] mt-2">
          Visualising How Raw Sensor Data Maps to Computed Scores Over Time.
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
          {(() => {
            const hasAnyData = SCORE_NAMES.some((s) => enrichedRawData[s]);
            if (!hasAnyData) {
              return (
                <div
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '64px 32px',
                  }}
                >
                  <div style={{ textAlign: 'center', maxWidth: 360 }}>
                    <div
                      style={{
                        width: 56,
                        height: 56,
                        borderRadius: '50%',
                        background: 'rgba(0,229,160,0.06)',
                        border: '1px solid rgba(0,229,160,0.15)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        margin: '0 auto 16px',
                      }}
                    >
                      <svg
                        width="24"
                        height="24"
                        fill="none"
                        stroke="#00E5A0"
                        strokeWidth="1.5"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M3 13.5l5-5 4 4 5-5 4 4"
                        />
                      </svg>
                    </div>
                    <p style={{ fontSize: 14, fontWeight: 600, color: '#C8D4E0', marginBottom: 8 }}>
                      No Score Derivation Data
                    </p>
                    <p style={{ fontSize: 12, color: '#556677', lineHeight: 1.6 }}>
                      Raw sensor columns (energy, power factor, phase, THD, current) not yet
                      recorded for this device. Data will appear once the ingestion pipeline
                      populates these fields.
                    </p>
                  </div>
                </div>
              );
            }

            return SCORE_NAMES.map((score, index) => {
              const scoreData = enrichedRawData[score];

              if (!scoreData) {
                return (
                  <div
                    key={score}
                    className="min-w-[800px] w-[800px] md:min-w-[1000px] md:w-[1000px] card p-6 flex items-center justify-center"
                    style={{
                      background: 'rgba(0,229,160,0.02)',
                      border: '1px solid rgba(0,229,160,0.08)',
                    }}
                  >
                    <div style={{ textAlign: 'center', maxWidth: 280 }}>
                      <p
                        style={{ fontSize: 13, fontWeight: 600, color: '#445566', marginBottom: 4 }}
                      >
                        {score
                          .split('_')
                          .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                          .join(' ')}
                      </p>
                      <p style={{ fontSize: 11, color: '#334455' }}>
                        No Data Recorded for This Score
                      </p>
                    </div>
                  </div>
                );
              }

              const isEmpty = !scoreData?.series?.length || !scoreData?.scoreData?.length;
              const group = SCORE_METRIC_GROUPS.find((g) => g.scoreKey === score);

              if (isEmpty) {
                return (
                  <div
                    key={score}
                    className="min-w-[800px] w-[800px] md:min-w-[1000px] md:w-[1000px] card p-6 flex items-center justify-center bg-yellow-900/10 border border-yellow-700/30"
                  >
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
                      <p className="text-[#6d6e71] text-xs leading-tight">
                        {score}: No valid data points
                      </p>
                    </div>
                  </div>
                );
              }

              return (
                <ScoreCardWithSelector
                  key={score}
                  deviceId={deviceId}
                  scoreName={score
                    .split('_')
                    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                    .join(' ')}
                  scoreKey={score}
                  series={scoreData.series}
                  scoreData={scoreData.scoreData}
                  referenceLines={
                    scoreData.referenceLines?.length
                      ? scoreData.referenceLines
                      : (REFERENCE_LINES[score] ?? [])
                  }
                  chartColor={SCORE_COLORS[index]}
                  timeRange={timeRange}
                  availableMetrics={group?.availableMetrics ?? []}
                />
              );
            });
          })()}
        </div>
      </div>

      {/* Scroll Hint */}
      <p className="text-center text-[#6d6e71] text-xs mt-6 opacity-70">
        Scroll Horizontally to Explore All Score Derivation Charts
      </p>
    </motion.div>
  );
};

export default ScoreDerivationSection;
