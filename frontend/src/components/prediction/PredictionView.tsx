// frontend/src/components/prediction/PredictionView.tsx
import React from 'react';
import { fetchDeltaForecast } from '../../api/predictions';
import DeltaForecastChart from './DeltaForecastChart';
import type { DeltaForecastResponse } from '../../types';

interface PredictionViewProps {
  deviceId: string;
}

export default function PredictionView({ deviceId }: PredictionViewProps) {
  const [data, setData] = React.useState<DeltaForecastResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setLoading(true);
    setError(null);
    fetchDeltaForecast(deviceId)
      .then(setData)
      .catch((err: Error) => setError(err.message ?? 'Failed to load forecast'))
      .finally(() => setLoading(false));
  }, [deviceId]);

  if (loading) {
    return <div className="card p-6 h-48 animate-pulse bg-[#2a3649] rounded-xl" />;
  }

  if (error || !data) {
    return (
      <div className="card p-6 h-48 flex items-center justify-center">
        <span className="text-[#6d6e71] text-sm">Forecast unavailable</span>
      </div>
    );
  }

  return (
    <div className="mt-8">
      <DeltaForecastChart forecast={data.forecast} tNow={data.t_now} />
    </div>
  );
}
