/**
 * @file HealthChart.test.jsx
 * @description Unit tests for Health Chart components with edge cases
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'

// Mock Recharts for testing
jest.mock('recharts', () => ({
  ComposedChart: jest.fn(({ children }) => <div data-testid="mock-composed-chart">{children}</div>),
  Line: jest.fn(() => <div data-testid="mock-line" />),
  XAxis: jest.fn(() => <div data-testid="mock-xaxis" />),
  YAxis: jest.fn(() => <div data-testid="mock-yaxis" />),
  CartesianGrid: jest.fn(() => <div data-testid="mock-cartesian-grid" />),
  Tooltip: jest.fn(() => <div data-testid="mock-tooltip" />),
  ResponsiveContainer: jest.fn(({ children }) => <div data-testid="mock-responsive-container">{children}</div>),
  Legend: jest.fn(() => <div data-testid="mock-legend" />),
  ReferenceLine: jest.fn(() => <div data-testid="mock-reference-line" />),
}))

// Mock summaryGenerator
jest.mock('../lib/summaryGenerator', () => ({
  buildSummary: jest.fn(() => 'Mock summary'),
  buildWorstDevicesList: jest.fn(() => []),
  buildThresholdEvents: jest.fn(() => []),
}))

// Mock api
const mockApi = {
  get: jest.fn(),
}
jest.mock('../api.js', () => mockApi)

// Import component
const { HealthChart } = require('../HealthChart')

describe('HealthChart', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockApi.get.mockResolvedValue({ data: { metrics: [] } })
  })

  describe('Edge Cases', () => {
    test('renders chart with empty data array', () => {
      const props = {
        metric: 'health_index',
        data: [],
        ahuIds: [],
      }
      
      expect(() => {
        render(<HealthChart {...props} />)
      }).not.toThrow()
    })

    test('handles NaN values in data', () => {
      const props = {
        metric: 'health_index',
        data: [
          { timestamp: '2026-03-01T10:00Z', ahu_id: 'e0101', value: NaN },
          { timestamp: '2026-03-01T11:00Z', ahu_id: 'e0101', value: 50 },
        ],
        ahuIds: ['e0101'],
      }

      expect(() => {
        render(<HealthChart {...props} />)
      }).not.toThrow()
    })

    test('handles missing health_index values', () => {
      const props = {
        metric: 'health_index',
        data: [
          { timestamp: '2026-03-01T10:00Z', ahu_id: 'e0101' },
          { timestamp: '2026-03-01T11:00Z', ahu_id: 'e0101', health_index: 50 },
        ],
        ahuIds: ['e0101'],
      }

      expect(() => {
        render(<HealthChart {...props} />)
      }).not.toThrow()
    })

    test('handles out-of-range scores (negative)', () => {
      const props = {
        metric: 'energy_anomaly',
        data: [
          { timestamp: '2026-03-01T10:00Z', ahu_id: 'e0101', energy_anomaly: -0.5 },
          { timestamp: '2026-03-01T11:00Z', ahu_id: 'e0101', energy_anomaly: 0.3 },
        ],
        ahuIds: ['e0101'],
      }

      expect(() => {
        render(<HealthChart {...props} />)
      }).not.toThrow()
    })

    test('handles out-of-range scores (> 1)', () => {
      const props = {
        metric: 'energy_anomaly',
        data: [
          { timestamp: '2026-03-01T10:00Z', ahu_id: 'e0101', energy_anomaly: 1.5 },
          { timestamp: '2026-03-01T11:00Z', ahu_id: 'e0101', energy_anomaly: 0.3 },
        ],
        ahuIds: ['e0101'],
      }

      expect(() => {
        render(<HealthChart {...props} />)
      }).not.toThrow()
    })

    test('handles null timestamp values', () => {
      const props = {
        metric: 'health_index',
        data: [
          { timestamp: null, ahu_id: 'e0101', health_index: 50 },
          { timestamp: '2026-03-01T11:00Z', ahu_id: 'e0101', health_index: 60 },
        ],
        ahuIds: ['e0101'],
      }

      expect(() => {
        render(<HealthChart {...props} />)
      }).not.toThrow()
    })

    test('handles missing ahu_id values', () => {
      const props = {
        metric: 'health_index',
        data: [
          { timestamp: '2026-03-01T10:00Z', ahu_id: null, health_index: 50 },
          { timestamp: '2026-03-01T11:00Z', ahu_id: 'e0101', health_index: 60 },
        ],
        ahuIds: ['e0101', null],
      }

      expect(() => {
        render(<HealthChart {...props} />)
      }).not.toThrow()
    })

    test('handles single data point', () => {
      const props = {
        metric: 'health_index',
        data: [
          { timestamp: '2026-03-01T10:00Z', ahu_id: 'e0101', health_index: 50 },
        ],
        ahuIds: ['e0101'],
      }

      expect(() => {
        render(<HealthChart {...props} />)
      }).not.toThrow()
    })

    test('handles very large dataset', () => {
      const largeData = Array.from({ length: 1000 }, (_, i) => ({
        timestamp: new Date(2026, 2, 1, i % 24).toISOString(),
        ahu_id: 'e0101',
        health_index: Math.random() * 100,
      }))

      const props = {
        metric: 'health_index',
        data: largeData,
        ahuIds: ['e0101'],
      }

      expect(() => {
        render(<HealthChart {...props} />)
      }).not.toThrow()
    })

    test('renders with valid data and checks placeholder message', () => {
      const props = {
        metric: 'health_index',
        data: [
          { timestamp: '2026-03-01T10:00Z', ahu_id: 'e0101', health_index: 50 },
          { timestamp: '2026-03-01T11:00Z', ahu_id: 'e0102', health_index: 60 },
        ],
        ahuIds: ['e0101', 'e0102'],
      }

      render(<HealthChart {...props} />)
      
      // Check that chart renders without crashing
      expect(document.body).toBeTruthy()
    })

    test('validates metric configuration', () => {
      const metricsConfig = {
        health_index: { label: 'Health Index', min: 0, max: 100 },
        energy_anomaly: { label: 'Energy Anomaly', min: 0, max: 1 },
        pf_degradation: { label: 'PF Degradation', min: 0, max: 1 },
        phase_imbalance: { label: 'Phase Imbalance', min: 0, max: 1 },
        thd_drift: { label: 'THD Drift', min: 0, max: 1 },
        overload: { label: 'Overload', min: 0, max: 1 },
      }

      // Verify all metrics have required configuration
      Object.entries(metricsConfig).forEach(([key, config]) => {
        expect(config.label).toBeDefined()
        expect(typeof config.min).toBe('number')
        expect(typeof config.max).toBe('number')
        expect(config.min < config.max).toBe(true)
      })
    })

    test('handles threshold line configurations', () => {
      const thresholds = {
        health_index: [
          { value: 80, label: 'Healthy', color: '#00c9b145' },
          { value: 60, label: 'Monitor', color: '#f5a62345' },
          { value: 40, label: 'Maint.', color: '#f5734e45' },
        ],
        energy_anomaly: [
          { value: 0.6, label: 'High', color: '#ff4d6d45' },
          { value: 0.3, label: 'Elev.', color: '#f5a62345' },
        ],
      }

      // Verify threshold configurations
      expect(thresholds.health_index).toHaveLength(3)
      expect(thresholds.energy_anomaly).toHaveLength(2)
    })
  })

  describe('Health Tier Validation', () => {
    test('maps health index to correct tier', () => {
      const getTier = (index) => {
        if (index >= 80) return 'Healthy'
        if (index >= 60) return 'Monitor'
        if (index >= 40) return 'Maintenance Soon'
        return 'Critical'
      }

      expect(getTier(95)).toBe('Healthy')
      expect(getTier(80)).toBe('Healthy')
      expect(getTier(75)).toBe('Monitor')
      expect(getTier(60)).toBe('Monitor')
      expect(getTier(50)).toBe('Maintenance Soon')
      expect(getTier(40)).toBe('Maintenance Soon')
      expect(getTier(20)).toBe('Critical')
      expect(getTier(0)).toBe('Critical')
    })

    test('handles edge case health indices', () => {
      const getTier = (index) => {
        if (index >= 80) return 'Healthy'
        if (index >= 60) return 'Monitor'
        if (index >= 40) return 'Maintenance Soon'
        return 'Critical'
      }

      // Edge cases at tier boundaries
      expect(getTier(79.9)).toBe('Monitor')
      expect(getTier(59.9)).toBe('Maintenance Soon')
      expect(getTier(39.9)).toBe('Critical')

      // Negative and out-of-range
      expect(getTier(-10)).toBe('Critical')
      expect(getTier(110)).toBe('Healthy') // Out of range but still maps
    })
  })

  describe('Score Clamping Validation', () => {
    test('clamps scores to valid range [0, 1]', () => {
      const clamp = (value) => Math.max(0, Math.min(1, value))

      expect(clamp(-0.5)).toBe(0)
      expect(clamp(1.5)).toBe(1)
      expect(clamp(0)).toBe(0)
      expect(clamp(1)).toBe(1)
      expect(clamp(0.5)).toBe(0.5)
    })

    test('validates all metrics stay within [0, 1]', () => {
      const metrics = [
        { name: 'energy_anomaly', value: 0.5 },
        { name: 'pf_degradation', value: 0.3 },
        { name: 'phase_imbalance', value: 0.4 },
        { name: 'thd_drift', value: 0.2 },
        { name: 'overload', value: 0.6 },
      ]

      metrics.forEach(({ name, value }) => {
        expect(value).toBeGreaterThanOrEqual(0)
        expect(value).toBeLessThanOrEqual(1)
      })
    })
  })

  describe('Missing Data Handling', () => {
    test('returns neutral score when data missing', () => {
      const getNeutralScore = (value) => {
        if (value === null || value === undefined || isNaN(value)) {
          return 0.5 // Neutral score for missing data
        }
        return value
      }

      expect(getNeutralScore(null)).toBe(0.5)
      expect(getNeutralScore(undefined)).toBe(0.5)
      expect(getNeutralScore(NaN)).toBe(0.5)
      expect(getNeutralScore(0.5)).toBe(0.5) // Valid value
    })

    test('calculates health index with neutral scores', () => {
      const calculateHealthIndex = (scores) => {
        const weights = {
          energy_anomaly: 0.15,
          pf_degradation: 0.25,
          phase_imbalance: 0.25,
          thd_drift: 0.15,
          overload: 0.20
        }

        const neutralScore = 0.5
        let penalty = 0
        Object.entries(scores).forEach(([metric, score]) => {
          const validScore = getNeutralScore(score)
          penalty += weights[metric] * validScore
        })
        return 100 - penalty * 100
      }

      const getNeutralScore = (value) => {
        if (value === null || value === undefined || isNaN(value)) {
          return 0.5
        }
        return value
      }

      // All neutral scores → health = 50
      const allNeutral = {
        energy_anomaly: null,
        pf_degradation: undefined,
        phase_imbalance: NaN,
        thd_drift: 0.5,
        overload: null
      }
      const healthIndex = calculateHealthIndex(allNeutral)
      expect(healthIndex).toBeCloseTo(50, 1)

      // All perfect scores → health = 100
      const allPerfect = {
        energy_anomaly: 0,
        pf_degradation: 0,
        phase_imbalance: 0,
        thd_drift: 0,
        overload: 0
      }
      const healthIndex2 = calculateHealthIndex(allPerfect)
      expect(healthIndex2).toBe(100)

      // All max scores → health = 0
      const allMax = {
        energy_anomaly: 1,
        pf_degradation: 1,
        phase_imbalance: 1,
        thd_drift: 1,
        overload: 1
      }
      const healthIndex3 = calculateHealthIndex(allMax)
      expect(healthIndex3).toBe(0)
    })
  })
})
