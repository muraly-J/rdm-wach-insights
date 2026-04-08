import { apiFetch } from './client';
import type { FinancialConfig, FinancialImpact } from '../types';

export async function fetchFinancialConfig(): Promise<FinancialConfig> {
  return apiFetch<FinancialConfig>('/financial-config');
}

export async function saveFinancialConfig(config: FinancialConfig): Promise<FinancialConfig> {
  return apiFetch<FinancialConfig>('/financial-config', {
    method: 'POST',
    body: JSON.stringify(config),
  });
}

export async function fetchFinancialImpact(
  level: number,
  range: '24h' | '7d' | '30d' | 'all' = '30d',
  deviceId?: string | null
): Promise<FinancialImpact> {
  const params = new URLSearchParams({ time_range: range });
  if (deviceId) params.set('device_id', deviceId);
  return apiFetch<FinancialImpact>(`/financial-impact?level=${level}&${params}`);
}
