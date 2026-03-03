import { useState, useEffect, useCallback } from 'react'
import api from '../api.js'
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts'

// ──────────────────────────────────────────────────────────────────────────────
// Constants & Config
// ──────────────────────────────────────────────────────────────────────────────

const HEALTH_TIERS = {
  Healthy: { color: '#00c9b1', label: 'Healthy', min: 80, max: 100 },
  Monitor: { color: '#f5a623', label: 'Monitor', min: 60, max: 79 },
  Maintenance Soon: { color: '#f5734e', label: 'Maintenance Soon', min: 40, max: 59 },
  Critical: { color: '#ff4d6d', label: 'Critical', min: 0, max: 39 },
}

const LEVELS = [
  { value: '1', label: 'Level 1' },
  { value: '2', label: 'Level 2' },
  { value: '3', label: 'Level 3' },
  { value: '4', label: 'Level 4' },
  { value: '5', label: 'Level 5' },
  { value: '6', label: 'Level 6' },
  { value: '7', label: 'Level 7' },
  { value: '8', label: 'Level 8' },
  { value: '9', label: 'Level 9' },
  { value: '10', label: 'Level 10' },
  { value: '11', label: 'Level 11' },
]

const TIME_RANGES = ['24h', '7d', '30d']

// ──────────────────────────────────────────────────────────────────────────────
// FleetDashboard Component
// ──────────────────────────────────────────────────────────────────────────────

export default function FleetDashboard({ onBack }) {
  // State
  const [selectedLevel, setSelectedLevel] = useState('1')
  const [timeRange, setTimeRange] = useState('24h')
  const [highlightedAhu, setHighlightedAhu] = useState(null)
  const [trendData, setTrendData] = useState([])
  const [rankingData, setRankingData] = useState({ best: [], worst: [] })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // Load data on level or time range change
  const loadData = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      // Fetch ranking data (use 24h for fastest load)
      const rankingRes = await api.get('/dashboard/ranking', {
        params: { level: selectedLevel, time_range: 'last_24h' },
      })
      setRankingData({
        best: rankingRes.data.best || [],
        worst: rankingRes.data.worst || [],
      })

      // Fetch trend data
      const trendRes = await api.get('/dashboard/trend', {
        params: { level: selectedLevel, range: timeRange },
      })

      // Convert latest_snapshot to series format for Recharts
      if (trendRes.data.series && trendRes.data.series.length > 0) {
        setTrendData(trendRes.data.series)
      } else if (trendRes.data.latest_snapshot && trendRes.data.ahus) {
        // Build a single data point from latest snapshot for display
        const snapshot = trendRes.data.latest_snapshot
        setTrendData([{
          timestamp: new Date().toISOString(),
          ...Object.fromEntries(trendRes.data.ahus.map(ahu => [ahu, snapshot[ahu]])),
        }])
      } else {
        setTrendData([])
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load dashboard data')
    } finally {
      setIsLoading(false)
    }
  }, [selectedLevel, timeRange])

  // Initial load - non-blocking
  useEffect(() => {
    const timer = setTimeout(() => {
      loadData()
    }, 100)
    return () => clearTimeout(timer)
  }, [])

  // Handle AHU click - toggle highlight
  const handleAhuClick = useCallback((ahuId) => {
    setHighlightedAhu(prev => prev === ahuId ? null : ahuId)
  }, [])

  // Handle chart click - reset highlight
  const handleChartClick = useCallback(() => {
    setHighlightedAhu(null)
  }, [])

  // Get tier color for badge
  const getTierColor = (tier) => {
    switch (tier) {
      case 'Healthy': return { bg: '#00c9b115', border: '#00c9b135', text: '#00c9b1' }
      case 'Monitor': return { bg: '#f5a62315', border: '#f5a62335', text: '#f5a623' }
      case 'Maintenance Soon': return { bg: '#f5734e15', border: '#f5734e35', text: '#f5734e' }
      case 'Critical': return { bg: '#ff4d6d15', border: '#ff4d6d35', text: '#ff4d6d' }
      default: return { bg: '#7a90b015', border: '#7a90b035', text: '#7a90b0' }
    }
  }

  // Format timestamp based on time range
  const formatXAxis = (tick) => {
    if (!tick) return ''
    const date = new Date(tick)
    if (timeRange === '24h') {
      return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
    } else if (timeRange === '7d') {
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
      return `${days[date.getDay()]} ${date.getDate()}`
    } else {
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
      return `${date.getDate()} ${months[date.getMonth()]}`
    }
  }

  // Custom tooltip for chart
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: '#0d1424',
          border: '1px solid #1c2b42',
          borderRadius: '8px',
          padding: '10px 14px',
          boxShadow: 'var(--shadow-md)',
        }}>
          <div style={{ fontSize: '10px', color: '#3d526e', marginBottom: '8px' }}>
            {new Date(label).toLocaleString()}
          </div>
          {payload.map((entry, index) => {
            const ahuId = entry.name
            const value = entry.value
            let tier = 'Healthy'
            if (value < 40) tier = 'Critical'
            else if (value < 60) tier = 'Maintenance Soon'
            else if (value < 80) tier = 'Monitor'

            const tierColor = getTierColor(tier)

            return (
              <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: tierColor.color, flexShrink: 0 }} />
                <span style={{ fontFamily: "'DM Mono', monospace", fontSize: '11px', color: '#eaf0fb' }}>
                  {ahuId}
                </span>
                <span style={{ fontSize: '11px', color: '#7a90b0' }}>
                  {value} <span style={{ fontSize: '10px', color: tierColor.text }}>{tier}</span>
                </span>
              </div>
            )
          })}
        </div>
      )
    }
    return null
  }

  // Get chart data keys (AHUs) - limit to first 8 for legend
  const chartDataKeys = trendData.length > 0 ? Object.keys(trendData[0]).filter(k => k !== 'timestamp') : []
  const displayedAhus = chartDataKeys.slice(0, 8)
  const hiddenCount = Math.max(0, chartDataKeys.length - 8)

  // Get line opacity for an AHU
  const getLineOpacity = (ahuId) => {
    if (!highlightedAhu) return 0.6
    return ahuId === highlightedAhu ? 1.0 : 0.15
  }

  const getLineWidth = (ahuId) => {
    if (!highlightedAhu) return 1.5
    return ahuId === highlightedAhu ? 3 : 1.5
  }

  // Level options for dropdown
  const levelOptions = LEVELS.map(l => (
    <option key={l.value} value={l.value}>
      {l.label}
    </option>
  ))

  // Render error screen
  if (error) {
    return (
      <div className="chat-view" style={{ display: 'flex', flexDirection: 'column' }}>
        <div className="thread">
          <div className="thread-inner" style={{ padding: '40px 32px' }}>
            <div className="turn turn-error">
              <div className="assistant-bubble error-bubble" style={{ maxWidth: '100%' }}>
                <div className="mb-3">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ff4d6d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="15" y1="9" x2="9" y2="15" />
                    <line x1="9" y1="9" x2="15" y2="15" />
                  </svg>
                </div>
                <p style={{ fontWeight: 600, marginBottom: '8px' }}>Error</p>
                <p style={{ whiteSpace: 'pre-wrap' }}>{error}</p>
                <button
                  onClick={() => { setError(null); loadData() }}
                  style={{
                    marginTop: '12px',
                    padding: '8px 16px',
                    background: '#00c9b115',
                    border: '1px solid #00c9b35',
                    borderRadius: '6px',
                    color: '#00c9b1',
                    fontWeight: 500,
                    cursor: 'pointer',
                  }}
                >
                  Try Again
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-view" style={{ display: 'flex', flexDirection: 'column' }}>
      {/* Loading Overlay */}
      {isLoading && trendData.length === 0 && (
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(13, 20, 36, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
        }}>
          <div style={{
            background: '#1a253a',
            padding: '24px 40px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            boxShadow: 'var(--shadow-lg)',
          }}>
            <div className="skeleton" style={{ width: '40px', height: '40px', borderRadius: '8px' }} />
            <div style={{ color: '#7a90b0', fontSize: '14px' }}>
              Loading fleet data...
            </div>
          </div>
        </div>
      )}

      {/* Dashboard Header */}
      <div style={{
        padding: '20px 32px 16px',
        background: 'linear-gradient(180deg, #0d1424 0%, #0a1120 100%)',
        borderBottom: '1px solid var(--border)',
      }}>
        {/* Back Button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
          <button
            onClick={onBack}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: '20px',
              padding: '6px 14px',
              color: '#7a90b0',
              fontFamily: "'DM Mono', monospace",
              fontSize: '11px',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 0.18s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = '#00c9b1'
              e.currentTarget.style.color = '#00c9b1'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border)'
              e.currentTarget.style.color = '#7a90b0'
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Back to Chat
          </button>
        </div>

        {/* Header Controls */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '24px',
          flexWrap: 'wrap',
        }}>
          {/* Level Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <label style={{
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: '#7a90b0',
            }}>
              Level
            </label>
            <select
              value={selectedLevel}
              onChange={(e) => setSelectedLevel(e.target.value)}
              style={{
                background: '#0d1424',
                border: '1px solid var(--border-bright)',
                borderRadius: '8px',
                padding: '6px 12px',
                color: '#eaf0fb',
                fontFamily: "'DM Mono', monospace",
                fontSize: '12px',
                fontWeight: 500,
                cursor: 'pointer',
                outline: 'none',
              }}
            >
              {levelOptions}
            </select>
          </div>

          {/* Time Range Toggle */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            background: '#0d1424',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '4px',
          }}>
            {TIME_RANGES.map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                style={{
                  padding: '6px 14px',
                  border: 'none',
                  background: timeRange === range ? '#00c9b1' : 'transparent',
                  color: timeRange === range ? '#080c18' : '#7a90b0',
                  borderRadius: '6px',
                  fontFamily: "'DM Mono', monospace",
                  fontSize: '10px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.18s',
                }}
              >
                {range.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '280px 1fr',
        gap: '24px',
        flex: 1,
        overflow: 'hidden',
        padding: '0 32px 40px',
      }}>
        {/* Left Panel - Top 5 Lists */}
        <div style={{
          background: '#0d1424',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          overflowY: 'auto',
        }}>
          {/* Top 5 Healthiest */}
          <div style={{
            borderBottom: '1px solid var(--border)',
            padding: '20px',
          }}>
            <div style={{
              fontSize: '9px',
              fontWeight: 700,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: '#3d526e',
              marginBottom: '14px',
            }}>
              Top 5 Healthiest
            </div>
            {rankingData.best.length === 0 ? (
              <div style={{
                padding: '24px',
                textAlign: 'center',
                color: '#7a90b0',
                fontSize: '12px',
              }}>
                No health data available
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {rankingData.best.map((ahu, idx) => {
                  const tierColor = getTierColor(ahu.tier)
                  return (
                    <div
                      key={idx}
                      onClick={() => handleAhuClick(ahu.ahu_id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        padding: '12px 14px',
                        background: highlightedAhu === ahu.ahu_id ? '#00c9b108' : 'transparent',
                        border: highlightedAhu === ahu.ahu_id ? `1px solid ${tierColor.color}` : '1px solid var(--border)',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        transition: 'all 0.15s',
                      }}
                      onMouseEnter={(e) => {
                        if (highlightedAhu === ahu.ahu_id) {
                          e.currentTarget.style.background = '#00c9b115'
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (highlightedAhu === ahu.ahu_id) {
                          e.currentTarget.style.background = '#00c9b108'
                        }
                      }}
                    >
                      <span style={{
                        width: '24px',
                        height: '24px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: idx === 0 ? '#00c9b1' : idx === 1 ? '#7a90b0' : idx === 2 ? '#3d526e' : 'var(--border)',
                        borderRadius: '6px',
                        color: idx === 0 ? '#080c18' : idx === 1 ? '#eaf0fb' : idx === 2 ? '#7a90b0' : '#3d526e',
                        fontSize: '11px',
                        fontWeight: 700,
                        flexShrink: 0,
                      }}>
                        {idx + 1}
                      </span>
                      <div style={{ flex: 1, overflow: 'hidden' }}>
                        <div style={{
                          fontFamily: "'DM Mono', monospace",
                          fontSize: '13px',
                          color: '#eaf0fb',
                          fontWeight: 500,
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}>
                          {ahu.ahu_id}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{
                          fontSize: '16px',
                          fontWeight: 700,
                          color: tierColor.color,
                          fontFamily: "'DM Mono', monospace",
                        }}>
                          {ahu.index}
                        </div>
                      </div>
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '12px',
                        border: `1px solid ${tierColor.border}`,
                        background: tierColor.bg,
                        color: tierColor.text,
                        fontSize: '9px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        whiteSpace: 'nowrap',
                      }}>
                        {ahu.tier}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Top 5 Needs Attention */}
          <div style={{ padding: '20px' }}>
            <div style={{
              fontSize: '9px',
              fontWeight: 700,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: '#3d526e',
              marginBottom: '14px',
            }}>
              Top 5 Needs Attention
            </div>
            {rankingData.worst.length === 0 ? (
              <div style={{
                padding: '24px',
                textAlign: 'center',
                color: '#7a90b0',
                fontSize: '12px',
              }}>
                No health data available
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {rankingData.worst.map((ahu, idx) => {
                  const tierColor = getTierColor(ahu.tier)
                  return (
                    <div
                      key={idx}
                      onClick={() => handleAhuClick(ahu.ahu_id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        padding: '12px 14px',
                        background: highlightedAhu === ahu.ahu_id ? '#ff4d6d08' : 'transparent',
                        border: highlightedAhu === ahu.ahu_id ? `1px solid ${tierColor.color}` : '1px solid var(--border)',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        transition: 'all 0.15s',
                      }}
                      onMouseEnter={(e) => {
                        if (highlightedAhu === ahu.ahu_id) {
                          e.currentTarget.style.background = '#ff4d6d15'
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (highlightedAhu === ahu.ahu_id) {
                          e.currentTarget.style.background = '#ff4d6d08'
                        }
                      }}
                    >
                      <span style={{
                        width: '24px',
                        height: '24px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: idx === 0 ? '#ff4d6d' : idx === 1 ? '#f5734e' : idx === 2 ? '#f5a623' : 'var(--border)',
                        borderRadius: '6px',
                        color: idx === 0 ? '#eaf0fb' : idx === 1 ? '#eaf0fb' : idx === 2 ? '#080c18' : '#3d526e',
                        fontSize: '11px',
                        fontWeight: 700,
                        flexShrink: 0,
                      }}>
                        {idx + 1}
                      </span>
                      <div style={{ flex: 1, overflow: 'hidden' }}>
                        <div style={{
                          fontFamily: "'DM Mono', monospace",
                          fontSize: '13px',
                          color: '#eaf0fb',
                          fontWeight: 500,
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}>
                          {ahu.ahu_id}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{
                          fontSize: '16px',
                          fontWeight: 700,
                          color: tierColor.color,
                          fontFamily: "'DM Mono', monospace",
                        }}>
                          {ahu.index}
                        </div>
                      </div>
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '12px',
                        border: `1px solid ${tierColor.border}`,
                        background: tierColor.bg,
                        color: tierColor.text,
                        fontSize: '9px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        whiteSpace: 'nowrap',
                      }}>
                        {ahu.tier}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Area - Chart */}
        <div style={{
          background: '#0d1424',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          padding: '20px',
          position: 'relative',
        }}>
          {/* Chart Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '20px',
          }}>
            <div>
              <h3 style={{
                fontSize: '12px',
                fontWeight: 700,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: '#7a90b0',
              }}>
                Health Index Trend
              </h3>
              <p style={{
                fontSize: '10px',
                color: '#3d526e',
                marginTop: '4px',
              }}>
                Level {selectedLevel} · Top 5 Healthiest AHUs
              </p>
            </div>
          </div>

          {/* Chart Container */}
          <ResponsiveContainer width="100%" height={320}>
            {trendData.length > 0 ? (
              <ComposedChart
                data={trendData}
                onClick={handleChartClick}
                margin={{ top: 20, right: 20, bottom: 40, left: 10 }}
              >
                <CartesianGrid
                  stroke="#1c2b42"
                  strokeOpacity={0.15}
                  vertical={false}
                />
                <XAxis
                  dataKey="timestamp"
                  type="category"
                  tick={formatXAxis}
                  axisLine={{ stroke: '#1c2b42' }}
                  tickLine={{ stroke: '#1c2b42' }}
                  tick={{ fontSize: '10px', fill: '#7a90b0' }}
                />
                <YAxis
                  domain={[0, 100]}
                  axisLine={{ stroke: '#1c2b42' }}
                  tickLine={{ stroke: '#1c2b42' }}
                  tick={{ fontSize: '10px', fill: '#7a90b0' }}
                />
                <Tooltip content={<CustomTooltip />} />

                {/* Reference lines at tier boundaries */}
                <ReferenceLine y={40} stroke="#ff4d6d" strokeDasharray="3 3" strokeOpacity={0.25} />
                <ReferenceLine y={60} stroke="#f5a623" strokeDasharray="3 3" strokeOpacity={0.25} />
                <ReferenceLine y={80} stroke="#00c9b1" strokeDasharray="3 3" strokeOpacity={0.25} />

                {/* Lines for each AHU */}
                {displayedAhus.map((ahuId, index) => (
                  <Line
                    key={ahuId}
                    type="monotone"
                    dataKey={ahuId}
                    stroke="#7a90b0"
                    strokeWidth={getLineWidth(ahuId)}
                    opacity={getLineOpacity(ahuId)}
                    activeDot={{ r: 4, strokeWidth: 0 }}
                    dot={{ r: 2 }}
                  />
                ))}

                {/* Legend */}
                {displayedAhus.length > 0 && (
                  <Legend
                    layout="horizontal"
                    verticalAlign="bottom"
                    align="center"
                    iconType="circle"
                    wrapperStyle={{
                      marginTop: '16px',
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '12px 20px',
                      fontSize: '10px',
                    }}
                  >
                    {displayedAhus.map((ahuId, index) => {
                      const tierColor = getTierColor(rankingData.best.find(b => b.ahu_id === ahuId)?.tier || 'Healthy')
                      const isHighlighted = highlightedAhu === ahuId

                      return (
                        <div
                          key={ahuId}
                          onClick={() => handleAhuClick(ahuId)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            cursor: 'pointer',
                            opacity: isHighlighted ? 1 : (highlightedAhu ? 0.25 : 1),
                            transition: 'opacity 0.2s',
                          }}
                        >
                          <span style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            background: tierColor.color,
                          }} />
                          <span style={{ fontFamily: "'DM Mono', monospace", color: '#7a90b0' }}>
                            {ahuId}
                          </span>
                        </div>
                      )
                    })}

                    {/* Show "and N more" if hidden count > 0 */}
                    {hiddenCount > 0 && (
                      <span style={{ fontFamily: "'DM Mono', monospace", color: '#3d526e' }}>
                        and {hiddenCount} more
                      </span>
                    )}
                  </Legend>
                )}
              </ComposedChart>
            ) : (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: '#7a90b0',
              }}>
                No trend data available
              </div>
            )}
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
