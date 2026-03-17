import React, { useState, useEffect } from 'react';
import RawScoreRelationChart from './RawScoreRelationChart';
import VariableSelector from '../../shared/VariableSelector';
import MetricMiniChart from '../../shared/MetricMiniChart';
import { fetchMeasurements } from '../../../api/client';
import { METRIC_META, MINI_CHART_COLORS } from '../../../constants/metricGroups';
import type { MetricOption, MeasurementPoint } from '../../../types';

interface ScoreCardWithSelectorProps {
  deviceId: string;
  scoreName: string;
  scoreKey: string;
  rawMetric: string;
  rawUnit: string;
  rawData: Array<{ timestamp: string; value: number }>;
  predictedData?: Array<{ timestamp: string; value: number }>;
  scoreData: Array<{ timestamp: string; value: number }>;
  chartColor: string;
  timeRange: '24h' | '7d' | '30d';
  availableMetrics: MetricOption[];
}

export default function ScoreCardWithSelector({
  deviceId, scoreName, scoreKey,
  rawMetric, rawUnit, rawData, predictedData, scoreData,
  chartColor, timeRange, availableMetrics,
}: ScoreCardWithSelectorProps) {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);
  const [measurements, setMeasurements] = useState<Record<string, MeasurementPoint[]>>({});
  const [loadingSet, setLoadingSet] = useState<Set<string>>(new Set());

  // Clear cache when timeRange or device changes
  useEffect(() => { setMeasurements({}); }, [timeRange, deviceId]);

  // Delta-fetch: only fetch metrics not yet cached
  useEffect(() => {
    const toFetch = selectedMetrics.filter((k) => !(k in measurements));
    if (!toFetch.length) return;

    setLoadingSet((prev) => new Set([...prev, ...toFetch]));

    fetchMeasurements(deviceId, toFetch, timeRange)
      .then((res) => {
        setMeasurements((prev) => ({ ...prev, ...res.measurements }));
      })
      .catch(console.error)
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
    <div className="min-w-[400px] w-[400px] md:min-w-[500px] md:w-[500px] flex flex-col">
      <RawScoreRelationChart
        scoreName={scoreName}
        rawMetric={rawMetric}
        rawUnit={rawUnit}
        rawData={rawData}
        predictedData={predictedData}
        scoreData={scoreData}
        chartColor={chartColor}
        timeRange={timeRange}
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
          loading={loadingSet.has(key)}
        />
      ))}
    </div>
  );
}
