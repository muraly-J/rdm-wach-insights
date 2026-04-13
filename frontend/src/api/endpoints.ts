// WACH Insight API Endpoints
// ==========================
// Centralized path constants for all backend endpoints

export const ENDPOINTS = {
  // Levels
  LEVELS: '/levels',

  // Dashboard (existing routes)
  DASHBOARD_RANKING: (level: number, range: string) =>
    `/dashboard/ranking?level=${level}&range=${range}`,
  DASHBOARD_TREND: (level: number, range: string) =>
    `/dashboard/trend?level=${level}&range=${range}`,
  DASHBOARD_SUMMARY: (level: number, range: string, ahuId?: string) =>
    `/dashboard/summary?level=${level}&range=${range}${ahuId ? `&ahu_id=${ahuId}` : ''}`,

  // Forecast (existing routes)
  FORECAST: (deviceId: string) => `/forecast/${deviceId}`,

  // New endpoints for UI revamp
  HEALTH_INDEX: (levelId: number, deviceId: string | null, range: string) =>
    `/level/${levelId}/health-index?time_range=${range}${deviceId ? `&device_id=${deviceId}` : ''}`,
  SCORE_BREAKDOWN: (levelId: number, range: string) =>
    `/level/${levelId}/scores?time_range=${range}`,
  RAW_SCORE_RELATIONSHIP: (deviceId: string, range: string) =>
    `/device/${deviceId}/raw-score-relationship?range=${range}`,

  // Chat
  CHAT: '/chat',

  // Query (existing LLM route)
  QUERY: '/query',
} as const;

// Type-safe endpoint keys
export type ApiEndpoint = keyof typeof ENDPOINTS;
