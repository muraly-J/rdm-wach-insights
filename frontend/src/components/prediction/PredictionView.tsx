// frontend/src/components/prediction/PredictionView.tsx
import React, { useState, useEffect } from 'react';
import PredictionChart from './PredictionChart';
import DeltaBadge from './DeltaBadge';
import PredictionSkeleton from './PredictionSkeleton';
import { fetchPredictions, PredictionResponse, PredictionMetric } from '../../api/predictions';
import MeasurementHistoryChart from './MeasurementHistoryChart';
import VariableSelector from '../shared/VariableSelector';
import { fetchMeasurements } from '../../api/client';
import {
  ALL_SELECTABLE_METRICS, PREDICTION_CORE_METRICS, MINI_CHART_COLORS,
  METRIC_META,
} from '../../constants/metricGroups';
import type { MeasurementPoint } from '../../types';

const METRICS: { key: PredictionMetric; label: string }[] = [
  { key: 'energy_import', label: 'Energy' },
  { key: 'power_total', label: 'Power' },
  { key: 'power_factor_avg', label: 'PF' },
  { key: 'current_unbalance', label: 'Unbalance' },
  { key: 'composite_thd', label: 'THD' },
];

const HORIZONS = ['1h', '12h', '24h', '168h'];

interface PredictionViewProps {
  deviceId: string;
}

export default function PredictionView({ deviceId }: PredictionViewProps) {
  const [data, setData] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [metric, setMetric] = useState<PredictionMetric>('energy_import');
  const [error, setError] = useState<string | null>(null);
  const [extraMetrics, setExtraMetrics] = useState<string[]>([]);
  const [extraMeasurements, setExtraMeasurements] = useState<Record<string, MeasurementPoint[]>>({});
  const [loadingExtra, setLoadingExtra] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchPredictions(deviceId)
      .then(setData)
      .catch((e: Error) => setError(e.message ?? 'Failed to load predictions'))
      .finally(() => setLoading(false));
  }, [deviceId]);

  useEffect(() => {
    const toFetch = extraMetrics.filter((k) => !(k in extraMeasurements));
    if (!toFetch.length) return;
    setLoadingExtra(true);
    fetchMeasurements(deviceId, toFetch, '7d')
      .then((res) =>
        setExtraMeasurements((prev) => ({ ...prev, ...res.measurements }))
      )
      .catch(console.error)
      .finally(() => setLoadingExtra(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [extraMetrics]);

  // Clear when device changes
  useEffect(() => { setExtraMeasurements({}); }, [deviceId]);

  if (loading) return <PredictionSkeleton />;
  if (error) return (
    <div className="p-6 text-red-400 bg-[#131A23] rounded-xl border border-[#1E2A3A]">
      Predictions unavailable: {error}
    </div>
  );
  if (!data) return null;

  const horizon1h = data.horizons['1h'];

  return (
    <section id="prediction-section" className="w-full space-y-6 p-6 bg-[#131A23] rounded-xl border border-[#1E2A3A]">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-lg font-semibold text-white">
          Predictions — <span className="text-[#00E5A0] font-mono">{deviceId}</span>
        </h2>
        <div className="flex gap-2 flex-wrap items-center">
          {METRICS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setMetric(key)}
              className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                metric === key
                  ? 'border-[#00E5A0] bg-[#00E5A0]/10 text-[#00E5A0]'
                  : 'border-[#1E2A3A] text-[#8A95A5] hover:border-[#2A3A4A]'
              }`}
            >
              {label}
            </button>
          ))}
          <span className="w-px h-4 bg-[#1E2A3A]" />
          <VariableSelector
            availableMetrics={ALL_SELECTABLE_METRICS}
            selectedMetrics={extraMetrics}
            onChange={setExtraMetrics}
            maxSelectable={8}
            label="Add Measurements"
          />
        </div>
      </div>

      {horizon1h && (
        <DeltaBadge
          deltaKwh={horizon1h.delta_kwh}
          horizon="1h"
        />
      )}

      <PredictionChart data={data} metric={metric} />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {HORIZONS.map((h) => {
          const hd = data.horizons[h];
          if (!hd) return null;
          const hi = hd.predicted_health_index;
          const tierColor =
            hi >= 80 ? 'text-[#00E5A0]' :
            hi >= 60 ? 'text-yellow-400' :
            hi >= 40 ? 'text-orange-400' :
            'text-red-400';
          return (
            <div key={h} className="bg-[#0B0F14] rounded-lg p-4 border border-[#1E2A3A]">
              <div className="text-xs text-[#8A95A5] mb-1">+{h}</div>
              <div className={`text-2xl font-bold font-mono ${tierColor}`}>{hi.toFixed(0)}</div>
              <div className="text-xs text-[#8A95A5]">Health Index</div>
              <div className="mt-2 text-xs text-[#4A5568]">
                Δ {hd.delta_kwh >= 0 ? '+' : ''}{hd.delta_kwh.toFixed(1)} kWh
              </div>
            </div>
          );
        })}
      </div>

      {extraMetrics.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-xs font-medium text-[#4A5568] uppercase tracking-wider">
            Additional Measurements
          </h3>
          {extraMetrics.map((key, idx) => (
            <MeasurementHistoryChart
              key={key}
              label={METRIC_META[key]?.label ?? key}
              unit={METRIC_META[key]?.unit ?? ''}
              data={extraMeasurements[key] ?? []}
              color={MINI_CHART_COLORS[idx % MINI_CHART_COLORS.length]}
              loading={loadingExtra}
              isCoreMetric={PREDICTION_CORE_METRICS.has(key)}
              tNow={data?.t_now}
            />
          ))}
        </div>
      )}
    </section>
  );
}
