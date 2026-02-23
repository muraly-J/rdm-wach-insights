import { useState, useEffect, useCallback } from 'react'
import api from '../api.js'

// ──────────────────────────────────────────────────────────────────────────────
// Electrical Risk Check Component (Stage 2B - Rule-Based Baseline)
// ──────────────────────────────────────────────────────────────

const HEALTH_TIERS = {
  Healthy: { color: '#10b981', label: 'Healthy', min: 80 },
  Monitor: { color: '#f59e0b', label: 'Monitor', min: 60 },
  MaintenanceSoon: { color: '#f97316', label: 'Maintenance Soon', min: 40 },
  Critical: { color: '#ef4444', label: 'Critical', min: 0 },
}

const TIERS_ORDER = ['Healthy', 'Monitor', 'MaintenanceSoon', 'Critical']

export default function ElectricalRiskView() {
  const [assessments, setAssessments] = useState([])
  const [fleetSummary, setFleetSummary] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [timeRange, setTimeRange] = useState('last_30d')
  const [selectedAhuId, setSelectedAhuId] = useState(null)
  const [details, setDetails] = useState(null)

  // Load fleet-wide assessment on mount
  useEffect(() => {
    loadFleetAssessment(timeRange)
  }, [timeRange])

  const loadFleetAssessment = useCallback(async (range) => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await api.get(`/api/electrical-risk?time_range=${range}`)
      setAssessments(response.data.assessments || [])
      setFleetSummary(response.data.fleet_summary || {})
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load electrical risk assessment')
    } finally {
      setIsLoading(false)
    }
  }, [])

  const loadAhuDetails = useCallback(async (ahuId) => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await api.get(`/api/electrical-risk/${ahuId}`)
      setDetails(response.data)
      setSelectedAhuId(ahuId)
    } catch (err) {
      setError(err.response?.data?.error || `Failed to load details for ${ahuId}`)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const closeDetails = useCallback(() => {
    setDetails(null)
    setSelectedAhuId(null)
  }, [])

  // Sort assessments by health index (lowest first for critical priority)
  const sortedAssessments = [...assessments].sort((a, b) => 
    (a.health_index || 0) - (b.health_index || 0)
  )

  // Tier distribution
  const tierCounts = fleetSummary?.tier_distribution || {
    Healthy: 0,
    Monitor: 0,
    MaintenanceSoon: 0,
    Critical: 0,
  }

  const totalAssessed = fleetSummary?.top_5_lowest_health_index?.length || 0

  // Get risk score with severity color
  const getRiskColor = (score) => {
    if (score >= 0.8) return 'text-red-600'
    if (score >= 0.6) return 'text-orange-500'
    if (score >= 0.4) return 'text-yellow-600'
    return 'text-green-600'
  }

  const getRiskBadge = (score) => {
    if (score >= 0.8) return 'CRITICAL'
    if (score >= 0.6) return 'ATTENTION'
    if (score >= 0.4) return 'MONITOR'
    return 'NORMAL'
  }

  // Health tier badge
  const getHealthTierColor = (tier) => {
    const colors = {
      Healthy: 'bg-emerald-100 text-emerald-800',
      Monitor: 'bg-amber-100 text-amber-800',
      MaintenanceSoon: 'bg-orange-100 text-orange-800',
      Critical: 'bg-red-100 text-red-800',
    }
    return colors[tier] || 'bg-gray-100 text-gray-800'
  }

  // Health index progress bar
  const HealthBar = ({ value }) => {
    let colorClass, bgClass
    if (value >= 80) { colorClass = 'text-emerald-600'; bgClass = 'bg-emerald-500' }
    else if (value >= 60) { colorClass = 'text-amber-500'; bgClass = 'bg-amber-500'
    }
    else if (value >= 40) { colorClass = 'text-orange-500'; bgClass = 'bg-orange-500' }
    else { colorClass = 'text-red-600'; bgClass = 'bg-red-500' }

    return (
      <div className="w-full bg-gray-200 rounded-full h-3">
        <div
          className={`h-3 rounded-full ${bgClass} transition-all duration-500`}
          style={{ width: `${value}%` }}
        />
      </div>
    )
  }

  // Risk score badge
  const RiskBadge = ({ score }) => (
    <div className={`px-2 py-1 rounded text-xs font-bold ${score >= 0.8 ? 'bg-red-100 text-red-700' : score >= 0.6 ? 'bg-orange-100 text-orange-700' : score >= 0.4 ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'}`}>
      {((1 - score) * 100).toFixed(0)}% Safe
    </div>
  )

  // Loading state
  if (isLoading && !assessments.length) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="p-6 text-center">
        <div className="text-red-600 font-medium">{error}</div>
        <button
          onClick={() => loadFleetAssessment(timeRange)}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Try Again
        </button>
      </div>
    )
  }

  // Detail view modal
  if (details && selectedAhuId) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50" onClick={closeDetails}>
        <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
          <div className="p-6 border-b">
            <h2 className="text-xl font-semibold">Electrical Risk Assessment</h2>
            <div className="flex justify-between items-center mt-2">
              <span className="font-mono text-lg">{selectedAhuId}</span>
              <button onClick={closeDetails} className="text-gray-500 hover:text-gray-700">✕</button>
            </div>
          </div>

          <div className="p-6 space-y-6">
            {/* Health Index */}
            <div className="flex items-center justify-between bg-gray-50 p-4 rounded-lg">
              <div>
                <span className="text-sm text-gray-500">Health Index</span>
                <div className="flex items-baseline space-x-2">
                  <span className={`text-3xl font-bold ${details.health_index >= 80 ? 'text-emerald-600' : details.health_index >= 60 ? 'text-amber-500' : 'text-red-600'}`}>
                    {details.health_index.toFixed(1)}
                  </span>
                  <span className="text-gray-400">/ 100</span>
                </div>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getHealthTierColor(details.health_tier)}`}>
                {details.health_tier}
              </span>
            </div>

            {/* Risk Scores */}
            <div className="space-y-4">
              <h3 className="font-semibold text-gray-700">Risk Scores</h3>
              
              {Object.entries(details.risk_scores).map(([name, scoreData]) => (
                <div key={name} className="border rounded-lg p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium capitalize">{name.replace('_', ' ')}</span>
                    <RiskBadge score={scoreData.score} />
                  </div>
                  <HealthBar value={(1 - scoreData.score) * 100} />
                  
                  <div className="mt-3 space-y-2">
                    <p className="text-sm text-gray-600"><strong>Signal:</strong> {scoreData.signal}</p>
                    <p className="text-sm text-gray-500"><strong>Severity:</strong> {scoreData.severity}</p>
                    <p className="text-sm text-gray-500"><strong>Confidence:</strong> {scoreData.confidence}</p>
                    {scoreData.root_cause_uncertainty && (
                      <p className="text-sm text-amber-600"><strong>Root Cause:</strong> {scoreData.root_cause_uncertainty}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Energy Assessment */}
            <div className="border rounded-lg p-4">
              <h3 className="font-semibold text-gray-700 mb-3">Energy Assessment</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Forecast 24h (kWh)</span>
                  <div className="font-medium">{details.energy.forecast_24h_kwh ?? 'N/A'}</div>
                </div>
                <div>
                  <span className="text-gray-500">Deviation Probability</span>
                  <div className={`font-medium ${details.energy.deviation_probability_pct > 10 ? 'text-red-500' : 'text-gray-700'}`}>
                    {details.energy.deviation_probability_pct != null ? `${details.energy.deviation_probability_pct}%` : 'N/A'}
                  </div>
                </div>
              </div>
            </div>

            {/* Data Quality */}
            <div className="border rounded-lg p-4 bg-gray-50">
              <h3 className="font-semibold text-gray-700 mb-2">Data Quality</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Missing Data</span>
                  <div className="font-medium">{details.data_quality.missing_data_pct}%</div>
                </div>
                <div>
                  <span className="text-gray-500">Model Source</span>
                  <div className="font-medium font-mono">{details.data_quality.model_source}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Main fleet view
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="pb-4 border-b mb-4">
        <h1 className="text-2xl font-bold">Electrical Risk Check</h1>
        <p className="text-gray-500 mt-1">
          Stage 2B - Rule-based baseline system. Scanning all AHUs for electrical risk factors.
        </p>
      </div>

      {/* Time Range Selector */}
      <div className="mb-6 flex items-center space-x-4">
        <span className="text-sm font-medium">Time Range:</span>
        {['last_24h', 'last_7d', 'last_30d', 'all_time'].map(range => (
          <button
            key={range}
            onClick={() => setTimeRange(range)}
            className={`px-3 py-1 rounded text-sm ${
              timeRange === range
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {range.replace('_', ' ').toUpperCase()}
          </button>
        ))}
      </div>

      {/* Tier Distribution Summary */}
      {fleetSummary && (
        <div className="grid grid-cols-4 gap-3 mb-6">
          {[
            { tier: 'Healthy', label: 'Healthy', color: 'bg-emerald-500' },
            { tier: 'Monitor', label: 'Monitor', color: 'bg-amber-500' },
            { tier: 'MaintenanceSoon', label: 'Maintenance Soon', color: 'bg-orange-500' },
            { tier: 'Critical', label: 'Critical', color: 'bg-red-500' },
          ].map((item) => (
            <div key={item.tier} className={`p-4 rounded-lg ${item.color} text-white`}>
              <div className="text-sm opacity-90">{item.label}</div>
              <div className="text-2xl font-bold">
                {tierCounts[item.tier] ?? 0}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Top Critical Units */}
      {fleetSummary?.top_5_lowest_health_index && fleetSummary.top_5_lowest_health_index.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3">⚠️ Units Requiring Immediate Attention</h2>
          <div className="space-y-3">
            {fleetSummary.top_5_lowest_health_index.slice(0, 5).map((item, idx) => (
              <div key={idx} className="flex items-center justify-between p-4 border rounded-lg hover:shadow-md transition">
                <div className="flex items-center space-x-3">
                  <span className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                    idx === 0 ? 'bg-red-500 text-white' :
                    idx === 1 ? 'bg-orange-500 text-white' :
                    idx === 2 ? 'bg-yellow-500 text-black' : 'bg-gray-200'
                  }`}>
                    {idx + 1}
                  </span>
                  <div>
                    <div className="font-mono font-semibold">{item.ahu_id}</div>
                    <div className="text-sm text-gray-500">
                      Health Index: {item.health_index.toFixed(1)}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => loadAhuDetails(item.ahu_id)}
                  className="px-4 py-2 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                >
                  View Details
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rising Risk Units */}
      {fleetSummary?.top_5_rising_risk && fleetSummary.top_5_rising_risk.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3">📈 Units with Rising Risk</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {fleetSummary.top_5_rising_risk.map((item, idx) => (
              <div key={idx} className="p-4 border rounded-lg bg-orange-50">
                <div className="flex justify-between items-start">
                  <span className="font-mono">{item.ahu_id}</span>
                  <span className="text-xs bg-orange-200 text-orange-700 px-2 py-1 rounded">High Load</span>
                </div>
                <div className="mt-2 text-sm">
                  Overload Score: <span className="font-bold">{item.overload_score.toFixed(3)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Quality Issues */}
      {fleetSummary?.data_quality_issues_count > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3">📋 Data Quality Warnings</h2>
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-yellow-800">
              {fleetSummary.data_quality_issues_count} AHUs have missing data that may affect risk scores.
            </p>
          </div>
        </div>
      )}

      {/* Full Assessment Table */}
      <div className="flex-1 overflow-y-auto">
        <h2 className="text-lg font-semibold mb-3"> fleet Assessment</h2>
        
        {sortedAssessments.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No assessments available for selected time range.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b">
                  <th className="p-3 font-semibold text-sm">AHU ID</th>
                  <th className="p-3 font-semibold text-sm">Health Index</th>
                  <th className="p-3 font-semibold text-sm">PF Risk</th>
                  <th className="p-3 font-semibold text-sm">Imbalance Risk</th>
                  <th className="p-3 font-semibold text-sm">THD Risk</th>
                  <th className="p-3 font-semibold text-sm">Overload Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {sortedAssessments.slice(0, 50).map((assessment) => (
                  <tr 
                    key={assessment.ahu_id} 
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => loadAhuDetails(assessment.ahu_id)}
                  >
                    <td className="p-3 font-mono">{assessment.ahu_id}</td>
                    <td className="p-3">
                      <div className="flex items-center space-x-2">
                        <span className={`font-bold ${assessment.health_index >= 80 ? 'text-emerald-600' : assessment.health_index >= 40 ? 'text-amber-500' : 'text-red-600'}`}>
                          {assessment.health_index.toFixed(1)}
                        </span>
                      </div>
                    </td>
                    <td className="p-3">
                      <RiskBadge score={assessment.risk_scores.power_factor.score} />
                    </td>
                    <td className="p-3">
                      <RiskBadge score={assessment.risk_scores.phase_imbalance.score} />
                    </td>
                    <td className="p-3">
                      <RiskBadge score={assessment.risk_scores.thd_drift.score} />
                    </td>
                    <td className="p-3">
                      <RiskBadge score={assessment.risk_scores.overload.score} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
