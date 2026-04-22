import React from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { fetchMeasurements } from '../../api/client';
import { CHART_CONFIG } from '../../constants/chartConfig';
import { METRIC_META } from '../../constants/metricGroups';

interface DeviceColumnProps {
  deviceId: string;
  deviceLabel: string;
  selectedMetrics: string[];
  timeRange: string;
  colorMap: Record<string, string>;
}

function toApiRange(timeRange: string): '24h' | '7d' | '30d' {
  if (timeRange === '24h' || timeRange === '7d' || timeRange === '30d') return timeRange;
  return '30d';
}

const DeviceColumn: React.FC<DeviceColumnProps> = ({
  deviceId,
  deviceLabel,
  selectedMetrics,
  timeRange,
  colorMap,
}) => {
  const [chartData, setChartData] = React.useState<Record<string, number | string | null>[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);

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

  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      <div
        style={{
          background: '#1a2234',
          border: '1px solid #2a3649',
          borderRadius: 10,
          padding: '10px 14px',
          marginBottom: 8,
        }}
      >
        <div style={{ fontSize: 10, color: '#556677', marginBottom: 2 }}>Device</div>
        <div
          style={{
            fontSize: 12,
            color: '#00E5A0',
            fontWeight: 600,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {deviceLabel}
        </div>
      </div>
      <div
        style={{
          background: '#1a2234',
          border: '1px solid #2a3649',
          borderRadius: 10,
          padding: 12,
        }}
      >
        {isLoading ? (
          <div
            className="animate-pulse rounded-lg"
            style={{
              height: CHART_CONFIG.HEIGHTS.DEVICE_COLUMN,
              background: '#2a3649',
            }}
          />
        ) : chartData.length === 0 ? (
          <div
            style={{
              height: CHART_CONFIG.HEIGHTS.DEVICE_COLUMN,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#556677',
              fontSize: 12,
            }}
          >
            No Data.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={CHART_CONFIG.HEIGHTS.DEVICE_COLUMN}>
            <LineChart data={chartData} margin={CHART_CONFIG.MARGINS.COMPARE}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3649" />
              <XAxis dataKey="timestamp" tick={{ fontSize: 9, fill: '#556677' }} />
              <YAxis tick={{ fontSize: 9, fill: '#556677' }} width={36} />
              <Tooltip
                contentStyle={{
                  background: '#141D28',
                  border: '1px solid #2a3649',
                  borderRadius: 6,
                  fontSize: 10,
                }}
              />
              {selectedMetrics.map((metricKey) => (
                <Line
                  key={metricKey}
                  type="monotone"
                  dataKey={metricKey}
                  name={METRIC_META[metricKey]?.label ?? metricKey}
                  stroke={colorMap[metricKey] ?? CHART_CONFIG.THEME.ACCENT}
                  dot={false}
                  strokeWidth={1.5}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default DeviceColumn;
