// frontend/src/components/prediction/PredictionChart.tsx
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { PredictionResponse, PredictionMetric, PredictionPoint } from '../../api/predictions';

interface PredictionChartProps {
  data: PredictionResponse;
  metric: PredictionMetric;
}

const METRIC_LABELS: Record<PredictionMetric, string> = {
  energy_import: 'Energy (kWh)',
  power_total: 'Power (kW)',
  power_factor_avg: 'Power Factor',
  current_unbalance: 'Current Unbalance (%)',
  composite_thd: 'THD (%)',
};

function toChartPoint(p: PredictionPoint, metric: PredictionMetric) {
  return { x: p.offset_hours, y: p[metric] };
}

export default function PredictionChart({ data, metric }: PredictionChartProps) {
  const yesterday = data.history_profiles.yesterday.map((p) => toChartPoint(p, metric));
  const lastWeek = data.history_profiles.last_week.map((p) => toChartPoint(p, metric));
  const twoWeeksAgo = data.history_profiles.two_weeks_ago.map((p) => toChartPoint(p, metric));
  const actuals = data.actuals.map((p) => toChartPoint(p, metric));

  const predPoints = Object.entries(data.horizons).map(([, h]) => ({
    x: h.offset_hours,
    y: h.predictions[metric] ?? null,
  }));

  const allX = new Set([
    ...yesterday.map((p) => p.x),
    ...lastWeek.map((p) => p.x),
    ...twoWeeksAgo.map((p) => p.x),
    ...actuals.map((p) => p.x),
    ...predPoints.map((p) => p.x),
  ]);
  const sortedX = Array.from(allX).sort((a, b) => a - b);

  function toMap(arr: { x: number; y: number | null }[]) {
    return Object.fromEntries(arr.map((p) => [p.x, p.y]));
  }

  const ydMap = toMap(yesterday);
  const lwMap = toMap(lastWeek);
  const twMap = toMap(twoWeeksAgo);
  const actMap = toMap(actuals);
  const predMap = toMap(predPoints);

  const chartData = sortedX.map((x) => ({
    x,
    yesterday: ydMap[x] ?? null,
    last_week: lwMap[x] ?? null,
    two_weeks_ago: twMap[x] ?? null,
    actual: actMap[x] ?? null,
    prediction: predMap[x] ?? null,
  }));

  const horizonOffsets = Object.values(data.horizons).map((h) => h.offset_hours);

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={chartData} margin={{ top: 16, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2e3f55" />
        <XAxis
          dataKey="x"
          type="number"
          domain={[-48, Math.max(168, ...horizonOffsets)]}
          ticks={[-48, -24, 0, 1, 12, 24, 168]}
          tickFormatter={(v) => (v === 0 ? 'Now' : v > 0 ? `+${v}h` : `${v}h`)}
          stroke="#4A5568"
          tick={{ fill: '#6d6e71', fontSize: 11 }}
        />
        <YAxis
          stroke="#4A5568"
          tick={{ fill: '#6d6e71', fontSize: 11 }}
          label={{
            value: METRIC_LABELS[metric],
            angle: -90,
            position: 'insideLeft',
            fill: '#6d6e71',
            fontSize: 10,
          }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#131A23',
            border: '1px solid #2e3f55',
            borderRadius: 8,
          }}
          labelFormatter={(v) => `Offset: ${v}h`}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: '#6d6e71' }} />

        {horizonOffsets.map((offset) => (
          <ReferenceLine
            key={offset}
            x={offset}
            stroke="#2A3A4A"
            strokeDasharray="4 2"
            label={{ value: `+${offset}h`, position: 'top', fill: '#4A5568', fontSize: 10 }}
          />
        ))}
        <ReferenceLine x={0} stroke="#4A5568" strokeWidth={1} />

        <Line
          dataKey="two_weeks_ago"
          name="2 Weeks Ago"
          stroke="#555"
          strokeDasharray="4 4"
          dot={false}
          connectNulls={false}
        />
        <Line dataKey="last_week" name="Last Week" stroke="#888" dot={false} connectNulls={false} />
        <Line
          dataKey="yesterday"
          name="Yesterday"
          stroke="#60a5fa"
          dot={false}
          connectNulls={false}
        />
        <Line
          dataKey="actual"
          name="Today (actual)"
          stroke="#4fbd95"
          strokeWidth={2}
          dot={false}
          connectNulls={false}
        />
        <Line
          dataKey="prediction"
          name="Prediction"
          stroke="#4fbd95"
          strokeWidth={2}
          strokeDasharray="6 3"
          dot={{ r: 5, fill: '#4fbd95' }}
          connectNulls={true}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
