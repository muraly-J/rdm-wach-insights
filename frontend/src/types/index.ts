// WACH Insight Types
// ==================
// Derived from WACH_INSIGHT_UI_REVAMP_PLAN.md Section 8 & 9

export type ScoreName =
  | 'energy_anomaly'
  | 'pf_degradation'
  | 'phase_imbalance'
  | 'thd_drift'
  | 'overload';

export type ScoreDataPoint = {
  timestamp: string;
  value: number;
};

export interface TimeSeriesData {
  timestamp: string;
  value: number;
}

export interface ScoreWithTrend {
  current: number;
  trend: number; // percentage change vs previous period
  data: ScoreDataPoint[];
}

export interface ScoreBreakdown {
  [key: string]: ScoreWithTrend;
}

export interface Device {
  id: string;
  name: string;
  level: number;
}

export interface HealthIndexData {
  device: Device;
  data: TimeSeriesData[];
}

export interface DashboardData {
  healthIndex: HealthIndexData[];
  scores: Record<ScoreName, TimeSeriesData[]>;
  devices: Device[];
  rawData: Record<string, TimeSeriesData[]>; // per-device only
}

// State Interface (from spec Section 8.1)
export interface AppState {
  selectedLevel: number | null;         // null = no level selected yet
  selectedDevice: string | null;        // null = "All AHUs"
  chatOpen: boolean;
  chatMessages: ChatMessage[];
  dashboardData: DashboardData | null;
  isLoading: boolean;
}

// Chat types (from spec Section 6)
export interface ChatMessage {
  id: string;
  role: 'user' | 'bot';
  content: string;
  timestamp: Date;
}

// API Response Types (from spec Section 9)
export interface LevelsResponse {
  levels: number[];
}

export interface HealthIndexResponse {
  devices: {
    id: string;
    name: string;
    data: { timestamp: string; value: number }[];
  }[];
}

export interface ScoresResponse {
  devices: {
    id: string;
    name: string;
    scores: Record<
      'energy_anomaly' | 'pf_degradation' | 'phase_imbalance' | 'thd_drift' | 'overload',
      { current: number; trend: number; data: { timestamp: string; value: number }[] }
    >;
  }[];
}

export interface RawScoreResponse {
  scores: Record<
    string,
    {
      rawMetric: string;
      rawUnit: string;
      rawData: { timestamp: string; value: number }[];
      scoreData: { timestamp: string; value: number }[];
    }
  >;
}
