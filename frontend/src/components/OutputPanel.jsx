import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'

const METRIC_UNITS = {
  power_total:          'kW', power_l1: 'kW', power_l2: 'kW', power_l3: 'kW',
  power_demand:         'kW', max_power_demand: 'kW',
  energy_import:        'kWh', energy_export: 'kWh',
  reactive_energy_import: 'kVArh', reactive_energy_export: 'kVArh',
  apparent_power_total: 'kVA', apparent_power_l1: 'kVA', apparent_power_l2: 'kVA',
  apparent_power_l3:    'kVA', apparent_power_demand: 'kVA', apparent_energy: 'kVAh',
  reactive_power_total: 'kVAr', reactive_power_l1: 'kVAr', reactive_power_l2: 'kVAr',
  reactive_power_l3:    'kVAr', reactive_power_demand: 'kVAr',
  current_avg:          'A', current_l1: 'A', current_l2: 'A', current_l3: 'A',
  current_l1_thd:       '%', current_l3_thd: '%', current_unbalance: '%',
  volts_l_n_avg:        'V', volts_l_l_avg: 'V', volts_l1_n: 'V', volts_l2_n: 'V', volts_l3_n: 'V',
  volts_l1_l2:          'V', volts_l2_l3: 'V', volts_l3_l1: 'V',
  volts_l1_thd:         '%', volts_l2_thd: '%', volts_l3_thd: '%', volts_unbalance: '%',
  power_factor_avg:     '', power_factor_l1: '', power_factor_l2: '', power_factor_l3: '',
  freq:                 'Hz',
}

const METRIC_LABELS = {
  power_total:          'Total Active Power', power_l1: 'L1 Active Power', power_l2: 'L2 Active Power', power_l3: 'L3 Active Power',
  power_demand:         'Power Demand', max_power_demand: 'Max Power Demand',
  energy_import:        'Imported Energy', energy_export: 'Exported Energy',
  reactive_energy_import: 'Reactive Energy Import', reactive_energy_export: 'Reactive Energy Export',
  apparent_power_total: 'Apparent Power', apparent_power_l1: 'L1 Apparent Power',
  apparent_power_l2:    'L2 Apparent Power', apparent_power_l3: 'L3 Apparent Power',
  apparent_power_demand:'Apparent Power Demand', apparent_energy: 'Apparent Energy',
  reactive_power_total: 'Reactive Power', reactive_power_l1: 'L1 Reactive Power',
  reactive_power_l2:    'L2 Reactive Power', reactive_power_l3: 'L3 Reactive Power',
  reactive_power_demand:'Reactive Power Demand',
  current_avg:          'Average Current', current_l1: 'L1 Current', current_l2: 'L2 Current',
  current_l3:           'L3 Current', current_l1_thd: 'L1 Current THD', current_l3_thd: 'L3 Current THD',
  current_unbalance:    'Current Unbalance',
  volts_l_n_avg:        'Avg Voltage (L-N)', volts_l_l_avg: 'Avg Voltage (L-L)',
  volts_l1_n:           'L1-N Voltage', volts_l2_n: 'L2-N Voltage', volts_l3_n: 'L3-N Voltage',
  volts_l1_l2:          'L1-L2 Voltage', volts_l2_l3: 'L2-L3 Voltage', volts_l3_l1: 'L3-L1 Voltage',
  volts_l1_thd:         'L1 Voltage THD', volts_l2_thd: 'L2 Voltage THD', volts_l3_thd: 'L3 Voltage THD',
  volts_unbalance:      'Voltage Unbalance',
  power_factor_avg:     'Avg Power Factor', power_factor_l1: 'L1 Power Factor',
  power_factor_l2:      'L2 Power Factor', power_factor_l3: 'L3 Power Factor',
  freq:                 'Frequency',
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
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
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

export default function OutputPanel({ result, isLoading }) {
  if (!result && !isLoading) {
    return (
      <div className="output-panel">
        <div className="output-empty">
          <div className="output-empty-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
          </div>
          <p>
            Your chart will appear here.<br />
            Ask a question in the panel on the left.
          </p>
        </div>
      </div>
    )
  }

  if (isLoading && !result) {
    return (
      <div className="output-panel">
        <div className="output-content">
          <div className="query-meta">
            <div className="skeleton" style={{ width: 80,  height: 22, borderRadius: 3 }} />
            <div className="skeleton" style={{ width: 120, height: 22, borderRadius: 3 }} />
            <div className="skeleton" style={{ width: 80,  height: 22, borderRadius: 3 }} />
          </div>
          <div className="chart-card">
            <div className="chart-card-header">
              <div className="skeleton" style={{ width: 200, height: 14, borderRadius: 3 }} />
            </div>
            <div className="chart-body">
              <div className="skeleton" style={{ width: '100%', height: 320, borderRadius: 6 }} />
            </div>
          </div>
          <div className="summary-card">
            <div className="skeleton" style={{ width: 70,  height: 11, borderRadius: 2, marginBottom: 12 }} />
            <div className="skeleton" style={{ width: '100%', height: 14, borderRadius: 3, marginBottom: 8 }} />
            <div className="skeleton" style={{ width: '85%',  height: 14, borderRadius: 3, marginBottom: 8 }} />
            <div className="skeleton" style={{ width: '60%',  height: 14, borderRadius: 3 }} />
          </div>
        </div>
      </div>
    )
  }

  const { chart, summary, metric, time_range, query_type, device_ids } = result
  const unit  = METRIC_UNITS[metric] || ''
  const label = METRIC_LABELS[metric] || metric
  const csvFilename = `wach_${metric}_${time_range}_${Date.now()}.csv`

  const rangeLabel = time_range.replace(/_/g, ' ')

  return (
    <div className="output-panel">
      <div className="output-content">

        {/* Meta tags row */}
        <div className="query-meta">
          <span className={`meta-tag ${chart.chart_type === 'line' ? 'type-line' : 'type-bar'}`}>
            {chart.chart_type === 'line' ? 'Time Series' : 'Ranking'}
          </span>
          <span className="meta-tag metric">{label}</span>
          <span className="meta-tag range">{rangeLabel}</span>
          {device_ids?.length > 0 && device_ids.map(d => (
            <span key={d} className="meta-tag metric">{d}</span>
          ))}
        </div>

        {/* Chart card */}
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
              <button
                className="csv-btn"
                onClick={() => downloadCSV(chart.csv, csvFilename)}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                Export CSV
              </button>
            )}
          </div>

          <div className="chart-body">
            {chart.chart_type === 'line'
              ? <LineChartView data={chart.data} deviceIds={chart.device_ids} unit={unit} />
              : <BarChartView  data={chart.data} unit={unit} />
            }
          </div>
        </div>

        {/* Summary card */}
        {summary && (
          <div className="summary-card">
            <div className="summary-label">Analysis</div>
            <p className="summary-text">{summary}</p>
          </div>
        )}

      </div>
    </div>
  )
}

function LineChartView({ data, deviceIds, unit }) {
  if (!data?.length) return <EmptyChart />

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 4, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#1f2d45" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="time"
          tick={<TickLabel />}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={v => `${v}`}
          tick={{ fill: '#7a90b0', fontSize: 10, fontFamily: 'DM Mono, monospace' }}
          axisLine={false}
          tickLine={false}
          width={52}
          unit={` ${unit}`}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          labelStyle={{ color: '#7a90b0', marginBottom: 4 }}
          formatter={(val, name) => [`${Number(val).toFixed(3)} ${unit}`, name]}
        />
        {deviceIds?.length > 1 && <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'DM Mono, monospace', color: '#7a90b0', paddingTop: 8 }} />}
        {(deviceIds || []).map((id, i) => (
          <Line
            key={id}
            type="monotone"
            dataKey={id}
            stroke={LINE_COLORS[i % LINE_COLORS.length]}
            strokeWidth={1.8}
            dot={false}
            activeDot={{ r: 4, fill: LINE_COLORS[i % LINE_COLORS.length] }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

function BarChartView({ data, unit }) {
  if (!data?.length) return <EmptyChart />

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data} margin={{ top: 4, right: 20, left: 0, bottom: 0 }} layout="vertical">
        <CartesianGrid stroke="#1f2d45" strokeDasharray="3 3" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: '#7a90b0', fontSize: 10, fontFamily: 'DM Mono, monospace' }}
          axisLine={false}
          tickLine={false}
          unit={` ${unit}`}
        />
        <YAxis
          type="category"
          dataKey="device_id"
          tick={{ fill: '#7a90b0', fontSize: 10, fontFamily: 'DM Mono, monospace' }}
          axisLine={false}
          tickLine={false}
          width={52}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(val) => [`${Number(val).toFixed(3)} ${unit}`, 'avg value']}
          cursor={{ fill: '#00c9b108' }}
        />
        <Bar
          dataKey="value"
          fill="#00c9b1"
          radius={[0, 3, 3, 0]}
          maxBarSize={24}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}

function EmptyChart() {
  return (
    <div style={{ height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ fontFamily: 'DM Mono, monospace', fontSize: 12, color: '#3d526e' }}>
        No data returned for this query.
      </p>
    </div>
  )
}