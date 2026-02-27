import { useState, useEffect, useCallback, useMemo } from 'react'
import api from '../api.js'
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts'
import { buildSummary, buildWorstDevicesList, buildThresholdEvents } from '../lib/summaryGenerator'

// ──────────────────────────────────────────────────────────────────────────────
// Constants & Config
// ──────────────────────────────────────────────────────────────────────────────

const COMPONENT_CONFIG = {
  health_index: {
    label: 'Health Index',
    weight: null,
    min: 0, max: 100,
    unit: '',
    thresholdLines: [
      { value: 80, label: 'Healthy', color: '#00c9b145' },
      { value: 60, label: 'Monitor', color: '#f5a62345' },
      { value: 40, label: 'Maint.', color: '#f5734e45' },
    ]
  },
  energy_anomaly: {
    label: 'Energy Anomaly',
    weight: 0.15,
    min: 0, max: 1,
    unit: '',
    thresholdLines: [
      { value: 0.6, label: 'High', color: '#ff4d6d45' },
      { value: 0.3, label: 'Elev.', color: '#f5a62345' },
    ]
  },
  pf_degradation: {
    label: 'PF Degradation',
    weight: 0.25,
    min: 0, max: 1,
    unit: '',
    thresholdLines: [
      { value: 0.6, label: 'High', color: '#ff4d6d45' },
      { value: 0.3, label: 'Elev.', color: '#f5a62345' },
    ]
  },
  phase_imbalance: {
    label: 'Phase Imbalance',
    weight: 0.25,
    min: 0, max: 1,
    unit: '',
    thresholdLines: [
      { value: 0.6, label: 'High', color: '#ff4d6d45' },
      { value: 0.3, label: 'Elev.', color: '#f5a62345' },
    ]
  },
  thd_drift: {
    label: 'THD Drift',
    weight: 0.15,
    min: 0, max: 1,
    unit: '',
    thresholdLines: [
      { value: 0.6, label: 'High', color: '#ff4d6d45' },
      { value: 0.3, label: 'Elev.', color: '#f5a62345' },
    ]
  },
  overload: {
    label: 'Overload',
    weight: 0.20,
    min: 0, max: 1,
    unit: '',
    thresholdLines: [
      { value: 0.6, label: 'High', color: '#ff4d6d45' },
      { value: 0.3, label: 'Elev.', color: '#f5a62345' },
    ]
  },
}

const TIER_COLORS = {
  Healthy: '#00c9b1',
  Monitor: '#f5a623',
  MaintenanceSoon: '#f5734e',
  Critical: '#ff4d6d',
}

// Distinct colors for AHU lines - using vibrant, distinguishable palette
const AHU_COLORS = [
  '#00c9b1', // Teal
  '#f5a623', // Orange
  '#7b68e0', // Purple
  '#ff6b6b', // Red
  '#ffd93d', // Yellow
  '#6bc7f5', // Light Blue
  '#ff8e53', // Deep Orange
  '#00b2a9', // Dark Teal
  '#ee8d57', // Amber
  '#9b5de5', // Violet
  '#f15bb5', // Pink
  '#00bbd9', // Cyan
  '#fee440', // Bright Yellow
  '#5e548e', // Slate Purple
  '#b33939', // Brick Red
  '#3f7e4d', // Forest Green
  '#0e6eb8', // Navy Blue
  '#9d4edd', // Lavender
  '#ff9f1c', // Amber Orange
  '#2ec4b6', // Turquoise
]

// ──────────────────────────────────────────────────────────────────────────────
// Helper Functions
// ──────────────────────────────────────────────────────────────────────────────

function getAhuTier(value) {
  if (value == null || isNaN(value)) return 'Healthy'
  if (value < 40) return 'Critical'
  if (value < 60) return 'MaintenanceSoon'
  if (value < 80) return 'Monitor'
  return 'Healthy'
}

// Helper to get value for an AHU from data (long format: find by ahu_id, then get metric)
function getAhuValue(row, ahuId, metricKey) {
  if (!row || !ahuId) return null
  // Long format: value stored in ahu_id column, metricKey is the value column
  if ('ahu_id' in row && row.ahu_id === ahuId) {
    return row[metricKey]
  }
  // Wide format: value stored directly in column named after AHU
  return row[ahuId]
}

function formatXAxis(tick, timeRange) {
  if (!tick) return ''
  const date = new Date(tick)
  if (timeRange === '24h') {
    return date.toLocaleTimeString('en-US', { hour: 'numeric' })
  } else if (timeRange === '7d') {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    return `${days[date.getDay()]} ${date.getDate()}`
  } else {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return `${date.getDate()} ${months[date.getMonth()]}`
  }
}

function formatYAxisTick(value, config) {
  if (config.min === 0 && config.max === 100) {
    return Math.round(value)
  }
  if (config.min === 0 && config.max === 1) {
    return (value * 100).toFixed(0) + '%'
  }
  return value.toFixed(2)
}

// ──────────────────────────────────────────────────────────────────────────────
// Transform long-format CSV to wide format for charts
// Long: [{timestamp, ahu_id, health_index}, ...]
// Wide: [{timestamp, e0101, e0102, ...}, ...]
function transformToWideFormat(longData, metricKey) {
  if (!longData || longData.length === 0) return []

  // Get unique timestamps
  const timestamps = [...new Set(longData.map(row => row.timestamp))].sort()

  // Get unique AHU IDs
  const ahuIds = [...new Set(longData.map(row => row.ahu_id))].sort()

  // Transform to wide format
  const wideData = timestamps.map(ts => {
    const row = { timestamp: ts }

    longData.filter(row => row.timestamp === ts).forEach(dataRow => {
      const ahuId = dataRow.ahu_id
      // Add metric value as AHU column (e.g., health_index, energy_anomaly, etc.)
      row[ahuId] = dataRow[metricKey]
    })

    return row
  })

  return wideData
}

// ──────────────────────────────────────────────────────────────────────────────
// Single Chart Component - Long Format Data Support
// ──────────────────────────────────────────────────────────────────────────────

function HealthChart({
  data,
  ahuIds,
  highlightedAhu,
  metricKey,
  timeRange,
  onAhuClick,
}) {
  const config = COMPONENT_CONFIG[metricKey]
  const isHealthIndex = metricKey === 'health_index'

  // For long-format data, check if we have the ahu_id column
  const hasAhuIdColumn = data && data.length > 0 && 'ahu_id' in data[0]
  
  // Transform long-format data to wide format for the chart
  // Long: [{timestamp, ahu_id, health_index}, ...]
  // Wide: [{timestamp, e0101, e0102, ...}, ...]
  const chartData = hasAhuIdColumn ? transformToWideFormat(data, metricKey) : (data || [])
  
  // Safety: ensure chartData is an array
  const safeChartData = Array.isArray(chartData) ? chartData : []
  
  // Get relevant AHUs from chart data (wide format has AHU IDs as column names)
  const safeAhuIds = Array.isArray(ahuIds) ? ahuIds : []
  const relevantAhuIds = safeAhuIds.filter(ahu =>
    safeChartData.some(row => row && row[ahu] !== undefined && row[ahu] !== null && row[ahu] !== '')
  )

  // Early return if no data to render
  if (safeChartData.length === 0 || relevantAhuIds.length === 0) {
    return (
      <div style={{
        background: '#0d1424',
        border: '1px solid var(--border)',
        borderRadius: '12px',
        padding: '40px 32px',
      }}>
        <div style={{ color: '#7a90b0', textAlign: 'center' }}>
          No data available
        </div>
      </div>
    )
  }

  return (
    <div style={{
      background: '#0d1424',
      border: '1px solid var(--border)',
      borderRadius: '12px',
      padding: '20px',
    }}>
      {/* Chart Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <h4 style={{
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: '#7a90b0',
          }}>
            {config.label}
          </h4>
          {config.weight && (
            <span style={{
              fontSize: '8px',
              color: '#3d526e',
            }}>
              (weight {config.weight})
            </span>
          )}
        </div>
      </div>

      {/* Chart Container */}
      <ResponsiveContainer width="100%" height={200}>
        {chartData.length > 0 && relevantAhuIds.length > 0 ? (
          <ComposedChart
            data={chartData}
            onClick={() => onAhuClick(null)}
          >
            <CartesianGrid
              stroke="#1c2b42"
              strokeOpacity={0.15}
              vertical={false}
            />
            
            {/* Reference Lines for thresholds */}
            {config.thresholdLines.map((line, idx) => (
              <ReferenceLine
                key={idx}
                y={line.value}
                stroke={line.color}
                label={{
                  value: line.label,
                  position: 'right',
                  fill: line.color,
                  fontSize: 9,
                }}
              />
            ))}

            {/* X Axis */}
            <XAxis
              dataKey="timestamp"
              type="category"
              tick={(props) => (
                <text
                  {...props}
                  transform={`rotate(0, ${props.x}, ${props.y + 12})`}
                  textAnchor="middle"
                  fill="#7a90b0"
                  fontSize={10}
                >
                  {formatXAxis(props.payload.value, timeRange)}
                </text>
              )}
              axisLine={{ stroke: '#1c2b42' }}
              tickLine={{ stroke: '#1c2b42' }}
            />

            {/* Y Axis */}
            <YAxis
              domain={[config.min, config.max]}
              tick={(props) => (
                <text
                  {...props}
                  transform={`rotate(0, ${props.x + 12}, ${props.y})`}
                  textAnchor="start"
                  fill="#7a90b0"
                  fontSize={10}
                >
                  {formatYAxisTick(props.payload.value, config)}
                </text>
              )}
              axisLine={{ stroke: '#1c2b42' }}
              tickLine={{ stroke: '#1c2b42' }}
              width={50}
            />

            {/* Tooltip */}
            <Tooltip
              content={(props) => {
                if (!props.active || !props.payload || props.payload.length === 0) return null
                return (
                  <div style={{
                    background: '#0d1424',
                    border: '1px solid #1c2b42',
                    borderRadius: '8px',
                    padding: '10px 14px',
                  }}>
                    <div style={{
                      fontSize: '10px',
                      color: '#3d526e',
                      marginBottom: '8px',
                    }}>
                      {new Date(props.label).toLocaleString()}
                    </div>
                    {props.payload.map((entry, idx) => {
                      const ahuId = entry.name
                      const value = entry.value
                      let tier = getAhuTier(value)

                      return (
                        <div key={idx} style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          marginBottom: '4px',
                        }}>
                          <span style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            background: TIER_COLORS[tier] || '#7a90b0',
                            flexShrink: 0,
                          }} />
                          <span style={{
                            fontFamily: "'DM Mono', monospace",
                            fontSize: '11px',
                            color: '#eaf0fb',
                          }}>
                            {ahuId}
                          </span>
                          <span style={{
                            fontSize: '11px',
                            color: '#7a90b0',
                          }}>
                            {value}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                )
              }}
            />

            {/* Legend */}
            <Legend
              verticalAlign="bottom"
              height={36}
              formatter={(value) => {
                const isHighlighted = highlightedAhu !== null
                return (
                  <span
                    onClick={() => onAhuClick(value)}
                    style={{
                      color: isHighlighted && value !== highlightedAhu ? '#7a90b066' : '#eaf0fb',
                      fontSize: '10px',
                      fontFamily: "'DM Mono', monospace",
                      cursor: 'pointer',
                      opacity: isHighlighted && value !== highlightedAhu ? 0.3 : 1,
                    }}
                  >
                    {value}
                  </span>
                )
              }}
            />

            {/* Lines for each AHU */}
            {relevantAhuIds.map((ahuId, idx) => {
              // Assign unique color to each AHU from the palette
              const lineColor = AHU_COLORS[idx % AHU_COLORS.length]
              const isHighlighted = highlightedAhu !== null
              return (
                <Line
                  key={ahuId}
                  type="monotone"
                  dataKey={ahuId}
                  stroke={lineColor}
                  strokeWidth={isHighlighted && ahuId !== highlightedAhu ? 1 : 2}
                  strokeOpacity={isHighlighted && ahuId !== highlightedAhu ? 0.15 : 0.8}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              )
            })}
          </ComposedChart>
        ) : (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: 200,
            color: '#7a90b0',
          }}>
            No data available
          </div>
        )}
      </ResponsiveContainer>
    </div>
  )
}

// ──────────────────────────────────────────────────────────────────────────────
// Main Dashboard Component
// ──────────────────────────────────────────────────────────────────────────────

export default function AhuHealthTrendDashboard({ onBack }) {
  // State
  const [selectedLevel, setSelectedLevel] = useState('1')
  const [timeRange, setTimeRange] = useState('24h')
  const [highlightedAhu, setHighlightedAhu] = useState(null)
  const [allData, setAllData] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // Load data from pre-generated CSV file
  const loadData = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      console.log('[Dashboard] Loading CSV data...')
      // Map timeRange to corresponding FAIR scoring CSV file
      const csvFileMap = {
        '24h': '/level1_hourly_health_24h.csv',
        '7d': '/level1_hourly_health_7d.csv', 
        '30d': '/level1_hourly_health_30d.csv'
      }
      const cacheBuster = Date.now()
      const csvFileBase = csvFileMap[timeRange] || '/level1_health_data.csv'
      const csvFile = `${csvFileBase}?t=${cacheBuster}`
      
      console.log('[Dashboard] Loading:', csvFile)
      const response = await fetch(csvFile, { cache: 'no-store' })
      console.log('[Dashboard] Response status:', response.status, response.ok)
      
      if (response.ok) {
        const csvText = await response.text()
        let rows = parseCsv(csvText)
        console.log('[Dashboard] CSV parsed, rows:', rows.length)
        
        // Filter by selected level
        if (rows.length > 0 && 'level' in rows[0]) {
          const levelPrefix = `Level ${selectedLevel}`
          console.log('[Dashboard] Filtering by level:', levelPrefix)
          rows = rows.filter(row => row.level === levelPrefix)
          console.log('[Dashboard] After filter, rows:', rows.length)
        }
        
        setAllData(rows)
      } else {
        console.log('[Dashboard] CSV not found, trying API fallback...')
        // Fallback to API if CSV not found
        const res = await api.get('/dashboard/trend/csv', {
          params: { level: selectedLevel, range: timeRange },
        })
        if (res.data && res.data.csv_content) {
          const rows = parseCsv(res.data.csv_content)
          setAllData(rows)
        } else if (res.data && res.data.series) {
          setAllData(res.data.series)
        } else {
          setAllData([])
        }
      }
    } catch (err) {
      console.error('[Dashboard] Error loading health data:', err)
      setError('Failed to load dashboard data. Please check console for details.')
    } finally {
      setIsLoading(false)
    }
  }, [selectedLevel, timeRange])

  // Parse CSV string to array of objects
  function parseCsv(csvStr) {
    const lines = csvStr.trim().split('\n')
    if (lines.length < 2) return []

    const headers = lines[0].split(',')
    const data = []

    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',')
      if (values.length < headers.length) continue

      const row = {}
      headers.forEach((header, idx) => {
        row[header.trim()] = values[idx] ? values[idx].trim() : null
      })
      data.push(row)
    }

    return data
  }

  // Initial load
  useEffect(() => {
    const timer = setTimeout(() => {
      loadData()
    }, 100)
    return () => clearTimeout(timer)
  }, [])

  // Get unique AHU IDs from data
  // Long format CSV: columns are timestamp, ahu_id, level, health_index, ...
  // Need to extract unique values from 'ahu_id' column
  const allAhuIds = allData.length > 0 && 'ahu_id' in allData[0]
    ? [...new Set(allData.map(row => row.ahu_id))].filter(id => id != null && typeof id === 'string').sort()
    : []

  // Filter AHU IDs based on selected level (Level 1 = e01 prefix)
  const ahuIds = allAhuIds.filter(ahuId => {
    if (!ahuId || typeof ahuId !== 'string') return false
    // Level 1 devices start with 'e01'
    const levelPrefix = `e${String(selectedLevel).padStart(2, '0')}`
    return ahuId.startsWith(levelPrefix)
  })

  // Map normalized column names back to original (no longer needed - columns match)
  const chartMetricKeyMap = {}

  // Memoized summary generation
  const summaries = useMemo(() => {
    if (!allData || allData.length === 0 || !ahuIds || ahuIds.length === 0) {
      return {}
    }
    
    const result = {}
    const metrics = ['health_index', 'energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload']
    
    for (const metricKey of metrics) {
      result[metricKey] = buildSummary(
        metricKey,
        allData,
        ahuIds,
        highlightedAhu,
        timeRange
      )
    }
    
    return result
  }, [allData, ahuIds, highlightedAhu, timeRange])

  // Memoized worst devices list
  const worstDevicesLists = useMemo(() => {
    if (!allData || allData.length === 0 || !ahuIds || ahuIds.length === 0) {
      return {}
    }
    
    const result = {}
    const metrics = ['health_index', 'energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload']
    
    for (const metricKey of metrics) {
      result[metricKey] = buildWorstDevicesList(metricKey, allData, ahuIds)
    }
    
    return result
  }, [allData, ahuIds])

  // Handle AHU click
  const handleAhuClick = useCallback((ahuId) => {
    setHighlightedAhu(prev => prev === ahuId ? null : ahuId)
  }, [])

  // Level options
  const levelOptions = Array.from({ length: 11 }, (_, i) => (
    <option key={i + 1} value={String(i + 1)}>
      Level {i + 1}
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
      {isLoading && allData.length === 0 && (
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
              Loading health trend data...
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
            {['24h', '7d', '30d'].map((range) => (
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

        {/* Pill Row - Device Selection */}
        <div style={{
          marginTop: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap',
        }}>
          <span style={{
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: '#7a90b0',
          }}>
            Devices:
          </span>
          {ahuIds.map((ahuId, idx) => {
            // Get latest value for this AHU to determine tier
            // Long format: find row where ahu_id matches, get health_index value
            const latest = allData.find(d => d.ahu_id === ahuId)
            // For long format CSV, get health_index from the matched row
            const value = latest && latest.health_index ? parseFloat(latest.health_index) : null
            const tier = getAhuTier(value)
            // Use AHU-specific color from palette
            const ahuColor = AHU_COLORS[idx % AHU_COLORS.length]
            const tierColor = TIER_COLORS[tier] || ahuColor
            const bg = highlightedAhu === ahuId ? `${ahuColor}25` : '#0d1424'
            const border = highlightedAhu === ahuId ? `1px solid ${ahuColor}` : '1px solid var(--border)'
            const color = highlightedAhu === ahuId ? ahuColor : '#7a90b0'
            const opacity = highlightedAhu !== null && ahuId !== highlightedAhu ? 0.3 : 1

            return (
              <span
                key={ahuId}
                onClick={() => handleAhuClick(ahuId)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '4px 10px',
                  background: bg,
                  border: border,
                  borderRadius: '16px',
                  color: color,
                  fontFamily: "'DM Mono', monospace",
                  fontSize: '10px',
                  fontWeight: highlightedAhu === ahuId ? 600 : 500,
                  cursor: 'pointer',
                  opacity: opacity,
                  transition: 'all 0.18s',
                }}
              >
                <span 
                  style={{ 
                    width: '6px', 
                    height: '6px', 
                    borderRadius: '50%', 
                    background: ahuColor,
                  }} 
                />
                {ahuId}
              </span>
            )
          })}
        </div>
      </div>

      {/* Charts Grid - 3 columns: Summary | Chart | Right Panel */}
      <div style={{
        padding: '24px 32px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        overflowY: 'auto',
      }}>
        {/* Metrics Array for 3-column rows */}
        {['health_index', 'energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload'].map((metricKey) => {
          const config = COMPONENT_CONFIG[metricKey]
          const summaryText = summaries[metricKey] || ''
          const worstDevices = worstDevicesLists[metricKey]
          
          // Get metric-specific color for left panel accent
          const getMetricColor = (key) => {
            if (key === 'health_index') return '#00c9b1' // Teal
            if (key === 'energy_anomaly') return '#ff6b6b' // Red
            if (key === 'pf_degradation') return '#f5a623' // Orange
            if (key === 'phase_imbalance') return '#ffd93d' // Yellow
            if (key === 'thd_drift') return '#6bc7f5' // Light Blue
            if (key === 'overload') return '#ff8e53' // Deep Orange
            return '#7a90b0'
          }
          
          const metricColor = getMetricColor(metricKey)
          
          return (
            <div
              key={metricKey}
              style={{
                display: 'grid',
                gridTemplateColumns: '220px 1fr 240px',
                gap: '16px',
                padding: '16px 0',
                borderBottom: `1px solid #1c2b42`,
              }}
            >
              {/* Left Panel: Contextual Summary */}
              <div style={{
                borderLeft: `3px solid ${metricColor}`,
                paddingLeft: '12px',
              }}>
                <div style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  color: '#7a90b0',
                  marginBottom: '8px',
                }}>
                  {config.label}
                </div>
                <div style={{
                  fontSize: '12px',
                  color: '#eaf0fb',
                  lineHeight: '1.6',
                }}>
                  {summaryText}
                </div>
              </div>

              {/* Center: Chart */}
              <HealthChart
                data={allData}
                ahuIds={ahuIds}
                highlightedAhu={highlightedAhu}
                metricKey={chartMetricKeyMap[metricKey] || metricKey}
                timeRange={timeRange}
                onAhuClick={handleAhuClick}
              />

              {/* Right Panel: Worst Devices or Threshold Events */}
              <div style={{
                paddingLeft: '12px',
              }}>
                {highlightedAhu ? (
                  // Mode B: Single device focused - threshold events
                  <div>
                    <div style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      letterSpacing: '0.1em',
                      textTransform: 'uppercase',
                      color: '#7a90b0',
                      marginBottom: '8px',
                    }}>
                      Threshold Events
                    </div>
                    {(() => {
                      const eventsResult = buildThresholdEvents(metricKey, allData, highlightedAhu)
                      return (
                        <div style={{
                          fontSize: '12px',
                          color: '#eaf0fb',
                          lineHeight: '1.6',
                        }}>
                          {eventsResult.events && eventsResult.events.length > 0 ? (
                            <ul style={{
                              margin: '0',
                              paddingLeft: '16px',
                              fontSize: '12px',
                            }}>
                              {eventsResult.events.map((evt, idx) => (
                                <li key={idx} style={{ marginBottom: '4px' }}>
                                  {evt.type === 'worsening' ? (
                                    <span style={{ color: '#ff4d6d' }}>▼</span>
                                  ) : evt.type === 'improving' ? (
                                    <span style={{ color: '#00c9b1' }}>▲</span>
                                  ) : null}
                                  {evt.date} — {evt.message}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <div style={{ color: '#7a90b0', fontStyle: 'italic' }}>
                              No threshold crossings in this period
                            </div>
                          )}
                        </div>
                      )
                    })()}
                  </div>
                ) : (
                  // Mode A: Broad view - worst devices
                  <div>
                    <div style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      letterSpacing: '0.1em',
                      textTransform: 'uppercase',
                      color: '#7a90b0',
                      marginBottom: '8px',
                    }}>
                      {worstDevices ? worstDevices.label : 'Needs Attention'}
                    </div>
                    <div style={{
                      fontSize: '12px',
                      fontFamily: "'DM Mono', monospace",
                      color: '#eaf0fb',
                    }}>
                      {worstDevices && worstDevices.devices.length > 0 ? (
                        <div>
                          {worstDevices.devices.map((device, idx) => (
                            <span
                              key={idx}
                              style={{
                                marginRight: '8px',
                                color: device.value != null && (device.value >= 0.6 || device.value < 80) ? '#ff4d6d' : undefined,
                              }}
                            >
                              {device.text || `${device.ahuId} (${device.value})`}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span style={{ color: '#00c9b1' }}>
                          All devices within normal range ✓
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
