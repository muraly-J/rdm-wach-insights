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
  { key: 'energy_anomaly',  label: 'Energy Anomaly'  },
  { key: 'pf_degradation',  label: 'PF Degradation'  },
  { key: 'phase_imbalance', label: 'Phase Imbalance' },
  { key: 'thd_drift',       label: 'THD Drift'       },
  { key: 'overload',        label: 'Overload'        },
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
          />
        );
      })}
    </div>
  );
};

export default ScoreCardsGrid;
