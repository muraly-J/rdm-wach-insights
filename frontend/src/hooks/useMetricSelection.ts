import { useState } from 'react';

export function useMetricSelection(initialMetrics: string[] = ['power_total', 'power_factor_avg']) {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(initialMetrics);

  const toggleMetric = (key: string) => {
    setSelectedMetrics((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  return { selectedMetrics, setSelectedMetrics, toggleMetric };
}
