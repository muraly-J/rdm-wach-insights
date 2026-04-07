import React from 'react';
import ScoreCard from './ScoreCard';
import SafetyFlagCard from './SafetyFlagCard';

interface ScoreCardsGridProps {
  scoreData: Record<string, { current: number; trend: number; data: any[] }>;
}

const SCORE_NAMES = [
  {
    key: 'energy_anomaly',
    label: 'Energy Anomaly',
    info: (
      <div className="space-y-2.5">
        <p className="text-[#E8ECF1] font-semibold text-[11px]">Energy Anomaly Score (weight 15%)</p>
        <p>Detects over-consumption vs a seasonal-naive baseline derived from the same hour on D−1, D−7, and D−14.</p>
        <div>
          <p className="text-[#E8ECF1] font-medium mb-1">Formula</p>
          <p className="font-mono bg-[#1c2431] rounded px-2 py-1 text-[10px]">
            excess = kWh_actual − mean(kWh_D-1, D-7, D-14)<br/>
            score = clip(excess / σ_baseline, 0, 1) × 100
          </p>
        </div>
        <div>
          <p className="text-[#E8ECF1] font-medium mb-1">Standard</p>
          <p>ISO 50001:2018 §6.4 (energy baseline &amp; EnPIs) · ASHRAE 90.1-2022 (energy monitoring)</p>
        </div>
        <p className="text-[#4A5568] text-[10px]">0 = consuming as expected · 100 = far above seasonal baseline</p>
      </div>
    ),
  },
  {
    key: 'pf_degradation',
    label: 'PF Degradation',
    info: (
      <div className="space-y-2.5">
        <p className="text-[#E8ECF1] font-semibold text-[11px]">Power Factor Degradation Score (weight 25%)</p>
        <p>Measures drop in power factor from the AHU's own historical average. Low PF means reactive power waste and TNB surcharges.</p>
        <div>
          <p className="text-[#E8ECF1] font-medium mb-1">Formula</p>
          <p className="font-mono bg-[#1c2431] rounded px-2 py-1 text-[10px]">
            PF = P / S = P / √(P² + Q²)<br/>
            score = clip((PF_baseline − PF_now) / PF_baseline, 0, 1) × 100
          </p>
        </div>
        <div>
          <p className="text-[#E8ECF1] font-medium mb-1">Standards &amp; Targets</p>
          <p>IEEE 1459-2010 (PF definition) · TNB tariff: PF &lt; 0.85 triggers 1.5%/0.01 surcharge · ASHRAE 180-2012 HVAC target: PF &gt; 0.90</p>
        </div>
        <p className="text-[#4A5568] text-[10px]">0 = PF at or above baseline · 100 = severely degraded</p>
      </div>
    ),
  },
  {
    key: 'phase_imbalance',
    label: 'Phase Imbalance',
    info: (
      <div className="space-y-2.5">
        <p className="text-[#E8ECF1] font-semibold text-[11px]">Phase Imbalance Score (weight 25%)</p>
        <p>Unbalanced current across L1/L2/L3 causes torque ripple, heat, and premature motor failure. Scored relative to this AHU's normal operating band.</p>
        <div>
          <p className="text-[#E8ECF1] font-medium mb-1">Formula (NEMA definition)</p>
          <p className="font-mono bg-[#1c2431] rounded px-2 py-1 text-[10px]">
            imbalance = max|Iₙ − Iₐᵥg| / Iₐᵥg × 100%<br/>
            score = clip((imbalance − μ) / σ_baseline, 0, 1) × 100
          </p>
        </div>
        <div>
          <p className="text-[#E8ECF1] font-medium mb-1">Standards</p>
          <p>NEMA MG-1 Part 14: derate motor if voltage unbalance &gt; 1%; current unbalance typically 6–10× higher · IEC 60034-26: unbalance &gt; 2% causes measurable efficiency loss</p>
        </div>
        <p className="text-[#4A5568] text-[10px]">0 = balanced · 100 = severely imbalanced</p>
      </div>
    ),
  },
  {
    key: 'thd_drift',
    label: 'THD Drift',
    info: (
      <div className="space-y-2.5">
        <p className="text-[#E8ECF1] font-semibold text-[11px]">THD Drift Score (weight 15%)</p>
        <p>Waveform distortion from VFDs and non-linear loads. High THD stresses winding insulation and causes additional heat. Scored when current THD drifts above this AHU's historical baseline.</p>
        <div>
          <p className="text-[#E8ECF1] font-medium mb-1">Formula</p>
          <p className="font-mono bg-[#1c2431] rounded px-2 py-1 text-[10px]">
            THD = √(I₂² + I₃² + … + Iₙ²) / I₁ × 100%<br/>
            score = clip((THD_now − μ_baseline) / σ_baseline, 0, 1) × 100
          </p>
        </div>
        <div>
          <p className="text-[#E8ECF1] font-medium mb-1">Standards</p>
          <p>IEEE 519-2022: voltage THD &lt; 5% at PCC; current THD limits depend on I_sc/I_L ratio · IEC 61000-3-2: harmonic current limits for equipment</p>
        </div>
        <p className="text-[#4A5568] text-[10px]">0 = clean waveform · 100 = heavily distorted above baseline</p>
      </div>
    ),
  },
  {
    key: 'overload',
    label: 'Overload',
    info: (
      <div className="space-y-2.5">
        <p className="text-[#E8ECF1] font-semibold text-[11px]">Overload Score (weight 20%)</p>
        <p>Compares current power draw to this AHU's historical 99th-percentile peak. Sustained operation near capacity risks motor burnout and tripped breakers.</p>
        <div>
          <p className="text-[#E8ECF1] font-medium mb-1">Formula</p>
          <p className="font-mono bg-[#1c2431] rounded px-2 py-1 text-[10px]">
            ratio = P_now / P_99th_percentile<br/>
            score = clip((ratio − 0.8) / 0.2, 0, 1) × 100
          </p>
        </div>
        <div>
          <p className="text-[#E8ECF1] font-medium mb-1">Standards</p>
          <p>IEC 60947-4-1: motor protection relay classes · NEMA MG-1: motors rated at 100% FLA continuous; service factor &lt; 1.15 above nameplate · IEC 60364-4-43: overcurrent protection coordination</p>
        </div>
        <p className="text-[#4A5568] text-[10px]">0 = well within capacity · 100 = at or above historical peak</p>
      </div>
    ),
  },
];

const SCORE_COLORS = ['#4fbd95', '#00a9a5', '#00aeef', '#e96852', '#f9a020'];

const ScoreCardsGrid: React.FC<ScoreCardsGridProps> = ({ scoreData }) => {
  // Find the score with the highest current value for the safety flag card
  const topScore = React.useMemo(() => {
    let highest: { score: (typeof SCORE_NAMES)[number]; index: number } | null = null;
    SCORE_NAMES.forEach((score, index) => {
      const data = scoreData[score.key];
      if (!data) return;
      if (!highest || data.current > (scoreData[highest.score.key]?.current ?? 0)) {
        highest = { score, index };
      }
    });
    return highest;
  }, [scoreData]);

  const renderCard = (score: (typeof SCORE_NAMES)[number], index: number) => {
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
  };

  return (
    <div className="mb-8">
      {/* === MOBILE / TABLET: simple 1-col → 2-col grid === */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 lg:hidden">
        {SCORE_NAMES.map((score, index) => (
          <div key={score.key}>
            {renderCard(score, index)}
          </div>
        ))}
        {topScore && scoreData[topScore.score.key] && (
          <div className="sm:col-span-2">
            <SafetyFlagCard
              title={topScore.score.label}
              value={scoreData[topScore.score.key]!.current}
              trend={scoreData[topScore.score.key]!.trend}
              info={topScore.score.info}
              chartColor={SCORE_COLORS[topScore.index]}
              data={scoreData[topScore.score.key]!.data}
            />
          </div>
        )}
      </div>

      {/* === DESKTOP: original 6-col centered layout (unchanged) === */}
      <div className="hidden lg:block">
        {/* Row 1: 3 cards */}
        <div className="grid grid-cols-6 gap-6 mb-6">
          {SCORE_NAMES.slice(0, 3).map((score, index) => (
            <div key={score.key} className="col-span-2">
              {renderCard(score, index)}
            </div>
          ))}

          {/* Row 2: 2 cards centered */}
          <div className="col-span-1" />
          {SCORE_NAMES.slice(3, 5).map((score, index) => (
            <div key={score.key} className="col-span-2">
              {renderCard(score, index + 3)}
            </div>
          ))}
          <div className="col-span-1" />
        </div>

        {/* Row 3: Safety flag card centered */}
        {topScore && scoreData[topScore.score.key] && (
          <div className="grid grid-cols-6 gap-6">
            <div className="col-span-1" />
            <div className="col-span-4">
              <SafetyFlagCard
                title={topScore.score.label}
                value={scoreData[topScore.score.key]!.current}
                trend={scoreData[topScore.score.key]!.trend}
                info={topScore.score.info}
                chartColor={SCORE_COLORS[topScore.index]}
                data={scoreData[topScore.score.key]!.data}
              />
            </div>
            <div className="col-span-1" />
          </div>
        )}
      </div>
    </div>
  );
};

export default ScoreCardsGrid;
