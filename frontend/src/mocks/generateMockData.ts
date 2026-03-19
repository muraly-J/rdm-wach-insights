// Mock Data Generator for WACH Insight UI Development
// =====================================================
// Used before real API integration is complete
// Spec reference: Section 15 "Mock Data Generator"

import { v4 as uuidv4 } from 'uuid';
import {
  AppState,
  ChatMessage,
  DashboardData,
  Device,
  HealthIndexData,
  ScoreName,
  ScoreWithTrend,
  TimeSeriesData,
} from '../types';

// Device list per level (matching AHU_LEVEL_CONFIG in schemas.py)
const LEVEL_DEVICES: Record<number, Device[]> = {
  1: Array.from({ length: 21 }, (_, i) => ({
    id: `e01${String(i + 1).padStart(2, '0')}`,
    name: `AHU-L1-${String(i + 1).padStart(2, '0')}`,
    level: 1,
  })),
  2: Array.from({ length: 15 }, (_, i) => ({
    id: `e02${String(i + 1).padStart(2, '0')}`,
    name: `AHU-L2-${String(i + 1).padStart(2, '0')}`,
    level: 2,
  })),
  3: Array.from({ length: 16 }, (_, i) => ({
    id: `e03${String(i + 1).padStart(2, '0')}`,
    name: `AHU-L3-${String(i + 1).padStart(2, '0')}`,
    level: 3,
  })),
  4: Array.from({ length: 13 }, (_, i) => ({
    id: `e04${String(i + 1).padStart(2, '0')}`,
    name: `AHU-L4-${String(i + 1).padStart(2, '0')}`,
    level: 4,
  })),
  5: Array.from({ length: 12 }, (_, i) => ({
    id: `e05${String(i + 1).padStart(2, '0')}`,
    name: `AHU-L5-${String(i + 1).padStart(2, '0')}`,
    level: 5,
  })),
};

const ALL_DEVICES = Object.values(LEVEL_DEVICES).flat();

// Helper: Generate time series data
function generateTimeSeries(
  count: number,
  startValue: number,
  volatility: number,
  trend: number = 0
): TimeSeriesData[] {
  const data: TimeSeriesData[] = [];
  let current = startValue;

  for (let i = 0; i < count; i++) {
    const timestamp = new Date(
      Date.now() - (count - i) * 3600000 // Hourly间隔
    ).toISOString();

    const noise = (Math.random() - 0.5) * 2 * volatility;
    current = Math.max(0, Math.min(100, current + noise + trend));

    data.push({
      timestamp,
      value: parseFloat(current.toFixed(2)),
    });
  }

  return data;
}

// Helper: Generate health index for a device
function generateHealthIndexData(device: Device, points: number = 48): HealthIndexData {
  // Each device has characteristic health baseline
  const baseHealth = 60 + Math.random() * 35;
  const trend = (Math.random() - 0.5) * 2; // Slight upward or downward drift

  return {
    device,
    data: generateTimeSeries(points, baseHealth, 5, trend),
  };
}

// Helper: Generate score breakdown for a device
function generateScoreBreakdown(
  device: Device,
  points: number = 48
): Record<ScoreName, ScoreWithTrend> {
  const scores: Record<ScoreName, ScoreWithTrend> = {
    energy_anomaly: {
      current: 65 + Math.random() * 30,
      trend: (Math.random() - 0.5) * 10,
      data: generateTimeSeries(points, 70, 8),
    },
    pf_degradation: {
      current: 60 + Math.random() * 35,
      trend: (Math.random() - 0.5) * 8,
      data: generateTimeSeries(points, 65, 10),
    },
    phase_imbalance: {
      current: 70 + Math.random() * 25,
      trend: (Math.random() - 0.5) * 6,
      data: generateTimeSeries(points, 72, 6),
    },
    thd_drift: {
      current: 68 + Math.random() * 27,
      trend: (Math.random() - 0.5) * 7,
      data: generateTimeSeries(points, 69, 7),
    },
    overload: {
      current: 72 + Math.random() * 23,
      trend: (Math.random() - 0.5) * 9,
      data: generateTimeSeries(points, 74, 9),
    },
  };

  return scores;
}

// Generator Functions (matches spec Section 15)
// =============================================

/**
 * Generate health index data for all devices in a level
 */
export function generateHealthIndex(level: number, points: number = 48): HealthIndexData[] {
  const devices = LEVEL_DEVICES[level] || [];
  return devices.map((device) => generateHealthIndexData(device, points));
}

/**
 * Generate full dashboard data for a level
 */
export function generateDashboardData(level: number, points: number = 48): DashboardData {
  const devices = LEVEL_DEVICES[level] || [];
  
  return {
    healthIndex: devices.map((device) => generateHealthIndexData(device, points)),
    scores: {
      energy_anomaly: [],
      pf_degradation: [],
      phase_imbalance: [],
      thd_drift: [],
      overload: [],
    },
    devices,
    rawData: {},
  };
}

/**
 * Generate score breakdown for all devices in a level
 */
export function generateScoreBreakdowns(level: number, points: number = 48) {
  const devices = LEVEL_DEVICES[level] || [];
  
  return devices.map((device) => ({
    id: device.id,
    name: device.name,
    scores: generateScoreBreakdown(device, points),
  }));
}

/**
 * Generate raw-score relationship data for a single device
 */
export function generateRawScoreRelationship(deviceId: string, points: number = 48) {
  const device = ALL_DEVICES.find((d) => d.id === deviceId);
  if (!device) return null;

  const scores: Record<string, any> = {
    energy_anomaly: {
      rawMetric: 'raw_energy_import',
      rawUnit: 'kWh',
      rawData: generateTimeSeries(points, 45, 8),
      scoreData: generateTimeSeries(points, 75, 8),
    },
    pf_degradation: {
      rawMetric: 'raw_power_factor_avg',
      rawUnit: '',
      rawData: generateTimeSeries(points, 0.82, 0.05),
      scoreData: generateTimeSeries(points, 70, 10),
    },
    phase_imbalance: {
      rawMetric: 'raw_current_unbalance',
      rawUnit: '%',
      rawData: generateTimeSeries(points, 2.5, 0.5),
      scoreData: generateTimeSeries(points, 72, 6),
    },
    thd_drift: {
      rawMetric: 'raw_composite_thd',
      rawUnit: '%',
      rawData: generateTimeSeries(points, 5, 1),
      scoreData: generateTimeSeries(points, 68, 7),
    },
    overload: {
      rawMetric: 'raw_power_total',
      rawUnit: 'kW',
      rawData: generateTimeSeries(points, 2.5, 0.8),
      scoreData: generateTimeSeries(points, 76, 9),
    },
  };

  return { device_id: deviceId, scores };
}

// Mock Chat Data
// ==============

/**
 * Generate initial chat messages
 */
export function generateInitialChatMessages(): ChatMessage[] {
  return [
    {
      id: 'init-1',
      role: 'bot',
      content: "Hey! I'm WACH AI. I can help you understand health scores, investigate anomalies, or explain what's driving a specific score. What would you like to know?",
      timestamp: new Date(),
    },
  ];
}

/**
 * Simulate bot response with slight delay
 */
export async function simulateBotResponse(userMessage: string): Promise<string> {
  return new Promise((resolve) => {
    setTimeout(() => {
      const lower = userMessage.toLowerCase();
      
      if (lower.includes('health') || lower.includes('score')) {
        resolve(
          "The current health index for this device is **78/100** (Healthy tier). " +
          "The main contributors are stable power factor at 0.87 and good phase imbalance at 1.2%. " +
          "I notice a slight energy anomaly spike around day 3 - would you like to investigate?"
        );
      } else if (lower.includes('energy')) {
        resolve(
          "Energy anomaly for this device shows a temporary spike of **15% above baseline** on day 3. " +
          "This coincides with normal building occupancy patterns - likely not a concern. " +
          "The 7-day average is within acceptable parameters."
        );
      } else if (lower.includes('vibration')) {
        resolve(
          "Vibration scores are currently **62/100** (Monitor tier). " +
          "The score has been gradually declining over the past 3 days. " +
          "Would you like to check the raw current unbalance data?"
        );
      } else if (lower.includes('compare') || lower.includes('levels')) {
        resolve(
          "Level 1 has 21 AHUs with an average health index of **76/100**. " +
          "Level 2 averages **72/100**, and Level 3 is at **68/100**. " +
          "Would you like to see the ranking for a specific level?"
        );
      } else {
        resolve(
          "I can help you explore health scores, investigate anomalies, or compare devices. " +
          "Try asking about 'energy', 'vibration', 'health index', or ask me to 'rank devices'."
        );
      }
    }, 800); // Simulate network delay
  });
}

// Exports for type safety
export {
  LEVEL_DEVICES,
  ALL_DEVICES,
};
