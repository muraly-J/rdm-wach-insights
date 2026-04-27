// WACH Insight Types
// ==================
// Derived from WACH_INSIGHT_UI_REVAMP_PLAN.md Section 8 & 9

export type OperationalState = 'On' | 'Off' | 'Off_Stale' | 'Inactive';

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
  label?: string;
  department?: string;
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
  selectedLevel: number | null; // null = no level selected yet
  selectedDevice: string | null; // null = "All AHUs"
  chatOpen: boolean;
  chatMessages: ChatMessage[];
  dashboardData: DashboardData | null;
  isLoading: boolean;
  heroVisible: boolean; // Hero overlay visibility (not persisted)
  workOrderPanelOpen?: boolean; // Work order slide-out panel visibility
  workOrderDraftsCount?: number; // Count of draft work orders
}

// Chat types (from spec Section 6)
export interface NavigateTarget {
  level: number;
  device?: string;
  view?: 'dashboard' | 'prediction';
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'bot';
  content: string;
  timestamp: Date;
  navigate?: NavigateTarget | null;
}

// API Response Types (from spec Section 9)
export interface LevelsResponse {
  levels: number[];
}

export interface HealthIndexResponse {
  devices: {
    id: string;
    name: string;
    label?: string;
    department?: string;
    area?: string;
    is_on?: boolean;
    data: { timestamp: string; value: number; is_on?: boolean }[];
  }[];
}

export interface ScoresResponse {
  devices: {
    id: string;
    name: string;
    label?: string;
    department?: string;
    scores: Record<
      'energy_anomaly' | 'pf_degradation' | 'phase_imbalance' | 'thd_drift' | 'overload',
      { current: number; trend: number; data: { timestamp: string; value: number }[] }
    >;
  }[];
}

export interface DerivationSeries {
  col: string;
  label: string;
  unit: string;
  style: 'solid' | 'dashed' | 'bold' | 'ref';
  group?: string;
  data: Array<{ timestamp: string; value: number }>;
}

export interface DerivationReferenceLine {
  value: number;
  label: string;
  color: string;
}

export interface ScoreDerivation {
  series: DerivationSeries[];
  scoreData: Array<{ timestamp: string; value: number }>;
  referenceLines?: DerivationReferenceLine[];
}

export interface RawScoreResponse {
  [scoreKey: string]: ScoreDerivation;
}

// ──────────────────────────────────────────────────────────────────────────────
// Ranking Types (for ExpandableHealthRankings)
// ──────────────────────────────────────────────────────────────────────────────

export interface DeviceRank {
  ahu_id: string;
  index: number; // health index (0-100)
  tier?: string;
  level?: string;
  operational_state?: OperationalState;
  last_on_timestamp?: string | null;
}

export interface RankingResponse {
  level: number | string;
  time_range: string;
  snapshot_time?: string;
  best: DeviceRank[];
  worst: DeviceRank[];
}

// ── Measurements API (variable selector) ─────────────────────────────────────

export interface MeasurementPoint {
  timestamp: string;
  value: number;
}

export interface MeasurementsResponse {
  device_id: string;
  range: string;
  measurements: Record<string, MeasurementPoint[]>;
}

export interface MetricOption {
  key: string;
  label: string;
  unit: string;
  description: string;
}

export interface ScoreMetricGroup {
  scoreKey: string;
  scoreLabel: string;
  availableMetrics: MetricOption[];
}

// ── Delta Forecast Types ──────────────────────────────────────────────────────

export interface DeltaForecastPoint {
  hour: number;
  target_time: string;
  predicted_delta_kwh: number | null;
}

export interface DeltaForecastResponse {
  device_id: string;
  generated_at: string;
  t_now: string;
  forecast: DeltaForecastPoint[];
}

// ── Financial Impact Types ────────────────────────────────────────────────────

export interface FinancialConfig {
  currency: string;
  tariff_rate: number;
  max_demand_rate: number;
  planned_maintenance_cost: number;
  emergency_multiplier: number;
}

export interface AHUCost {
  ahu_id: string;
  health_index: number;
  excess_energy_cost: number;
  pf_penalty_cost: number;
  maintenance_risk: number;
  total_cost: number;
}

export interface FinancialImpact {
  currency: string;
  level: number;
  range: string;
  grand_total: number;
  excess_energy_cost: number;
  pf_penalty_cost: number;
  maintenance_risk: number;
  top_ahus: AHUCost[];
}

// ── AHU On/Off Period Types ───────────────────────────────────────────────

export type OffPeriod = { start: string; end: string };

// ── AHU Heatmap Types ─────────────────────────────────────────────────────

export interface AHUHeatmapHour {
  hour: number;
  avg_health: number | null;
}

export interface AHUHeatmapResponse {
  ahu_id: string;
  range: string;
  hours: AHUHeatmapHour[];
}

// ── Site Summary Types ─────────────────────────────────────────────────────

export interface LevelHealthTile {
  level: number; // 1–11
  avgHealth: number; // 0–100
  ahuCount: number;
}

export interface SpotlightAHU {
  id: string;
  name: string;
  level: number;
  healthScore: number;
  monthlyCostMYR: number;
  safetyFlags: number;
  operational_state?: OperationalState;
  last_on_timestamp?: string | null;
}

export interface TrendDelta {
  label: string; // e.g. "Energy"
  value: number; // signed
  unit: string; // "%" | "pts" | "MYR" | ""
  direction: 'up' | 'down';
}

// ── Site Alerts Types ─────────────────────────────────────────────────────

export interface AlertAHU {
  id: string;
  name: string;
  level: number;
  healthScore: number;
  tier: 'Critical' | 'Maintenance Soon';
  operational_state?: OperationalState;
  last_on_timestamp?: string | null;
}

export interface SiteAlertsResponse {
  ahus: AlertAHU[];
  total: number;
}

export interface SiteSummaryData {
  totalAHUs: number;
  avgSiteHealth: number;
  ahusInAlert: number;
  estMonthlyCostMYR: number;
  starAHU: SpotlightAHU;
  criticalAHU: SpotlightAHU;
  levelTiles: LevelHealthTile[]; // 11 entries
  trendDeltas: TrendDelta[];
  alertAHUs: AlertAHU[]; // AHUs in Maintenance Soon or Critical tier
}
