import { useState, useRef, useEffect } from 'react'

import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'

// ── Categorised example queries ───────────────────────────────────────────────
const EXAMPLE_CATEGORIES = [
  {
    label: '⚡ Power',
    queries: [
      'Rank top 10 devices by total power this month',
      'Show e0101 total power last 7 days',
      'Compare e0101 vs e0206 power today',
      'Top 5 devices by power demand all time',
      'Show e0305 power demand last 30 days',
      'Rank top 10 by max power demand this week',
    ],
  },
  {
    label: '🔋 Energy',
    queries: [
      'Rank top 10 devices by energy import this month',
      'Show e0101 energy import last 30 days',
      'Top 5 devices by reactive energy import all time',
      'Show e0206 apparent energy last 7 days',
      'Rank top 10 by energy import today',
      'Compare e0101 vs e0305 energy import this month',
    ],
  },
  {
    label: '📊 Efficiency',
    queries: [
      'Which 10 devices have the worst power factor this month?',
      'Show e0101 power factor last 30 days',
      'Rank top 10 devices by average power factor all time',
      'Compare e0101 vs e0206 power factor last 7 days',
      'Show e0305 power factor L1 last 30 days',
      'Which 5 devices have the lowest power factor today?',
    ],
  },
  {
    label: '🔌 Current & Voltage',
    queries: [
      'Show e0101 average current last 7 days',
      'Rank top 10 devices by average current this month',
      'Show e0206 voltage today',
      'Compare e0101 vs e0305 current last 7 days',
      'Rank top 10 by average voltage all time',
      'Show e0101 phase L1 current last 30 days',
    ],
  },
  {
    label: '⚠️ Diagnostics',
    queries: [
      'Which 10 devices have the worst voltage unbalance this month?',
      'Show e0101 current unbalance last 30 days',
      'Rank top 10 devices by voltage THD this month',
      'Show e0206 voltage harmonic distortion last 7 days',
      'Which devices have the highest current THD today?',
      'Show e0305 current unbalance last 7 days',
    ],
  },
  {
    label: '🔄 Reactive Power',
    queries: [
      'Top 5 devices by reactive power all time',
      'Show e0101 reactive power last 7 days',
      'Rank top 10 by reactive power demand this month',
      'Compare e0101 vs e0206 reactive power last 30 days',
      'Show e0305 reactive power L1 last 7 days',
      'Top 10 devices by reactive energy import this month',
    ],
  },
]

// ── Metric display maps ───────────────────────────────────────────────────────
const METRIC_UNITS = {
  power_total: 'kW', power_l1: 'kW', power_l2: 'kW', power_l3: 'kW',
  power_demand: 'kW', max_power_demand: 'kW',
  energy_import: 'kWh', energy_export: 'kWh',
  reactive_energy_import: 'kVArh', reactive_energy_export: 'kVArh',
  apparent_power_total: 'kVA', apparent_power_l1: 'kVA', apparent_power_l2: 'kVA',
  apparent_power_l3: 'kVA', apparent_power_demand: 'kVA', apparent_energy: 'kVAh',
  reactive_power_total: 'kVAr', reactive_power_l1: 'kVAr', reactive_power_l2: 'kVAr',
  reactive_power_l3: 'kVAr', reactive_power_demand: 'kVAr',
  current_avg: 'A', current_l1: 'A', current_l2: 'A', current_l3: 'A',
  current_l1_thd: '%', current_l3_thd: '%', current_unbalance: '%',
  volts_l_n_avg: 'V', volts_l_l_avg: 'V',
  volts_l1_n: 'V', volts_l2_n: 'V', volts_l3_n: 'V',
  volts_l1_l2: 'V', volts_l2_l3: 'V', volts_l3_l1: 'V',
  volts_l1_thd: '%', volts_l2_thd: '%', volts_l3_thd: '%', volts_unbalance: '%',
  power_factor_avg: '', power_factor_l1: '', power_factor_l2: '', power_factor_l3: '',
  freq: 'Hz',
}

const METRIC_LABELS = {
  power_total: 'Total Active Power', power_l1: 'L1 Power', power_l2: 'L2 Power',
  power_l3: 'L3 Power', power_demand: 'Power Demand', max_power_demand: 'Max Power Demand',
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
  current_unbalance: 'Current Unbalance',
  volts_l_n_avg: 'Avg Voltage (L-N)', volts_l_l_avg: 'Avg Voltage (L-L)',
  volts_l1_n: 'L1-N Voltage', volts_l2_n: 'L2-N Voltage', volts_l3_n: 'L3-N Voltage',
  volts_l1_l2: 'L1-L2 Voltage', volts_l2_l3: 'L2-L3 Voltage', volts_l3_l1: 'L3-L1 Voltage',
  volts_l1_thd: 'L1 Voltage THD', volts_l2_thd: 'L2 Voltage THD', volts_l3_thd: 'L3 Voltage THD',
  volts_unbalance: 'Voltage Unbalance',
  power_factor_avg: 'Avg Power Factor', power_factor_l1: 'L1 Power Factor',
  power_factor_l2: 'L2 Power Factor', power_factor_l3: 'L3 Power Factor',
  freq: 'Frequency',
}

const LINE_COLORS = ['#00c9b1', '#f5a623', '#7b7eff', '#ff6b8a', '#4ecdc4', '#ffe66d']

const TOOLTIP_STYLE = {
  backgroundColor: '#161d30',
  border: '1px solid #1f2d45',
  borderRadius: '6px',
  fontFamily: 'DM Mono, monospace',
  fontSize: '11px',
  color: '#e8eef8',
}

function downloadCSV(csv, filename) {
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
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

// ── Example chips with category tabs ─────────────────────────────────────────
function ExampleChips({ onQuery, isLoading }) {
  const [activeCategory, setActiveCategory] = useState(0)

  return (
    <div className="example-section">
      <div className="example-category-tabs">
        {EXAMPLE_CATEGORIES.map((cat, i) => (
          <button
            key={cat.label}
            className={`category-tab${activeCategory === i ? ' active' : ''}`}
            onClick={() => setActiveCategory(i)}
          >
            {cat.label}
          </button>
        ))}
      </div>
      <div className="example-chips">
        {EXAMPLE_CATEGORIES[activeCategory].queries.map(q => (
          <button
            key={q}
            className="chip"
            onClick={() => onQuery(q)}
            disabled={isLoading}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Result card ───────────────────────────────────────────────────────────────
function ResultCard({ result }) {
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
        {device_ids?.map(d => <span key={d} className="meta-tag metric">{d}</span>)}
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
          <div className="skeleton" style={{ width: '100%', height: 260, borderRadius: 6 }} />
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
export default function ChatView({ messages, isLoading, onQuery, onClear }) {
  const [input, setInput] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const threadEndRef = useRef(null)
  const textareaRef = useRef(null)
  const recognitionRef = useRef(null)

  useEffect(() => { textareaRef.current?.focus() }, [])

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
    onQuery(q)
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = '44px'
  }

  function toggleVoice() {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      alert('Voice input is not supported in this browser. Try Chrome.')
      return
    }
    if (isRecording) { recognitionRef.current?.stop(); setIsRecording(false); return }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    const rec = new SR()
    rec.lang = 'en-US'; rec.interimResults = false; rec.maxAlternatives = 1
    rec.onresult = (e) => {
      const t = e.results[0][0].transcript
      setInput(prev => prev ? `${prev} ${t}` : t)
    }
    rec.onend = () => setIsRecording(false)
    rec.onerror = () => setIsRecording(false)
    rec.start()
    recognitionRef.current = rec
    setIsRecording(true)
  }

  return (
    <div className="chat-view">
      <div className="thread">
        <div className="thread-inner">
          {messages.map((msg, i) => (
            <div key={msg.id} className={`turn turn-${msg.role}`}>

              {msg.role === 'user' && (
                <div
                  className={`user-bubble${!isLoading ? ' clickable' : ''}`}
                  onClick={() => !isLoading && onQuery(msg.text)}
                  title="Click to re-run"
                >
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
                      {msg.result && <ResultCard result={msg.result} />}
                    </>
                  )}
                  {i === 0 && (
                    <ExampleChips onQuery={onQuery} isLoading={isLoading} />
                  )}
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
            <textarea
              ref={textareaRef}
              className="chat-input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about AHU energy performance..."
              rows={1}
              disabled={isLoading}
            />
            <button className={`mic-btn${isRecording ? ' recording' : ''}`} onClick={toggleVoice}
              title={isRecording ? 'Stop recording' : 'Voice input'}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
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
          formatter={(val, name) => [`${Number(val).toFixed(3)}${unit ? ` ${unit}` : ''}`, name]} />
        {deviceIds?.length > 1 && <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'DM Mono, monospace', color: '#7a90b0', paddingTop: 8 }} />}
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
        <Tooltip contentStyle={TOOLTIP_STYLE}
          formatter={(val) => [`${Number(val).toFixed(3)}${unit ? ` ${unit}` : ''}`, 'avg value']}
          cursor={{ fill: '#00c9b108' }} />
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