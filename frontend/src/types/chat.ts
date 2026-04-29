export interface NavigateTarget {
  level: number;
  device?: string;
  view?: 'prediction' | 'dashboard';
}

export interface ActionItem {
  type: 'approve_work_order' | 'dismiss' | 'edit_draft';
  work_order_id: number;
  label: string;
  description: string;
}

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result?: string;
}

// Single source of truth for health tiers — mirrors fair_health_scoring.py HEALTH_TIERS
// Healthy: FAIR 80-100 | Monitor: 60-79 | Maintenance Soon: 40-59 | Critical: 0-39
export type HealthTier = 'Healthy' | 'Monitor' | 'Maintenance Soon' | 'Critical';

export const HEALTH_TIER_COLORS: Record<HealthTier, string> = {
  Critical: '#FF4D4D',
  'Maintenance Soon': '#FFB020',
  Monitor: '#4DA6FF',
  Healthy: '#00E5A0',
};

export interface AHUSummary {
  ahu_id: string;
  level: number;
  fair: { F: number; A: number; I: number; R: number; composite: number };
  severity: HealthTier;
}

export interface ChartCardData {
  title: string;
  entries: Array<{ device: string; value: number }>;
  unit: string;
}

export interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  navigate?: NavigateTarget | null;
  actions?: ActionItem[];
  tool_calls?: ToolCall[];
  ahu_summary?: AHUSummary | null;
  chart_data?: ChartCardData | null;
  suggestions?: string[];
}

export interface WorkOrder {
  id: number;
  ticket_no: string;
  ahu_id: string;
  level: number;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  trigger_source: string;
  fair_snapshot: Record<string, number> | null;
  notified_via: string;
  approved_by: string | null;
}
