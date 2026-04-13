import { useEffect, useState } from 'react';
import { fetchMeasurements } from '../../../api/client';
import { METRIC_META, MINI_CHART_COLORS } from '../../../constants/metricGroups';
import type {
  DerivationReferenceLine,
  DerivationSeries,
  MeasurementPoint,
  MetricOption,
  OffPeriod,
} from '../../../types';
import MetricMiniChart from '../../shared/MetricMiniChart';
import VariableSelector from '../../shared/VariableSelector';
import RawScoreRelationChart from './RawScoreRelationChart';

interface ScoreCardWithSelectorProps {
  deviceId: string;
  scoreName: string;
  scoreKey: string;
  series: DerivationSeries[];
  scoreData: Array<{ timestamp: string; value: number }>;
  referenceLines?: DerivationReferenceLine[];
  chartColor: string;
  timeRange: '24h' | '7d' | '30d';
  availableMetrics: MetricOption[];
  offPeriods?: OffPeriod[];
}

export default function ScoreCardWithSelector({
  deviceId,
  scoreName,
  scoreKey,
  series,
  scoreData,
  referenceLines,
  chartColor,
  timeRange,
  availableMetrics,
  offPeriods,
}: ScoreCardWithSelectorProps) {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);
  const [measurements, setMeasurements] = useState<Record<string, MeasurementPoint[]>>({});
  const [loadingSet, setLoadingSet] = useState<Set<string>>(new Set());

  // Clear cache when timeRange or device changes
  useEffect(() => {
    setMeasurements({});
  }, [timeRange, deviceId]);

  // Delta-fetch: only fetch metrics not yet cached
  useEffect(() => {
    const toFetch = selectedMetrics.filter((k) => !(k in measurements));
    if (!toFetch.length) return;

    setLoadingSet((prev) => new Set([...prev, ...toFetch]));

    fetchMeasurements(deviceId, toFetch, timeRange)
      .then((res) => {
        setMeasurements((prev) => ({ ...prev, ...res.measurements }));
      })
      .catch(() => {})
      .finally(() => {
        setLoadingSet((prev) => {
          const next = new Set(prev);
          toFetch.forEach((k) => next.delete(k));
          return next;
        });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMetrics]);

  return (
    <div className="min-w-[800px] w-[800px] md:min-w-[1000px] md:w-[1000px] flex flex-col">
      <RawScoreRelationChart
        scoreName={scoreName}
        series={series}
        scoreData={scoreData}
        referenceLines={referenceLines}
        chartColor={chartColor}
        timeRange={timeRange}
        offPeriods={offPeriods}
        headerAction={
          <VariableSelector
            availableMetrics={availableMetrics}
            selectedMetrics={selectedMetrics}
            onChange={setSelectedMetrics}
            maxSelectable={5}
            label="Add Variables"
          />
        }
      />

      {selectedMetrics.map((key, idx) => (
        <MetricMiniChart
          key={key}
          label={METRIC_META[key]?.label ?? key}
          unit={METRIC_META[key]?.unit ?? ''}
          data={measurements[key] ?? []}
          color={MINI_CHART_COLORS[idx % MINI_CHART_COLORS.length]}
          offPeriods={offPeriods}
          loading={loadingSet.has(key)}
        />
      ))}
    </div>
  );
}
