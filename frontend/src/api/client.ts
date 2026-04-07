// WACH Insight API Client
// ========================
// Fetch wrappers for all endpoints with error handling

import { LevelsResponse, HealthIndexResponse, ScoresResponse, MeasurementsResponse, SiteSummaryData } from '../types';

// API base URL (Vite proxy configuration in vite.config.js)
const API_BASE = '/api';

// Get API key from environment variable
const API_KEY = import.meta.env.VITE_API_KEY || 'dev-key-local-development';

/**
 * Generic fetch wrapper with error handling
 */
export async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${url}`, {
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${API_KEY}`,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`[API] Error fetching ${url}:`, error);
    throw error;
  }
}

/**
 * GET /api/levels — List available building levels
 * Spec: Section 9 data contract
 */
export async function fetchLevels(): Promise<LevelsResponse> {
  return apiFetch<LevelsResponse>('/levels');
}

/**
 * GET /api/level/{id}/devices — Static AHU device list for a level
 */
export async function fetchLevelDevices(levelId: number): Promise<{
  level: number;
  devices: Array<{ id: string; label: string; department: string; area: string }>;
}> {
  return apiFetch(`/level/${levelId}/devices`);
}

/**
 * GET /api/level/{id}/health-index — Health index time series
 */
export async function fetchHealthIndex(
  levelId: number,
  range: '24h' | '7d' | '30d',
  deviceId?: string | null
): Promise<HealthIndexResponse> {
  const params = new URLSearchParams({ time_range: range });
  if (deviceId && deviceId !== 'all') params.set('device_id', deviceId);
  return apiFetch<HealthIndexResponse>(`/level/${levelId}/health-index?${params}`);
}

/**
 * GET /api/level/{id}/scores — Five FAIR-score breakdown
 */
export async function fetchScoreBreakdown(
  levelId: number,
  range: '24h' | '7d' | '30d'
): Promise<ScoresResponse> {
  return apiFetch<ScoresResponse>(`/level/${levelId}/scores?time_range=${range}`);
}

/**
 * GET /api/device/{id}/raw-score-relationship — Raw data ↔ Score mapping
 * NEW: This endpoint does not exist yet - needs backend implementation
 */
export async function fetchRawScoreRelationship(
  deviceId: string,
  range: '24h' | '7d' | '30d'
): Promise<Record<string, unknown>> {
  return apiFetch(`/device/${deviceId}/raw-score-relationship?range=${range}`);
}

export interface NavigateTarget {
  level: number;
  device?: string;
  view?: 'prediction' | 'dashboard';
}

/**
 * POST /api/chat — Chat widget messaging
 */
export async function sendChatMessage(
  message: string,
  options?: {
    level?: number;
    device?: string | null;
    financial_impact?: number | null;
    history?: Array<{ role: 'user' | 'model'; content: string }>;
    persona?: string | null;
  }
) {
  const { history, persona, ...context } = options ?? {};
  return apiFetch<{ reply: string; navigate?: NavigateTarget | null }>('/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      context,
      history: history ?? [],
      persona: persona ?? null,
    }),
  });
}

/**
 * GET /api/dashboard/ranking — Top 5 best/worst AHUs by health index
 * Existing: backend/routes/dashboard.py#L24
 */
export async function fetchDashboardRanking(
  level: number,
  range: 'last_24h' | 'last_7d' | 'last_30d'
) {
  return apiFetch(`/dashboard/ranking?level=${level}&range=${range}`);
}

/**
 * GET /api/dashboard/safety-flags — Safety flags per device
 * Existing: backend/routes/dashboard.py#L631
 */
export async function fetchDashboardSafetyFlags(
  level: number,
  range: 'last_24h' | 'last_7d' | 'last_30d'
) {
  return apiFetch(`/dashboard/safety-flags?level=${level}&range=${range}`);
}

/**
 * GET /api/device/{id}/measurements — Raw metric time series for a device
 */
export async function fetchMeasurements(
  deviceId: string,
  metrics: string[],
  range: '24h' | '7d' | '30d'
): Promise<MeasurementsResponse> {
  const params = new URLSearchParams({ metrics: metrics.join(','), range });
  return apiFetch<MeasurementsResponse>(`/device/${deviceId}/measurements?${params}`);
}

/**
 * GET /api/site/summary — Site-wide aggregated summary across all levels
 */
export async function fetchSiteSummary(
  range: '24h' | '7d' | '30d' = '7d'
): Promise<SiteSummaryData> {
  return apiFetch<SiteSummaryData>(`/site/summary?range=${range}`);
}
