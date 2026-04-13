import type { MetricOption, ScoreMetricGroup } from '../types';

export const METRIC_META: Record<string, { unit: string; label: string; description: string }> = {
  power_total: { unit: 'kW', label: 'Power Total', description: 'Total active power' },
  power_l1: { unit: 'kW', label: 'Power L1', description: 'Active power Phase L1' },
  power_l2: { unit: 'kW', label: 'Power L2', description: 'Active power Phase L2' },
  power_l3: { unit: 'kW', label: 'Power L3', description: 'Active power Phase L3' },
  power_demand: { unit: 'kW', label: 'Power Demand', description: 'Rolling average demand' },
  energy_import: { unit: 'kWh', label: 'Energy Import', description: 'Energy consumed from grid' },
  apparent_power_total: {
    unit: 'kVA',
    label: 'Apparent Power',
    description: 'Total apparent power',
  },
  reactive_power_total: {
    unit: 'kVAR',
    label: 'Reactive Power',
    description: 'Total reactive power',
  },
  power_factor_avg: { unit: '', label: 'PF Average', description: 'Power factor average' },
  power_factor_l1: { unit: '', label: 'PF L1', description: 'Power factor Phase L1' },
  power_factor_l2: { unit: '', label: 'PF L2', description: 'Power factor Phase L2' },
  power_factor_l3: { unit: '', label: 'PF L3', description: 'Power factor Phase L3' },
  current_unbalance: { unit: '%', label: 'Current Unbalance', description: 'Current unbalance %' },
  current_avg: { unit: 'A', label: 'Current Avg', description: 'Average current across phases' },
  current_l1: { unit: 'A', label: 'Current L1', description: 'Current Phase L1' },
  current_l2: { unit: 'A', label: 'Current L2', description: 'Current Phase L2' },
  current_l3: { unit: 'A', label: 'Current L3', description: 'Current Phase L3' },
  volts_unbalance: { unit: '%', label: 'Voltage Unbalance', description: 'Voltage unbalance %' },
  volts_l1_n: { unit: 'V', label: 'Volts L1-N', description: 'Phase L1 to neutral' },
  volts_l2_n: { unit: 'V', label: 'Volts L2-N', description: 'Phase L2 to neutral' },
  volts_l3_n: { unit: 'V', label: 'Volts L3-N', description: 'Phase L3 to neutral' },
  current_l1_thd: { unit: '%', label: 'Current THD L1', description: 'Current THD Phase L1' },
  current_l3_thd: { unit: '%', label: 'Current THD L3', description: 'Current THD Phase L3' },
  volts_l1_thd: { unit: '%', label: 'Voltage THD L1', description: 'Voltage THD Phase L1' },
  volts_l2_thd: { unit: '%', label: 'Voltage THD L2', description: 'Voltage THD Phase L2' },
  volts_l3_thd: { unit: '%', label: 'Voltage THD L3', description: 'Voltage THD Phase L3' },
  freq: { unit: 'Hz', label: 'Frequency', description: 'System frequency' },
  volts_l_n_avg: { unit: 'V', label: 'Volts L-N Avg', description: 'Phase-to-neutral average' },
  volts_l_l_avg: { unit: 'V', label: 'Volts L-L Avg', description: 'Phase-to-phase average' },
};

function toOption(key: string): MetricOption {
  const meta = METRIC_META[key] ?? { unit: '', label: key, description: '' };
  return { key, ...meta };
}

export const SCORE_METRIC_GROUPS: ScoreMetricGroup[] = [
  {
    scoreKey: 'energy_anomaly',
    scoreLabel: 'Energy Anomaly',
    availableMetrics: [
      'energy_import',
      'power_total',
      'power_l1',
      'power_l2',
      'power_l3',
      'power_demand',
    ].map(toOption),
  },
  {
    scoreKey: 'pf_degradation',
    scoreLabel: 'PF Degradation',
    availableMetrics: [
      'power_factor_avg',
      'power_factor_l1',
      'power_factor_l2',
      'power_factor_l3',
      'reactive_power_total',
      'apparent_power_total',
      'power_total',
    ].map(toOption),
  },
  {
    scoreKey: 'phase_imbalance',
    scoreLabel: 'Phase Imbalance',
    availableMetrics: [
      'current_unbalance',
      'current_l1',
      'current_l2',
      'current_l3',
      'current_avg',
      'volts_unbalance',
      'volts_l1_n',
      'volts_l2_n',
      'volts_l3_n',
    ].map(toOption),
  },
  {
    scoreKey: 'thd_drift',
    scoreLabel: 'THD Drift',
    availableMetrics: [
      'current_l1_thd',
      'current_l3_thd',
      'volts_l1_thd',
      'volts_l2_thd',
      'volts_l3_thd',
    ].map(toOption),
  },
  {
    scoreKey: 'overload',
    scoreLabel: 'Overload',
    availableMetrics: [
      'power_total',
      'power_l1',
      'power_l2',
      'power_l3',
      'current_avg',
      'current_l1',
      'current_l2',
      'current_l3',
      'apparent_power_total',
    ].map(toOption),
  },
];

// All selectable metrics for Prediction view (deduplicated flat list)
export const ALL_SELECTABLE_METRICS: MetricOption[] = Object.keys(METRIC_META).map(toOption);

// Core metrics that have full forecast data in PredictionChart
export const PREDICTION_CORE_METRICS = new Set([
  'energy_import',
  'power_total',
  'power_factor_avg',
  'current_unbalance',
  'composite_thd',
]);

// Cycling colors for mini-charts (avoids clash with main score colors)
export const MINI_CHART_COLORS = ['#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16', '#F97316'];
