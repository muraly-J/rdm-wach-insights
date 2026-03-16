// frontend/src/components/prediction/DeltaBadge.tsx
interface DeltaBadgeProps {
  deltaKwh: number;
  horizon: string;
  baseline?: number;
}

export default function DeltaBadge({ deltaKwh, horizon, baseline }: DeltaBadgeProps) {
  const absVal = Math.abs(deltaKwh).toFixed(1);
  const sign = deltaKwh >= 0 ? '+' : '−';
  const pct = baseline && baseline > 0
    ? ` (${sign}${Math.abs((deltaKwh / baseline) * 100).toFixed(0)}%)`
    : '';

  const color =
    deltaKwh > 3 ? 'text-red-400' :
    deltaKwh < -3 ? 'text-yellow-400' :
    'text-[#00E5A0]';

  const label =
    deltaKwh >= 0
      ? `Predicted +${absVal} kWh above baseline${pct} over next ${horizon}`
      : `Predicted −${absVal} kWh below baseline${pct} over next ${horizon}`;

  return (
    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1E2A3A] border border-[#2A3A4A] ${color}`}>
      <span className="text-sm font-semibold font-mono">{label}</span>
    </div>
  );
}
