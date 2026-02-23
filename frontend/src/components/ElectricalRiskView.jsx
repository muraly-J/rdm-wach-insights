import { useState, useEffect, useCallback } from 'react'
import api from '../api.js'

// ──────────────────────────────────────────────────────────────────────────────
// Electrical Risk Check Component (Stage 2B - Rule-Based Baseline)
// Matches ChatView style and design system
// ──────────────────────────────────────────────────────────────────────────────

const HEALTH_TIERS = {
  Healthy: { color: '#00c9b1', label: 'Healthy', min: 80 },
  Monitor: { color: '#f5a623', label: 'Monitor', min: 60 },
  MaintenanceSoon: { color: '#f5734e', label: 'Maintenance Soon', min: 40 },
  Critical: { color: '#ff4d6d', label: 'Critical', min: 0 },
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
    if (score >= 0.8) return 'text-red-500'
    if (score >= 0.6) return 'text-orange-400'
    if (score >= 0.4) return 'text-yellow-400'
    return 'text-emerald-500'
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
      Healthy: 'bg-teal-500/15 text-teal-400 border-teal-500/20',
      Monitor: 'bg-orange-500/15 text-orange-400 border-orange-500/20',
      MaintenanceSoon: 'bg-red-500/15 text-red-400 border-red-500/20',
      Critical: 'bg-red-600/20 text-red-500 border-red-600/30',
    }
    return colors[tier] || 'bg-gray-500/10 text-gray-400 border-gray-500/20'
  }

  // Health index progress bar
  const HealthBar = ({ value }) => {
    let colorClass, bgClass
    if (value >= 80) { colorClass = 'text-emerald-500'; bgClass = 'bg-emerald-500' }
    else if (value >= 60) { colorClass = 'text-amber-500'; bgClass = 'bg-amber-500' }
    else if (value >= 40) { colorClass = 'text-orange-500'; bgClass = 'bg-orange-500' }
    else { colorClass = 'text-red-600'; bgClass = 'bg-red-500' }

    return (
      <div className="w-full bg-[#131c2e] rounded-full h-2">
        <div
          className={`h-2 rounded-full ${bgClass} transition-all duration-500`}
          style={{ width: `${value}%` }}
        />
      </div>
    )
  }

  // Risk score badge
  const RiskBadge = ({ score }) => (
    <div className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${
      score >= 0.8 ? 'bg-red-500/15 text-red-400 border border-red-500/20' :
      score >= 0.6 ? 'bg-orange-500/15 text-orange-400 border border-orange-500/20' :
      score >= 0.4 ? 'bg-yellow-500/15 text-yellow-500 border border-yellow-500/20' :
      'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
    }`}>
      {((1 - score) * 100).toFixed(0)}% Safe
    </div>
  )

  // Loading state
  if (isLoading && !assessments.length) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600"></div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="chat-view" style={{ display: 'flex', flexDirection: 'column' }}>
        <div className="thread" style={{ flex: 1, overflowY: 'auto', padding: '40px 32px 24px' }}>
          <div className="thread-inner">
            <div className="turn turn-error" style={{ alignItems: 'flex-start' }}>
              <div className="assistant-bubble error-bubble" style={{ maxWidth: '100%' }}>
                <div className="mb-3">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ff4d6d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="15" y1="9" x2="9" y2="15" />
                    <line x1="9" y1="9" x2="15" y2="15" />
                  </svg>
                </div>
                <p className="font-medium mb-2">Error</p>
                <p style={{ whiteSpace: 'pre-wrap' }}>{error}</p>
              </div>
            </div>
          </div>
        </div>
        <div className="input-bar">
          <div className="input-bar-inner" style={{ maxWidth: '820px', margin: '0 auto' }}>
            <div className="input-row">
              <button
                onClick={() => loadFleetAssessment(timeRange)}
                className="send-btn"
                style={{ width: 'auto', height: '46px', padding: '0 24px', fontSize: '13px' }}
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Detail view modal
  if (details && selectedAhuId) {
    const { health_index, health_tier, risk_scores, energy, data_quality } = details

    return (
      <div className="chat-view" style={{ display: 'flex', flexDirection: 'column' }}>
        <div className="thread" style={{ flex: 1, overflowY: 'auto', padding: '40px 32px 24px' }}>
          <div className="thread-inner" style={{ maxWidth: '700px' }}>
            {/* Modal Header */}
            <div className="turn turn-assistant" style={{ alignItems: 'flex-start' }}>
              <div className="assistant-bubble" style={{ maxWidth: '100%', position: 'relative' }}>
                <div className="banner-header">
                  <h3>Electrical Risk Assessment</h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="device-tag" style={{ fontFamily: "'DM Mono', monospace", fontSize: '12px' }}>
                      {selectedAhuId}
                    </span>
                    <button
                      onClick={closeDetails}
                      style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: '#7a90b0', fontSize: '20px', padding: '4px'
                      }}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </div>
                </div>

                {/* Health Index */}
                <div className="banner-header" style={{ marginTop: '16px', marginBottom: '16px' }}>
                  <div>
                    <span className="device-tag" style={{ color: '#7a90b0', fontSize: '12px' }}>
                      Health Index
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span className={`font-bold ${health_index >= 80 ? 'text-teal-400' : health_index >= 60 ? 'text-orange-400' : 'text-red-500'}`} style={{ fontSize: '18px', fontFamily: "'DM Mono', monospace" }}>
                      {health_index.toFixed(1)}
                    </span>
                    <span style={{ color: '#3d526e', fontSize: '10px' }}>/ 100</span>
                  </div>
                </div>

                {/* Health Tier Badge */}
                <div className="input-hint" style={{ marginBottom: '16px' }}>
                  <span className={`px-3 py-1 rounded-full text-[9px] font-bold uppercase border ${getHealthTierColor(health_tier)}`}>
                    {health_tier}
                  </span>
                </div>

                {/* Risk Scores */}
                <h3 style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#7a90b0', marginBottom: '12px' }}>
                  Risk Scores
                </h3>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {Object.entries(risk_scores).map(([name, scoreData]) => (
                    <div key={name} style={{ background: '#0d1424', border: '1px solid #1c2b42', borderRadius: '8px', padding: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '12px', fontWeight: 500, textTransform: 'capitalize' }}>
                          {name.replace('_', ' ')}
                        </span>
                        <RiskBadge score={scoreData.score} />
                      </div>
                      <HealthBar value={(1 - scoreData.score) * 100} />

                      <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <div style={{ fontSize: '10px', color: '#7a90b0' }}>
                          <span style={{ color: '#3d526e', marginRight: '4px' }}>Signal:</span>
                          <span>{scoreData.signal}</span>
                        </div>
                        <div style={{ fontSize: '10px', color: '#3d526e' }}>
                          <span style={{ marginRight: '4px' }}>Severity:</span>
                          {scoreData.severity}
                        </div>
                        <div style={{ fontSize: '10px', color: '#3d526e' }}>
                          <span style={{ marginRight: '4px' }}>Confidence:</span>
                          {scoreData.confidence}
                        </div>
                        {scoreData.root_cause_uncertainty && (
                          <div style={{ fontSize: '10px', color: '#f5a623' }}>
                            <span style={{ marginRight: '4px' }}>Root Cause:</span>
                            {scoreData.root_cause_uncertainty}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Energy Assessment */}
                <h3 style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#7a90b0', marginTop: '16px', marginBottom: '12px' }}>
                  Energy Assessment
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div style={{ background: '#0d1424', border: '1px solid #1c2b42', borderRadius: '8px', padding: '10px' }}>
                    <span style={{ display: 'block', fontSize: '9px', color: '#3d526e', marginBottom: '4px' }}>Forecast 24h (kWh)</span>
                    <div style={{ fontSize: '13px', fontWeight: 500, fontFamily: "'DM Mono', monospace" }}>
                      {energy.forecast_24h_kwh ?? 'N/A'}
                    </div>
                  </div>
                  <div style={{ background: '#0d1424', border: '1px solid #1c2b42', borderRadius: '8px', padding: '10px' }}>
                    <span style={{ display: 'block', fontSize: '9px', color: '#3d526e', marginBottom: '4px' }}>Deviation Probability</span>
                    <div className={energy.deviation_probability_pct > 10 ? 'text-red-500' : 'text-gray-300'} style={{ fontSize: '13px', fontWeight: 500, fontFamily: "'DM Mono', monospace" }}>
                      {energy.deviation_probability_pct != null ? `${energy.deviation_probability_pct}%` : 'N/A'}
                    </div>
                  </div>
                </div>

                {/* Data Quality */}
                <h3 style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#7a90b0', marginTop: '16px', marginBottom: '12px' }}>
                  Data Quality
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div style={{ background: '#0d1424', border: '1px solid #1c2b42', borderRadius: '8px', padding: '10px' }}>
                    <span style={{ display: 'block', fontSize: '9px', color: '#3d526e', marginBottom: '4px' }}>Missing Data</span>
                    <div style={{ fontSize: '13px', fontWeight: 500, fontFamily: "'DM Mono', monospace" }}>
                      {data_quality.missing_data_pct ?? 'N/A'}%
                    </div>
                  </div>
                  <div style={{ background: '#0d1424', border: '1px solid #1c2b42', borderRadius: '8px', padding: '10px' }}>
                    <span style={{ display: 'block', fontSize: '9px', color: '#3d526e', marginBottom: '4px' }}>Model Source</span>
                    <div style={{ fontSize: '12px', fontFamily: "'DM Mono', monospace" }}>
                      {data_quality.model_source ?? 'N/A'}
                    </div>
                  </div>
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
    <div className="chat-view">
      {/* Header */}
      <div style={{ padding: '40px 32px 24px' }}>
        <div className="banner-header">
          <h3>Electrical Risk Check</h3>
        </div>
        <p style={{ color: '#7a90b0', fontSize: '12px', lineHeight: 1.6 }}>
          Stage 2B - Rule-based baseline system. Scanning all AHUs for electrical risk factors.
        </p>
      </div>

      {/* Time Range Selector */}
      <div style={{ padding: '0 32px 16px' }}>
        <span style={{ fontSize: '9px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#3d526e' }}>
          Time Range:
        </span>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
          {['last_24h', 'last_7d', 'last_30d', 'all_time'].map(range => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`category-tab ${timeRange === range ? 'active' : ''}`}
            >
              {range.replace('_', ' ').toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Tier Distribution Summary */}
      {fleetSummary && (
        <div style={{ padding: '0 32px' }}>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '24px' }}>
            {[
              { tier: 'Healthy', label: 'Healthy', color: '#00c9b1' },
              { tier: 'Monitor', label: 'Monitor', color: '#f5a623' },
              { tier: 'MaintenanceSoon', label: 'Maintenance Soon', color: '#f5734e' },
              { tier: 'Critical', label: 'Critical', color: '#ff4d6d' },
            ].map((item) => (
              <div key={item.tier} style={{
                background: 'linear-gradient(135deg, #0d1424, #131c2e)',
                border: '1px solid #1c2b42',
                borderRadius: '8px',
                padding: '16px',
                flex: 1,
              }}>
                <div style={{ fontSize: '9px', color: item.color, textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '6px' }}>
                  {item.label}
                </div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: '#eaf0fb' }}>
                  {tierCounts[item.tier] ?? 0}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Critical Units */}
      {fleetSummary?.top_5_lowest_health_index && fleetSummary.top_5_lowest_health_index.length > 0 && (
        <div style={{ padding: '0 32px' }}>
          <h3 className="banner-header" style={{ marginBottom: '12px', marginTop: '0' }}>
            <span>⚠️ Units Requiring Immediate Attention</span>
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {fleetSummary.top_5_lowest_health_index.slice(0, 5).map((item, idx) => (
              <div key={idx} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '14px', background: '#0d1424', border: '1px solid #1c2b42',
                borderRadius: '8px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{
                    width: '30px', height: '30px', borderRadius: '8px',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700,
                    backgroundColor: idx === 0 ? '#ff4d6d' : idx === 1 ? '#f5734e' : idx === 2 ? '#f5a623' : '#1c2b42',
                    color: idx === 0 ? 'white' : idx === 1 ? 'white' : idx === 2 ? '#080c18' : '#7a90b0',
                  }}>
                    {idx + 1}
                  </span>
                  <div>
                    <div style={{ fontFamily: "'DM Mono', monospace", fontWeight: 500, color: '#eaf0fb' }}>
                      {item.ahu_id}
                    </div>
                    <div style={{ fontSize: '11px', color: '#7a90b0' }}>
                      Health Index: {item.health_index.toFixed(1)}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => loadAhuDetails(item.ahu_id)}
                  style={{
                    padding: '8px 16px', background: '#00c9b115', border: '1px solid #00c9b135',
                    borderRadius: '6px', color: '#00c9b1', fontWeight: 500, cursor: 'pointer',
                    fontSize: '12px', transition: 'all 0.18s'
                  }}
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
        <div style={{ padding: '0 32px' }}>
          <h3 className="banner-header" style={{ marginBottom: '12px', marginTop: '0' }}>
            <span>📈 Units with Rising Risk</span>
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
            {fleetSummary.top_5_rising_risk.map((item, idx) => (
              <div key={idx} style={{
                padding: '14px', background: '#0d1424', border: '1px solid #f5734e20',
                borderRadius: '8px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <span style={{ fontFamily: "'DM Mono', monospace", fontWeight: 500 }}>{item.ahu_id}</span>
                  <span style={{
                    fontSize: '9px', background: '#f5734e20', color: '#f5734e',
                    padding: '3px 8px', borderRadius: '12px'
                  }}>
                    High Load
                  </span>
                </div>
                <div style={{ marginTop: '10px', fontSize: '12px' }}>
                  Overload Score: <span style={{ fontWeight: 700, color: '#eaf0fb' }}>{item.overload_score.toFixed(3)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Quality Issues */}
      {fleetSummary?.data_quality_issues_count > 0 && (
        <div style={{ padding: '0 32px' }}>
          <h3 className="banner-header" style={{ marginBottom: '12px', marginTop: '0' }}>
            <span>📋 Data Quality Warnings</span>
          </h3>
          <div style={{
            padding: '14px', background: '#f5a62308', border: '1px solid #f5a62330',
            borderRadius: '8px', color: '#f5a623'
          }}>
            <p style={{ fontSize: '12px', margin: 0, lineHeight: 1.6 }}>
              {fleetSummary.data_quality_issues_count} AHUs have missing data that may affect risk scores.
            </p>
          </div>
        </div>
      )}

      {/* Full Assessment Table */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 32px 40px' }}>
        <h3 className="banner-header" style={{ marginBottom: '12px', marginTop: '0' }}>
          <span>Fleet Assessment</span>
        </h3>

        {sortedAssessments.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#7a90b0' }}>
            No assessments available for selected time range.
          </div>
        ) : (
          <div style={{ background: '#0d1424', border: '1px solid #1c2b42', borderRadius: '8px', overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ background: '#131c2e', borderBottom: '1px solid #1c2b42' }}>
                  <th style={{ padding: '10px 12px', fontWeight: 600, color: '#7a90b0', textAlign: 'left' }}>AHU ID</th>
                  <th style={{ padding: '10px 12px', fontWeight: 600, color: '#7a90b0', textAlign: 'left' }}>Health Index</th>
                  <th style={{ padding: '10px 12px', fontWeight: 600, color: '#7a90b0', textAlign: 'left' }}>PF Risk</th>
                  <th style={{ padding: '10px 12px', fontWeight: 600, color: '#7a90b0', textAlign: 'left' }}>Imbalance Risk</th>
                  <th style={{ padding: '10px 12px', fontWeight: 600, color: '#7a90b0', textAlign: 'left' }}>THD Risk</th>
                  <th style={{ padding: '10px 12px', fontWeight: 600, color: '#7a90b0', textAlign: 'left' }}>Overload Risk</th>
                </tr>
              </thead>
              <tbody style={{ borderLeft: '1px solid #1c2b42', borderRight: '1px solid #1c2b42' }}>
                {sortedAssessments.slice(0, 50).map((assessment) => (
                  <tr
                    key={assessment.ahu_id}
                    style={{
                      borderBottom: '1px solid #1c2b42',
                      cursor: 'pointer', transition: 'background-color 0.15s'
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = '#0f1a2e' }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                    onClick={() => loadAhuDetails(assessment.ahu_id)}
                  >
                    <td style={{ padding: '10px 12px', fontFamily: "'DM Mono', monospace" }}>
                      {assessment.ahu_id}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span className={`font-bold ${assessment.health_index >= 80 ? 'text-teal-400' : assessment.health_index >= 40 ? 'text-orange-400' : 'text-red-500'}`}>
                          {assessment.health_index.toFixed(1)}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <RiskBadge score={assessment.risk_scores.power_factor.score} />
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <RiskBadge score={assessment.risk_scores.phase_imbalance.score} />
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <RiskBadge score={assessment.risk_scores.thd_drift.score} />
                    </td>
                    <td style={{ padding: '10px 12px' }}>
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
