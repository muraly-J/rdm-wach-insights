import React from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { fetchMeasurements } from '../../api/client';
import { CHART_CONFIG } from '../../constants/chartConfig';
import { METRIC_META, SCORE_METRIC_GROUPS } from '../../constants/metricGroups';
import { useMetricSelection } from '../../hooks/useMetricSelection';
import { renderOffPeriodAreas } from '../../utils/offPeriodAreas';

interface SingleDeviceChartProps {
  deviceId: string;
  deviceLabel: string;
  timeRange: string;
  isOn?: boolean;
  healthChartData?: Array<{ timestamp?: string; is_on?: boolean;[key: string]: any }>;
}

function toApiRange(timeRange: string): '24h' | '7d' | '30d' {
  if (timeRange === '24h' || timeRange === '7d' || timeRange === '30d') return timeRange;
  return '30d';
}

const SingleDeviceChart: React.FC<SingleDeviceChartProps> = ({
  deviceId,
  deviceLabel,
  timeRange,
  isOn = true,
  healthChartData,
}) => {
  const { selectedMetrics, setSelectedMetrics, toggleMetric } = useMetricSelection();
  const [chartData, setChartData] = React.useState<Record<string, number | string | null>[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [groupOpen, setGroupOpen] = React.useState<string | null>(null);

  const apiRange = toApiRange(timeRange);

  React.useEffect(() => {
    if (selectedMetrics.length === 0 || !deviceId) return;
    setIsLoading(true);
    fetchMeasurements(deviceId, selectedMetrics, apiRange)
      .then((res) => {
        const firstMetric = selectedMetrics[0];
        const points = res.measurements[firstMetric] ?? [];
        const data = points.map((p, i) => {
          const entry: Record<string, number | string | null> = { timestamp: p.timestamp };
          selectedMetrics.forEach((m) => {
            entry[m] = res.measurements[m]?.[i]?.value ?? null;
          });
          return entry;
        });
        setChartData(data);
      })
      .catch(() => {
        setChartData([]);
      })
      .finally(() => setIsLoading(false));
  }, [deviceId, selectedMetrics, timeRange]);

  // Merge is_on flags from healthChartData
  const chartDataWithIsOn = React.useMemo(() => {
    if (!chartData?.length || !healthChartData?.length) return chartData;
    return chartData.map((point, i) => ({
      ...point,
      is_on: healthChartData[i]?.is_on ?? true,
    }));
  }, [chartData, healthChartData]);

  return (
    <div>
      <div
        style={{
          marginBottom: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          flexWrap: 'wrap',
        }}
      >
        <span style={{ fontSize: 12, color: '#8899aa' }}>Metrics for</span>
        <span style={{ fontSize: 13, color: isOn ? '#00E5A0' : '#8899aa', fontWeight: 600 }}>
          {deviceLabel}
        </span>
        {!isOn && (
          <span
            style={{
              fontSize: 10,
              color: '#556677',
              background: '#1a2234',
              border: '1px solid #2a3649',
              borderRadius: 4,
              padding: '2px 6px',
              fontWeight: 600,
              letterSpacing: '0.05em',
            }}
          >
            OFF
          </span>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
        {SCORE_METRIC_GROUPS.map((group) => (
          <div key={group.scoreKey} style={{ position: 'relative' }}>
            <button
              onClick={() => setGroupOpen(groupOpen === group.scoreKey ? null : group.scoreKey)}
              style={{
                background: '#1a2234',
                border: '1px solid #2a3649',
                borderRadius: 8,
                padding: '5px 10px',
                fontSize: 11,
                color: '#8899aa',
                cursor: 'pointer',
              }}
            >
              {group.scoreLabel} ▾
            </button>
            {groupOpen === group.scoreKey && (
              <div
                style={{
                  position: 'absolute',
                  top: 'calc(100% + 4px)',
                  left: 0,
                  zIndex: 20,
                  background: '#141D28',
                  border: '1px solid #2a3649',
                  borderRadius: 8,
                  padding: 6,
                  minWidth: 180,
                  boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                }}
              >
                {group.availableMetrics.map((m) => (
                  <div
                    key={m.key}
                    onClick={() => toggleMetric(m.key)}
                    style={{
                      padding: '5px 8px',
                      borderRadius: 5,
                      cursor: 'pointer',
                      fontSize: 11,
                      color: selectedMetrics.includes(m.key) ? '#00E5A0' : '#8899aa',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = '#2a3649')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        flexShrink: 0,
                        background: selectedMetrics.includes(m.key) ? '#00E5A0' : '#2a3649',
                        border: '1px solid #2a3649',
                      }}
                    />
                    {m.label}
                    <span style={{ marginLeft: 'auto', fontSize: 9, color: '#445566' }}>
                      {m.unit}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div
        style={{
          background: '#1a2234',
          border: '1px solid #2a3649',
          borderRadius: 12,
          padding: 16,
        }}
      >
        {isLoading ? (
          <div
            style={{
              height: CHART_CONFIG.HEIGHTS.LOADING_STATE,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#556677',
            }}
          >
            Loading data…
          </div>
        ) : chartData.length === 0 ? (
          <div
            style={{
              height: CHART_CONFIG.HEIGHTS.LOADING_STATE,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#556677',
            }}
          >
            No data for selected metrics.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={CHART_CONFIG.HEIGHTS.SINGLE_DEVICE}>
            <LineChart data={chartDataWithIsOn} margin={CHART_CONFIG.MARGINS.SINGLE}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3649" />
              <XAxis dataKey="timestamp" tick={{ fontSize: 10, fill: '#556677' }} />
              <YAxis tick={{ fontSize: 10, fill: '#556677' }} />
              <Tooltip
                contentStyle={{
                  background: '#141D28',
                  border: '1px solid #2a3649',
                  borderRadius: 8,
                  fontSize: 11,
                }}
                labelStyle={{ color: '#8899aa' }}
              />
              <Legend wrapperStyle={{ fontSize: 11, color: '#8899aa' }} />
              {selectedMetrics.map((metricKey, i) => (
                <Line
                  key={metricKey}
                  type="monotone"
                  dataKey={metricKey}
                  name={METRIC_META[metricKey]?.label ?? metricKey}
                  stroke={CHART_CONFIG.CHART_COLORS[i % CHART_CONFIG.CHART_COLORS.length]}
                  dot={false}
                  strokeWidth={1.5}
                />
              ))}
              {renderOffPeriodAreas(chartDataWithIsOn)}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default SingleDeviceChart;
