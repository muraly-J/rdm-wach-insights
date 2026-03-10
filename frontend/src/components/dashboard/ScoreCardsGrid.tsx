import React from 'react';
import ScoreCard from './ScoreCard';

interface ScoreCardsGridProps {
  scoreData: Record<string, { current: number; trend: number; data: any[] }>;
}

/**
 * ScoreCardsGrid - Grid of five score cards (Section 5.3)
 * 
 * Responsive: grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5
 */
const SCORE_NAMES = [
  {
    key: 'energy_anomaly',
    label: 'Energy Anomaly',
    info: 'How much more energy this AHU consumed vs its prediction (average of yesterday, last week, and two weeks ago). Large over-consumption relative to typical daily variation → high score. 0 = consuming as expected, 100 = far above baseline.',
  },
  {
    key: 'pf_degradation',
    label: 'PF Degradation',
    info: "Power factor measures how efficiently the motor converts electricity to mechanical work (ideal = 1.0). A drop below the AHU's historical average signals motor inefficiency or load issues. 0 = PF at or above baseline, 100 = severely degraded.",
  },
  {
    key: 'phase_imbalance',
    label: 'Phase Imbalance',
    info: "Three-phase motors need balanced current across all phases. Imbalance causes vibration, heat build-up, and early motor failure. Risk increases when current imbalance (%) significantly exceeds the AHU's normal operating range. 0 = balanced, 100 = severely imbalanced.",
  },
  {
    key: 'thd_drift',
    label: 'THD Drift',
    info: "Total Harmonic Distortion measures waveform distortion caused by non-linear loads like variable-frequency drives (VFDs). High THD stresses insulation and causes motor heating. Scored when THD drifts above the AHU's historical baseline. 0 = clean waveform, 100 = heavily distorted.",
  },
  {
    key: 'overload',
    label: 'Overload',
    info: "Compares current power draw to the AHU's historical 99th-percentile peak. Operating near or above peak capacity risks motor burnout and tripped breakers. 0 = well within capacity, 100 = exceeding historical peak.",
  },
];

const SCORE_COLORS = ['#00E5A0', '#00B8D4', '#7C5CFC', '#FF6B8A', '#FFB020'];

const ScoreCardsGrid: React.FC<ScoreCardsGridProps> = ({ scoreData }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6 mb-8">
      {SCORE_NAMES.map((score, index) => {
        const data = scoreData[score.key];
        
        if (!data) {
          return (
            <ScoreCard
              key={score.key}
              title={score.label}
              value={0}
              trendValue={0}
              data={[]}
              chartColor={SCORE_COLORS[index]}
              infoText={score.info}
            />
          );
        }

        return (
          <ScoreCard
            key={score.key}
            title={score.label}
            value={data.current}
            trendValue={data.trend}
            data={data.data}
            chartColor={SCORE_COLORS[index]}
            infoText={score.info}
          />
        );
      })}
    </div>
  );
};

export default ScoreCardsGrid;
