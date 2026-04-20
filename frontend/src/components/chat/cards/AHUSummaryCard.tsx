import type { AHUSummary } from '../../../types/chat';
import { HEALTH_TIER_COLORS } from '../../../types/chat';

interface AHUSummaryCardProps {
  summary: AHUSummary;
}

const FAIR_LABELS = ['F', 'A', 'I', 'R'] as const;

export default function AHUSummaryCard({ summary }: AHUSummaryCardProps) {
  const color = HEALTH_TIER_COLORS[summary.severity] ?? '#4DA6FF';

  return (
    <div
      className="rounded-[10px] px-3.5 py-2.5 mt-2"
      style={{ background: '#141920', border: `1px solid ${color}33` }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="inline-block w-1.5 h-1.5 rounded-full" style={{ background: color }} />
        <span className="text-[13px] font-semibold text-[#E8ECF1]">{summary.ahu_id}</span>
        <span className="text-[10px] text-[#556677]">Level {summary.level}</span>
        <span className="ml-auto text-[10px] font-semibold uppercase" style={{ color }}>
          {summary.severity}
        </span>
      </div>

      {/* FAIR score bars */}
      <div className="flex gap-1.5">
        {FAIR_LABELS.map((label) => {
          const value = summary.fair[label];
          return (
            <div key={label} className="flex-1">
              <div className="flex justify-between text-[9px] text-[#556677] mb-0.5">
                <span>{label}</span>
                <span>{value}</span>
              </div>
              <div className="h-1 rounded-sm bg-[#1a2638] overflow-hidden">
                <div
                  className="h-full rounded-sm transition-all duration-300"
                  style={{
                    width: `${value}%`,
                    background: value >= 70 ? '#00E5A0' : value >= 40 ? '#FFB020' : '#FF4D4D',
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Composite */}
      <div className="mt-1.5 flex justify-between text-[11px] text-[#8899aa]">
        <span>Composite</span>
        <span className="font-semibold" style={{ color }}>
          {summary.fair.composite}
        </span>
      </div>
    </div>
  );
}
