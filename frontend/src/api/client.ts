// WACH Insight API Client
// ========================
// Fetch wrappers for all endpoints with error handling

import { LevelsResponse, HealthIndexResponse, ScoresResponse } from '../types';

// API base URL (Vite proxy configuration in vite.config.js)
const API_BASE = '/api';

/**
 * Generic fetch wrapper with error handling
 */
async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${url}`, {
      headers: { 'Content-Type': 'application/json' },
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
 * GET /api/level/{id}/health-index — Health index time series (CSV-backed)
 */
export async function fetchHealthIndex(
  levelId: number,
  range: '24h' | '7d' | '30d',
  deviceId?: string | null
): Promise<HealthIndexResponse> {
  const params = new URLSearchParams({ time_range: range });
  if (deviceId) params.set('device_id', deviceId);
  return apiFetch<HealthIndexResponse>(`/level/${levelId}/health-index?${params}`);
}

/**
 * GET /api/level/{id}/scores — Five FAIR-score breakdown (CSV-backed)
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
) {
  // TODO: Implement backend endpoint
  return apiFetch(`/device/${deviceId}/raw-score-relationship?range=${range}`);
}

/**
 * POST /api/chat — Chat widget messaging
 * Spec: Section 6.4 chat backend integration
 */
export async function sendChatMessage(
  message: string,
  context?: { level?: number; device?: string | null }
) {
  return apiFetch<{ reply: string }>('/chat', {
    method: 'POST',
    body: JSON.stringify({ message, context }),
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
