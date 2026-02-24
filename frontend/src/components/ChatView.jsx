import { useState, useRef, useEffect } from 'react'
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, ReferenceLine,
  LineChart, BarChart, Bar,
} from 'recharts'
import { getDeviceLabel, getDeviceDetail, isMapped } from '../deviceMap.js'

// ── Categorised example queries ───────────────────────────────────────────────
const EXAMPLE_CATEGORIES = [
  {
    label: '🔮 Predictions',
    type: 'forecast',
    queries: [
      { label: 'Forecast e0202 — Child Development Centre (L02)', deviceId: 'e0202' },
      { label: 'Forecast e0207 — Medical Social Services (L02)',  deviceId: 'e0207' },
      { label: 'Forecast e0211 — Post Graduate Medical Centre (L03)', deviceId: 'e0211' },
    ],
  },
  {
    label: '⚡ Power Comparisons',
    queries: [
      'Compare power total of AHUs in levels 1, 2, and 3 for the past month',
      'Compare top 20 devices by power demand this week across all levels',
      'Which 15 AHUs have the highest total power in levels 7, 8, and 9?',
      'Show me a comparison of power usage across all AHUs today',
      'Rank top 10 devices by max power demand this month',
      'Compare e0105 vs e0308 power today',
    ],
  },
  {
    label: '🔋 Energy Analysis',
    queries: [
      'Compare energy import of AHUs in levels 4, 5, and 6 last month',
      'Which 10 AHUs have the highest energy consumption all time?',
      'Show me total energy usage for levels 1-3 compared this week',
      'Compare e0206 vs e0401 energy import last 30 days',
      'Top 5 energy hogs across all building levels this month',
      'Energy consumption comparison: AHUs in level 11 vs level 1',
    ],
  },
  {
    label: '📊 Efficiency Insights',
    queries: [
      'Compare power factor of AHUs in levels 2 and 3 this month — find inefficiencies',
      'Which 10 AHUs have the worst power factor across all levels?',
      'Show me power factor comparison between e0105 and e0308 last 30 days',
      'Efficiency ranking: compare top 15 devices by average power factor today',
      'Power factor comparison across levels 7, 8, 9, and 10 this week',
      'Which AHUs in levels 1-3 have the lowest power factor today?',
    ],
  },
  {
    label: '🔌 Current & Voltage',
    queries: [
      'Compare current usage across AHUs in levels 4, 5, and 6 this week',
      'Voltage comparison: show phases L1, L2, L3 for e0206 today',
      'Which 10 AHUs have the highest average current all time?',
      'Compare e0307 vs e0112 voltage levels last 7 days',
      'Current unbalance comparison across all AHUs this month',
      'Voltage THD comparison: levels 1, 2, and 3 today',
    ],
  },
  {
    label: '⚠️ Diagnostics',
    queries: [
      'Which AHUs in levels 7, 8, and 9 have the worst voltage unbalance this month?',
      'Current THD comparison across all building levels — identify issues',
      'Show me voltage harmonics for AHUs in level 11 vs level 1',
      'Which 10 devices have the highest current unbalance today?',
      'Voltage unbalance comparison: levels 4, 5, and 6 last week',
      'THD analysis for AHUs in levels 2-5 this month',
    ],
  },
  {
    label: '🔄 Reactive Power',
    queries: [
      'Compare reactive power of AHUs in levels 1, 2, and 3 this month',
      'Which 10 devices have the highest reactive energy import all time?',
      'Reactive power comparison: levels 7, 8, and 9 vs levels 10, 11',
      'Compare e0214 vs e0317 reactive power last 30 days',
      'Top reactive power consumers across all AHUs this week',
      'Reactive energy import comparison for levels 4-6 today',
    ],
  },
]

// ── Follow-up suggestion logic ────────────────────────────────────────────────
const DIAGNOSTIC_FOLLOWUPS = {
  power_total:          (d) => `Show ${d} power factor last 30 days`,
  energy_import:        (d) => `Show ${d} power factor last 30 days`,
  apparent_power_total: (d) => `Show ${d} power factor last 30 days`,
  power_demand:         (d) => `Show ${d} max power demand last 30 days`,
  reactive_power_total: (d) => `Show ${d} power factor last 30 days`,
  current_avg:          (d) => `Show ${d} current unbalance last 30 days`,
  volts_l_n_avg:        (d) => `Show ${d} voltage unbalance last 30 days`,
  volts_l_l_avg:        (d) => `Show ${d} voltage unbalance last 30 days`,
}
const RELATED_METRICS = {
  power_total: 'energy import', energy_import: 'power demand',
  power_demand: 'max power demand', power_factor_avg: 'reactive power',
  reactive_power_total: 'power factor', current_avg: 'current unbalance',
  current_unbalance: 'voltage unbalance', volts_l_n_avg: 'voltage unbalance',
  volts_unbalance: 'current unbalance', volts_l1_thd: 'current THD',
  current_l1_thd: 'voltage THD', apparent_power_total: 'power factor',
}
const TIME_RANGE_LABELS = { last_24h: 'today', last_7d: 'last 7 days', last_30d: 'last 30 days', all_time: 'all time' }
const NEXT_TIME_RANGE = {
  last_24h: { label: 'last 7 days' }, last_7d: { label: 'last 30 days' },
  last_30d: { label: 'all time' }, all_time: { label: 'last 30 days' },
}

function buildFollowUps(result) {
  const { query_type, metric, time_range, device_ids, chart } = result
  const suggestions = []
  const rangeLabel = TIME_RANGE_LABELS[time_range] || time_range
  if (query_type === 'ranking') {
    const topDevices = chart?.data?.slice(0, 2).map(r => r.device_id) || []
    if (topDevices.length >= 2) suggestions.push(`Compare ${topDevices[0]} vs ${topDevices[1]} ${metric.replace(/_/g, ' ')} ${rangeLabel}`)
    if (topDevices.length >= 1) suggestions.push(`Show ${topDevices[0]} ${metric.replace(/_/g, ' ')} ${rangeLabel}`)
    const diagFn = DIAGNOSTIC_FOLLOWUPS[metric]
    if (diagFn && topDevices.length >= 1) suggestions.push(diagFn(topDevices[0]))
    const nextRange = NEXT_TIME_RANGE[time_range]
    if (nextRange) suggestions.push(`Rank top 10 by ${metric.replace(/_/g, ' ')} ${nextRange.label}`)
  } else {
    const deviceStr = device_ids?.join(' and ') || 'this device'
    const firstDevice = device_ids?.[0]
    const related = RELATED_METRICS[metric]
    if (related) suggestions.push(`Show ${deviceStr} ${related} ${rangeLabel}`)
    const diagFn = DIAGNOSTIC_FOLLOWUPS[metric]
    if (diagFn && firstDevice) suggestions.push(diagFn(firstDevice))
    const nextRange = NEXT_TIME_RANGE[time_range]
    if (nextRange) suggestions.push(`Show ${deviceStr} ${metric.replace(/_/g, ' ')} ${nextRange.label}`)
    if (device_ids?.length === 1) suggestions.push(`Rank top 10 devices by ${metric.replace(/_/g, ' ')} ${rangeLabel}`)
  }
  return [...new Set(suggestions)].slice(0, 4)
}

// ── Metric display maps ───────────────────────────────────────────────────────
const METRIC_UNITS = {
  power_total: 'kW', power_l1: 'kW', power_l2: 'kW', power_l3: 'kW',
  power_demand: 'kW', max_power_demand: 'kW', energy_import: 'kWh', energy_export: 'kWh',
  reactive_energy_import: 'kVArh', reactive_energy_export: 'kVArh',
  apparent_power_total: 'kVA', apparent_power_l1: 'kVA', apparent_power_l2: 'kVA',
  apparent_power_l3: 'kVA', apparent_power_demand: 'kVA', apparent_energy: 'kVAh',
  reactive_power_total: 'kVAr', reactive_power_l1: 'kVAr', reactive_power_l2: 'kVAr',
  reactive_power_l3: 'kVAr', reactive_power_demand: 'kVAr',
  current_avg: 'A', current_l1: 'A', current_l2: 'A', current_l3: 'A',
  current_l1_thd: '%', current_l3_thd: '%', current_unbalance: '%',
  volts_l_n_avg: 'V', volts_l_l_avg: 'V', volts_l1_n: 'V', volts_l2_n: 'V', volts_l3_n: 'V',
  volts_l1_l2: 'V', volts_l2_l3: 'V', volts_l3_l1: 'V',
  volts_l1_thd: '%', volts_l2_thd: '%', volts_l3_thd: '%', volts_unbalance: '%',
  power_factor_avg: '', power_factor_l1: '', power_factor_l2: '', power_factor_l3: '', freq: 'Hz',
}
const METRIC_LABELS = {
  power_total: 'Total Active Power', power_l1: 'L1 Power', power_l2: 'L2 Power', power_l3: 'L3 Power',
  power_demand: 'Power Demand', max_power_demand: 'Max Power Demand',
  energy_import: 'Imported Energy', energy_export: 'Exported Energy',
  reactive_energy_import: 'Reactive Energy Import', reactive_energy_export: 'Reactive Energy Export',
  apparent_power_total: 'Apparent Power', apparent_power_l1: 'L1 Apparent Power',
  apparent_power_l2: 'L2 Apparent Power', apparent_power_l3: 'L3 Apparent Power',
  apparent_power_demand: 'Apparent Power Demand', apparent_energy: 'Apparent Energy',
  reactive_power_total: 'Reactive Power', reactive_power_l1: 'L1 Reactive Power',
  reactive_power_l2: 'L2 Reactive Power', reactive_power_l3: 'L3 Reactive Power',
  reactive_power_demand: 'Reactive Power Demand',
  current_avg: 'Average Current', current_l1: 'L1 Current', current_l2: 'L2 Current',
  current_l3: 'L3 Current', current_l1_thd: 'L1 Current THD', current_l3_thd: 'L3 Current THD',
  current_unbalance: 'Current Unbalance', volts_l_n_avg: 'Avg Voltage (L-N)', volts_l_l_avg: 'Avg Voltage (L-L)',
  volts_l1_n: 'L1-N Voltage', volts_l2_n: 'L2-N Voltage', volts_l3_n: 'L3-N Voltage',
  volts_l1_l2: 'L1-L2 Voltage', volts_l2_l3: 'L2-L3 Voltage', volts_l3_l1: 'L3-L1 Voltage',
  volts_l1_thd: 'L1 Voltage THD', volts_l2_thd: 'L2 Voltage THD', volts_l3_thd: 'L3 Voltage THD',
  volts_unbalance: 'Voltage Unbalance', power_factor_avg: 'Avg Power Factor',
  power_factor_l1: 'L1 Power Factor', power_factor_l2: 'L2 Power Factor',
  power_factor_l3: 'L3 Power Factor', freq: 'Frequency',
}

const LINE_COLORS = ['#00c9b1', '#f5a623', '#7b7eff', '#ff6b8a', '#4ecdc4', '#ffe66d']
const TOOLTIP_STYLE = {
  backgroundColor: '#161d30', border: '1px solid #1f2d45', borderRadius: '6px',
  fontFamily: 'DM Mono, monospace', fontSize: '11px', color: '#e8eef8',
}

function downloadCSV(csv, filename) {
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

function TickLabel({ x, y, payload }) {
  return (
    <text x={x} y={y + 12} textAnchor="middle"
      style={{ fill: '#7a90b0', fontSize: 10, fontFamily: 'DM Mono, monospace' }}>
      {payload.value}
    </text>
  )
}

// ── Example chips ─────────────────────────────────────────────────────────────
function ExampleChips({ onQuery, onForecast, isLoading }) {
  const [activeCategory, setActiveCategory] = useState(0)
  const cat = EXAMPLE_CATEGORIES[activeCategory]

  return (
    <div className="example-section">
      <div className="example-category-tabs">
        {EXAMPLE_CATEGORIES.map((c, i) => (
          <button key={c.label}
            className={`category-tab${activeCategory === i ? ' active' : ''}${c.type === 'forecast' ? ' forecast-tab' : ''}`}
            onClick={() => setActiveCategory(i)}>
            {c.label}
          </button>
        ))}
      </div>
      <div className="example-chips">
        {cat.type === 'forecast'
          ? cat.queries.map(q => (
              <button key={q.deviceId} className="chip forecast-chip"
                onClick={() => onForecast(q.deviceId)} disabled={isLoading}>
                {q.label}
              </button>
            ))
          : cat.queries.map(q => (
              <button key={q} className="chip" onClick={() => onQuery(q)} disabled={isLoading}>{q}</button>
            ))
        }
      </div>
    </div>
  )
}

// ── Follow-up suggestions ─────────────────────────────────────────────────────
function SuggestedFollowUps({ result, onQuery, isLoading }) {
  const suggestions = buildFollowUps(result)
  if (!suggestions.length) return null
  return (
    <div className="followup-section">
      <div className="followup-label">Explore further</div>
      <div className="followup-chips">
        {suggestions.map(q => (
          <button key={q} className="followup-chip" onClick={() => onQuery(q)} disabled={isLoading}>
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 5, flexShrink: 0 }}>
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Device tag ────────────────────────────────────────────────────────────────
function DeviceTag({ deviceId }) {
  const mapped = isMapped(deviceId)
  const label  = mapped ? getDeviceLabel(deviceId) : null
  const detail = mapped ? getDeviceDetail(deviceId) : `Device ${deviceId} — location not confirmed`
  return (
    <span className={`meta-tag device-tag${!mapped ? ' device-tag-unknown' : ''}`} title={detail}>
      {deviceId}
      {label && <span className="device-tag-name">· {label}</span>}
    </span>
  )
}

// ── Forecast card ─────────────────────────────────────────────────────────────
function ForecastCard({ result, onQuery, onForecast, isLoading }) {
  const { device_id, history, forecast, summary, recent_avg, generated_at } = result

  // Downsample history to last 7 days at ~30-min granularity for performance
  // then append forecast. Each point has { time, history, forecast }
  const downsample = (arr, step) =>
    arr.filter((_, i) => i % step === 0 || i === arr.length - 1)

  const histStep    = Math.max(1, Math.floor(history.length / 336)) // ~7d × 2/hr
  const histSampled = downsample(history, histStep)

  // Format time labels
  const fmt = (iso) => {
    try {
      const d = new Date(iso)
      return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
    } catch { return iso }
  }

  const chartData = [
    ...histSampled.map(p => ({ time: fmt(p.time), history: p.value, forecast: null })),
    // Bridge point — last history value also starts the forecast line
    { time: fmt(histSampled[histSampled.length - 1]?.time), history: histSampled[histSampled.length - 1]?.value, forecast: histSampled[histSampled.length - 1]?.value },
    ...forecast.map(p => ({ time: fmt(p.time), history: null, forecast: p.value })),
  ]

  const nowLabel  = fmt(histSampled[histSampled.length - 1]?.time)
  const hasAlert  = summary.includes('⚠️') || summary.includes('ℹ️')
  const deviceLabel = getDeviceLabel(device_id)
  const genTime   = generated_at ? new Date(generated_at).toLocaleString() : ''

  // CSV download for forecast
  const handleDownload = () => {
    const rows = ['time,type,power_total_kw']
    histSampled.forEach(p => rows.push(`${p.time},historical,${p.value}`))
    forecast.forEach(p => rows.push(`${p.time},forecast,${p.value}`))
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url; a.download = `wach_forecast_${device_id}_${Date.now()}.csv`; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="result-card">
      <div className="query-meta">
        <span className="meta-tag type-forecast">Forecast</span>
        <span className="meta-tag metric">Power Total (kW)</span>
        <span className="meta-tag range">7d history + 24h ahead</span>
        <DeviceTag deviceId={device_id} />
      </div>

      <div className="chart-card">
        <div className="chart-card-header">
          <span className="chart-card-title">
            {device_id}{deviceLabel !== device_id ? ` · ${deviceLabel}` : ''} · Power Forecast
          </span>
          <button className="csv-btn" onClick={handleDownload}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Export CSV
          </button>
        </div>

        <div className="forecast-legend">
          <span className="forecast-legend-item">
            <span className="forecast-legend-dot history" />
            Historical (7 days)
          </span>
          <span className="forecast-legend-item">
            <span className="forecast-legend-dot prediction" />
            Forecast (24 hours)
          </span>
          <span className="forecast-legend-item muted">
            Avg: {recent_avg?.toFixed(2)} kW
          </span>
        </div>

        <div className="chart-body">
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={chartData} margin={{ top: 4, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#1f2d45" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="time" tick={<TickLabel />} axisLine={false} tickLine={false}
                interval={Math.floor(chartData.length / 8)} />
              <YAxis tick={{ fill: '#7a90b0', fontSize: 10, fontFamily: 'DM Mono, monospace' }}
                axisLine={false} tickLine={false} width={52} unit=" kW" />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelStyle={{ color: '#7a90b0', marginBottom: 4 }}
                formatter={(val, name) => [
                  val !== null ? `${Number(val).toFixed(3)} kW` : '—',
                  name === 'history' ? 'Historical' : 'Forecast',
                ]}
              />
              {/* "Now" vertical line */}
              <ReferenceLine x={nowLabel} stroke="#3d526e" strokeDasharray="4 4"
                label={{ value: 'NOW', position: 'top', fill: '#3d526e', fontSize: 9, fontFamily: 'DM Mono, monospace' }} />
              <Line type="monotone" dataKey="history"
                stroke="#00c9b1" strokeWidth={1.6} dot={false}
                connectNulls={false} activeDot={{ r: 3, fill: '#00c9b1' }} />
              <Line type="monotone" dataKey="forecast"
                stroke="#f5a623" strokeWidth={1.8} dot={false} strokeDasharray="5 3"
                connectNulls={false} activeDot={{ r: 4, fill: '#f5a623' }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {summary && (
        <div className={`summary-card${hasAlert ? ' summary-alert' : ''}`}>
          <div className="summary-label">Forecast Analysis</div>
          <p className="summary-text">{summary}</p>
          {genTime && <p className="summary-generated">Generated {genTime}</p>}
        </div>
      )}

      {/* Follow-up: view actual recent data or run another device */}
      <div className="followup-section">
        <div className="followup-label">Explore further</div>
        <div className="followup-chips">
          <button className="followup-chip" onClick={() => onQuery(`Show ${device_id} total power last 7 days`)} disabled={isLoading}>
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 5 }}>
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            View actual 7-day history for {device_id}
          </button>
          <button className="followup-chip" onClick={() => onQuery(`Show ${device_id} power factor last 7 days`)} disabled={isLoading}>
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 5 }}>
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            Check power factor for {device_id}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Standard result card ──────────────────────────────────────────────────────
function ResultCard({ result, onQuery, onForecast, isLoading }) {
  const { chart, summary, metric, time_range, device_ids } = result
  const unit = METRIC_UNITS[metric] || ''
  const label = METRIC_LABELS[metric] || metric
  const rangeLabel = time_range.replace(/_/g, ' ')
  const csvFilename = `wach_${metric}_${time_range}_${Date.now()}.csv`

  return (
    <div className="result-card">
      <div className="query-meta">
        <span className={`meta-tag ${chart.chart_type === 'line' ? 'type-line' : 'type-bar'}`}>
          {chart.chart_type === 'line' ? 'Time Series' : 'Ranking'}
        </span>
        <span className="meta-tag metric">{label}</span>
        <span className="meta-tag range">{rangeLabel}</span>
        {device_ids?.map(d => <DeviceTag key={d} deviceId={d} />)}
      </div>
      <div className="chart-card">
        <div className="chart-card-header">
          <span className="chart-card-title">
            {chart.chart_type === 'line'
              ? device_ids?.length > 1
                ? `${device_ids.join(' vs ')} · ${label} · ${rangeLabel}`
                : `${label} over ${rangeLabel}`
              : `Top ${chart.data?.length} devices by ${label} · ${rangeLabel}`
            }
          </span>
          {chart.csv && (
            <button className="csv-btn" onClick={() => downloadCSV(chart.csv, csvFilename)}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Export CSV
            </button>
          )}
        </div>
        <div className="chart-body">
          {chart.chart_type === 'line'
            ? <LineChartView data={chart.data} deviceIds={chart.device_ids} unit={unit} />
            : <BarChartView data={chart.data} unit={unit} />
          }
        </div>
      </div>
      {summary && (
        <div className="summary-card">
          <div className="summary-label">Analysis</div>
          <p className="summary-text">{summary}</p>
        </div>
      )}
      <SuggestedFollowUps result={result} onQuery={onQuery} isLoading={isLoading} />
    </div>
  )
}

function SkeletonResult() {
  return (
    <div className="result-card">
      <div className="query-meta">
        <div className="skeleton" style={{ width: 80, height: 22, borderRadius: 3 }} />
        <div className="skeleton" style={{ width: 120, height: 22, borderRadius: 3 }} />
        <div className="skeleton" style={{ width: 80, height: 22, borderRadius: 3 }} />
      </div>
      <div className="chart-card">
        <div className="chart-card-header">
          <div className="skeleton" style={{ width: 200, height: 14, borderRadius: 3 }} />
        </div>
        <div className="chart-body">
          <div className="skeleton" style={{ width: '100%', height: 280, borderRadius: 6 }} />
        </div>
      </div>
      <div className="summary-card">
        <div className="skeleton" style={{ width: 70, height: 11, borderRadius: 2, marginBottom: 12 }} />
        <div className="skeleton" style={{ width: '100%', height: 14, borderRadius: 3, marginBottom: 8 }} />
        <div className="skeleton" style={{ width: '85%', height: 14, borderRadius: 3, marginBottom: 8 }} />
        <div className="skeleton" style={{ width: '60%', height: 14, borderRadius: 3 }} />
      </div>
    </div>
  )
}

// ── Main chat view ────────────────────────────────────────────────────────────
export default function ChatView({ messages, isLoading, onQuery, onForecast, onClear }) {
  const [input, setInput] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const threadEndRef = useRef(null)
  const textareaRef  = useRef(null)
  const recognitionRef = useRef(null)

  useEffect(() => { textareaRef.current?.focus() }, [])
  useEffect(() => { threadEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${Math.min(ta.scrollHeight, 140)}px`
  }, [input])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() }
  }
  function submit() {
    const q = input.trim()
    if (!q || isLoading) return
    onQuery(q); setInput('')
    if (textareaRef.current) textareaRef.current.style.height = '44px'
  }
  function toggleVoice() {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      alert('Voice input is not supported in this browser. Try Chrome.'); return
    }
    if (isRecording) { recognitionRef.current?.stop(); setIsRecording(false); return }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    const rec = new SR()
    rec.lang = 'en-US'; rec.interimResults = false; rec.maxAlternatives = 1
    rec.onresult = (e) => { const t = e.results[0][0].transcript; setInput(prev => prev ? `${prev} ${t}` : t) }
    rec.onend = () => setIsRecording(false)
    rec.onerror = () => setIsRecording(false)
    rec.start(); recognitionRef.current = rec; setIsRecording(true)
  }

  return (
    <div className="chat-view">
      <div className="thread">
        <div className="thread-inner">
          {messages.map((msg, i) => (
            <div key={msg.id} className={`turn turn-${msg.role}`}>
              {msg.role === 'user' && (
                <div className={`user-bubble${!isLoading ? ' clickable' : ''}`}
                  onClick={() => !isLoading && onQuery(msg.text)} title="Click to re-run">
                  {msg.text}
                </div>
              )}
              {(msg.role === 'assistant' || msg.role === 'error') && (
                <>
                  {msg.text === null && (
                    <>
                      <div className="thinking">
                        <div className="thinking-dots"><span /><span /><span /></div>
                        querying...
                      </div>
                      <SkeletonResult />
                    </>
                  )}
                  {msg.text !== null && (
                    <>
                      <div className={`assistant-bubble${msg.role === 'error' ? ' error-bubble' : ''}`}
                        style={{ whiteSpace: 'pre-wrap' }}>
                        {msg.text}
                      </div>
                      {msg.result && msg.result.query_type === 'forecast'
                        ? <ForecastCard result={msg.result} onQuery={onQuery} onForecast={onForecast} isLoading={isLoading} />
                        : msg.result
                          ? <ResultCard result={msg.result} onQuery={onQuery} onForecast={onForecast} isLoading={isLoading} />
                          : null
                      }
                    </>
                  )}
                  {i === 0 && <ExampleChips onQuery={onQuery} onForecast={onForecast} isLoading={isLoading} />}
                </>
              )}
            </div>
          ))}
          <div ref={threadEndRef} />
        </div>
      </div>

      <div className="input-bar">
        <div className="input-bar-inner">
          <div className="input-row">
            <textarea ref={textareaRef} className="chat-input" value={input}
              onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown}
              placeholder="Ask about AHU energy performance..." rows={1} disabled={isLoading} />
            <button className={`mic-btn${isRecording ? ' recording' : ''}`} onClick={toggleVoice}
              title={isRecording ? 'Stop recording' : 'Voice input'}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" /><line x1="8" y1="23" x2="16" y2="23" />
              </svg>
            </button>
            <button className="send-btn" onClick={submit} disabled={isLoading || !input.trim()} title="Send">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
          <div className="input-footer">
            <p className="input-hint">Enter to send · Shift+Enter for new line · Click a past query to re-run</p>
            <button className="clear-btn" onClick={onClear}>
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                <path d="M10 11v6" /><path d="M14 11v6" /><path d="M9 6V4h6v2" />
              </svg>
              Clear
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Bar tooltip ───────────────────────────────────────────────────────────────
function BarTooltipContent({ active, payload, unit }) {
  if (!active || !payload?.length) return null
  const deviceId = payload[0]?.payload?.device_id
  const value    = payload[0]?.value
  const detail   = deviceId ? getDeviceDetail(deviceId) : null
  return (
    <div style={TOOLTIP_STYLE}>
      <div style={{ color: '#7a90b0', marginBottom: 4, fontSize: 10 }}>{deviceId}</div>
      {detail && <div style={{ color: '#a0b4cc', marginBottom: 6, fontSize: 10 }}>{detail}</div>}
      <div style={{ color: '#00c9b1' }}>{Number(value).toFixed(3)}{unit ? ` ${unit}` : ''}</div>
    </div>
  )
}

// ── Chart components ──────────────────────────────────────────────────────────
function LineChartView({ data, deviceIds, unit }) {
  if (!data?.length) return <EmptyChart />
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 4, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#1f2d45" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="time" tick={<TickLabel />} axisLine={false} tickLine={false} interval="preserveStartEnd" />
        <YAxis tick={{ fill: '#7a90b0', fontSize: 10, fontFamily: 'DM Mono, monospace' }}
          axisLine={false} tickLine={false} width={52} unit={unit ? ` ${unit}` : ''} />
        <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: '#7a90b0', marginBottom: 4 }}
          formatter={(val, name) => [
            `${Number(val).toFixed(3)}${unit ? ` ${unit}` : ''}`,
            getDeviceLabel(name) !== name ? `${name} · ${getDeviceLabel(name)}` : name,
          ]} />
        {deviceIds?.length > 1 && (
          <Legend
            formatter={(v) => { const l = getDeviceLabel(v); return l !== v ? `${v} · ${l}` : v }}
            wrapperStyle={{ fontSize: 11, fontFamily: 'DM Mono, monospace', color: '#7a90b0', paddingTop: 8 }}
          />
        )}
        {(deviceIds || []).map((id, i) => (
          <Line key={id} type="monotone" dataKey={id}
            stroke={LINE_COLORS[i % LINE_COLORS.length]} strokeWidth={1.8}
            dot={false} activeDot={{ r: 4, fill: LINE_COLORS[i % LINE_COLORS.length] }} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

function BarChartView({ data, unit }) {
  if (!data?.length) return <EmptyChart />
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 20, left: 0, bottom: 0 }} layout="vertical">
        <CartesianGrid stroke="#1f2d45" strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" tick={{ fill: '#7a90b0', fontSize: 10, fontFamily: 'DM Mono, monospace' }}
          axisLine={false} tickLine={false} unit={unit ? ` ${unit}` : ''} />
        <YAxis type="category" dataKey="device_id"
          tick={{ fill: '#7a90b0', fontSize: 10, fontFamily: 'DM Mono, monospace' }}
          axisLine={false} tickLine={false} width={52} />
        <Tooltip content={<BarTooltipContent unit={unit} />} cursor={{ fill: '#00c9b108' }} />
        <Bar dataKey="value" fill="#00c9b1" radius={[0, 3, 3, 0]} maxBarSize={24} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function EmptyChart() {
  return (
    <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ fontFamily: 'DM Mono, monospace', fontSize: 12, color: '#3d526e' }}>No data returned.</p>
    </div>
  )
}