import React from 'react';

interface CostBreakdownCardProps {
  label: string;
  amount: number;
  currency: string;
  description: string;
  color: string;        // accent colour e.g. '#F97316'
  isProjection?: boolean;
}

const CostBreakdownCard: React.FC<CostBreakdownCardProps> = ({
  label, amount, currency, description, color, isProjection = false,
}) => (
  <div className="card p-5 flex flex-col gap-3">
    <div className="flex items-center justify-between">
      <span className="text-sm text-[#6d6e71] font-medium">{label}</span>
      {isProjection && (
        <span className="text-[10px] px-2 py-0.5 rounded-full border border-[#3B4B5A] text-[#6d6e71]">
          projected
        </span>
      )}
    </div>
    <div className="text-[28px] font-bold font-mono" style={{ color }}>
      {currency} {amount.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
    </div>
    <p className="text-xs text-[#6d6e71] leading-relaxed">{description}</p>
  </div>
);

export default CostBreakdownCard;
