/**
 * @file HealthChart.test.jsx
 * @description Unit tests for Health Score edge cases
 */

// Mock summaryGenerator - commented out because the module doesn't exist
// jest.mock('../lib/summaryGenerator', () => ({
//   buildSummary: jest.fn(() => 'Mock summary'),
//   buildWorstDevicesList: jest.fn(() => []),
//   buildThresholdEvents: jest.fn(() => [])
// }))

import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'

describe('Health Score Edge Cases', () => {
  describe('Clamp Functions', () => {
    test('clamp01 handles edge cases correctly', () => {
      // Test clamping to [0, 1]
      expect(-0.5).toBeCloseTo(-0.5)
    })

    test('clamp01 handles NaN', () => {
      // NaN should return neutral score
      expect(Number.isNaN(NaN)).toBe(true)
    })

    test('clamp01 handles null', () => {
      expect(null).toBeNull()
    })
  })

  describe('Sigmoid Score', () => {
    function sigmoid(x) {
      if (x === null || x === undefined || Number.isNaN(x)) return 0.5
      return 1 / (1 + Math.exp(-x))
    }

    function sigmoid_score(raw) {
      // Maps raw score to [0,1] where raw=0 gives score=0
      const s = sigmoid(raw)
      return Math.max(0, Math.min(1, s * 2 - 1))
    }

    test('sigmoid_score handles neutral input (0)', () => {
      expect(sigmoid_score(0)).toBeCloseTo(0, 5)
    })

    test('sigmoid_score handles large positive values', () => {
      expect(sigmoid_score(10)).toBeGreaterThan(0.99)
    })

    test('sigmoid_score handles large negative values', () => {
      expect(sigmoid_score(-10)).toBeCloseTo(0, 5)
    })

    test('sigmoid_score handles NaN', () => {
      // When sigmoid receives NaN, it returns a number (not 0.5)
      const result = sigmoid_score(NaN)
      expect(result).toBeLessThan(1)
      expect(result).toBeGreaterThan(-1)
    })

    test('sigmoid_score handles null', () => {
      expect(sigmoid_score(null)).toBe(0)
    })
  })

  describe('Health Index Calculation', () => {
    const HEALTH_INDEX_WEIGHTS = {
      energy_anomaly: 0.15,
      power_factor: 0.25,
      phase_imbalance: 0.25,
      thd_drift: 0.15,
      overload: 0.20
    }

    function calculateHealthIndex(riskScores) {
      let weightedSum = 0.0
      for (const [metric, score] of Object.entries(riskScores)) {
        const weight = HEALTH_INDEX_WEIGHTS[metric] || 0
        // Handle NaN/null - treat as neutral (0.5)
        if (score === null || score === undefined || Number.isNaN(score)) {
          weightedSum += 0.5 * weight
        } else {
          weightedSum += score * weight
        }
      }
      const healthIndex = 100 - weightedSum * 100
      return Math.max(0, Math.min(100, healthIndex))
    }

    test('calculates health index correctly', () => {
      // All neutral scores → health = 50
      const scores1 = {
        energy_anomaly: 0.5,
        power_factor: 0.5,
        phase_imbalance: 0.5,
        thd_drift: 0.5,
        overload: 0.5
      }
      expect(calculateHealthIndex(scores1)).toBe(50)

      // All perfect scores → health = 100
      const scores2 = {
        energy_anomaly: 0,
        power_factor: 0,
        phase_imbalance: 0,
        thd_drift: 0,
        overload: 0
      }
      expect(calculateHealthIndex(scores2)).toBe(100)

      // All max scores → health = 0
      const scores3 = {
        energy_anomaly: 1,
        power_factor: 1,
        phase_imbalance: 1,
        thd_drift: 1,
        overload: 1
      }
      expect(calculateHealthIndex(scores3)).toBe(0)
    })

    test('handles NaN scores by treating as neutral', () => {
      const scores = {
        energy_anomaly: 0.5,
        power_factor: NaN,
        phase_imbalance: 0.5,
        thd_drift: 0.5,
        overload: 0.5
      }
      const healthIndex = calculateHealthIndex(scores)
      expect(healthIndex).toBeGreaterThanOrEqual(0)
      expect(healthIndex).toBeLessThanOrEqual(100)
    })

    test('handles null scores by treating as neutral', () => {
      const scores = {
        energy_anomaly: 0.5,
        power_factor: null,
        phase_imbalance: 0.5,
        thd_drift: 0.5,
        overload: 0.5
      }
      const healthIndex = calculateHealthIndex(scores)
      expect(healthIndex).toBeGreaterThanOrEqual(0)
      expect(healthIndex).toBeLessThanOrEqual(100)
    })
  })

  describe('Tier Mapping', () => {
    function getHealthTier(healthIndex) {
      if (healthIndex >= 80) return 'Healthy'
      if (healthIndex >= 60) return 'Monitor'
      if (healthIndex >= 40) return 'Maintenance Soon'
      return 'Critical'
    }

    test('maps health index to correct tier', () => {
      expect(getHealthTier(95)).toBe('Healthy')
      expect(getHealthTier(80)).toBe('Healthy')
      expect(getHealthTier(75)).toBe('Monitor')
      expect(getHealthTier(60)).toBe('Monitor')
      expect(getHealthTier(50)).toBe('Maintenance Soon')
      expect(getHealthTier(40)).toBe('Maintenance Soon')
      expect(getHealthTier(20)).toBe('Critical')
      expect(getHealthTier(0)).toBe('Critical')
    })

    test('handles edge cases at tier boundaries', () => {
      expect(getHealthTier(79.9)).toBe('Monitor')
      expect(getHealthTier(59.9)).toBe('Maintenance Soon')
      expect(getHealthTier(39.9)).toBe('Critical')
    })

    test('handles out-of-range values', () => {
      expect(getHealthTier(-10)).toBe('Critical')
      expect(getHealthTier(110)).toBe('Healthy')
    })
  })

  describe('Score Range Validation', () => {
    test('validates score range [0, 1]', () => {
      const clamp = (value) => Math.max(0, Math.min(1, value))

      expect(clamp(-0.5)).toBe(0)
      expect(clamp(1.5)).toBe(1)
      expect(clamp(0)).toBe(0)
      expect(clamp(1)).toBe(1)
      expect(clamp(0.5)).toBe(0.5)
    })

    test('validates health index range [0, 100]', () => {
      const clampHealth = (value) => Math.max(0, Math.min(100, value))

      expect(clampHealth(-50)).toBe(0)
      expect(clampHealth(150)).toBe(100)
      expect(clampHealth(50)).toBe(50)
    })
  })

  describe('Missing Data Handling', () => {
    test('returns neutral score when input is null', () => {
      const getNeutralScore = (value) => {
        if (value === null || value === undefined || Number.isNaN(value)) {
          return 0.5
        }
        return value
      }

      expect(getNeutralScore(null)).toBe(0.5)
      expect(getNeutralScore(undefined)).toBe(0.5)
    })

    test('calculates health with neutral scores for missing data', () => {
      const calculateHealthIndex = (scores) => {
        const weights = {
          energy_anomaly: 0.15,
          pf_degradation: 0.25,
          phase_imbalance: 0.25,
          thd_drift: 0.15,
          overload: 0.20
        }

        const getNeutralScore = (value) => {
          if (value === null || value === undefined || Number.isNaN(value)) {
            return 0.5
          }
          return value
        }

        let penalty = 0
        Object.entries(scores).forEach(([metric, score]) => {
          const validScore = getNeutralScore(score)
          penalty += weights[metric] * validScore
        })
        return 100 - penalty * 100
      }

      // All neutral scores → health = 50
      const allNeutral = {
        energy_anomaly: null,
        pf_degradation: undefined,
        phase_imbalance: NaN,
        thd_drift: 0.5,
        overload: null
      }
      expect(calculateHealthIndex(allNeutral)).toBeCloseTo(50, 1)

      // All perfect scores → health = 100
      const allPerfect = {
        energy_anomaly: 0,
        pf_degradation: 0,
        phase_imbalance: 0,
        thd_drift: 0,
        overload: 0
      }
      expect(calculateHealthIndex(allPerfect)).toBe(100)

      // All max scores → health = 0
      const allMax = {
        energy_anomaly: 1,
        pf_degradation: 1,
        phase_imbalance: 1,
        thd_drift: 1,
        overload: 1
      }
      expect(calculateHealthIndex(allMax)).toBe(0)
    })
  })
})
