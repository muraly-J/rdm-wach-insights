// frontend/src/api/predictions.ts
import { apiFetch } from './client';

export type PredictionMetric =
  | 'energy_import'
  | 'power_total'
  | 'power_factor_avg'
  | 'current_unbalance'
  | 'composite_thd';

export interface PredictionPoint {
  offset_hours: number;
  timestamp: string;
  energy_import: number | null;
  power_total: number | null;
  power_factor_avg: number | null;
  current_unbalance: number | null;
  composite_thd: number | null;
}

export interface HorizonResult {
  offset_hours: number;
  target_time: string;
  predictions: Partial<Record<PredictionMetric, number>>;
  delta_kwh: number;
  fair_scores: Record<string, number>;
  predicted_health_index: number;
}

export interface PredictionResponse {
  device_id: string;
  generated_at: string;
  t_now: string;
  history_profiles: {
    yesterday: PredictionPoint[];
    last_week: PredictionPoint[];
    two_weeks_ago: PredictionPoint[];
  };
  actuals: PredictionPoint[];
  horizons: Record<string, HorizonResult>;
}

export async function fetchPredictions(
  deviceId: string,
  horizons: string[] = ['1h', '12h', '24h', '168h']
): Promise<PredictionResponse> {
  return apiFetch<PredictionResponse>(
    `/predictions/${deviceId}?horizons=${horizons.join(',')}`
  );
}
