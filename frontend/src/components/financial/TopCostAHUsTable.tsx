import React from 'react';
import type { AHUCost } from '../../types';

interface Props {
  ahus: AHUCost[];
  currency: string;
}

function fmt(n: number) {
  return n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function tierColor(hi: number) {
  if (hi >= 80) return 'text-[#4fbd95]';
  if (hi >= 60) return 'text-yellow-400';
  if (hi >= 40) return 'text-orange-400';
  return 'text-red-400';
}

const TopCostAHUsTable: React.FC<Props> = ({ ahus, currency }) => {
  if (!ahus.length) return (
    <div className="card p-6 text-center text-[#6d6e71] text-sm">No data available</div>
  );

  return (
    <div className="card p-0 overflow-hidden">
      <div className="px-6 py-4 border-b border-[#2e3f55]">
        <h3 className="font-display text-[18px] font-bold">Top AHUs by Financial Impact</h3>
        <p className="text-xs text-[#6d6e71] mt-1">Ranked by estimated total cost — prioritise these for maintenance</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#2e3f55]">
              {['#', 'AHU', 'Health', 'Excess Energy', 'PF Penalty', 'Maint. Risk', 'Total'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs text-[#6d6e71] font-medium whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ahus.map((row, i) => (
              <tr key={row.ahu_id} className="border-b border-[#2e3f55]/50 hover:bg-[#2a3649]/50 transition-colors">
                <td className="px-4 py-3 text-[#6d6e71] text-xs">{i + 1}</td>
                <td className="px-4 py-3 font-mono text-white font-medium">{row.ahu_id}</td>
                <td className={`px-4 py-3 font-mono font-bold ${tierColor(row.health_index)}`}>
                  {row.health_index.toFixed(0)}
                </td>
                <td className="px-4 py-3 text-[#6d6e71]">{currency} {fmt(row.excess_energy_cost)}</td>
                <td className="px-4 py-3 text-[#6d6e71]">{currency} {fmt(row.pf_penalty_cost)}</td>
                <td className="px-4 py-3 text-[#6d6e71]">{currency} {fmt(row.maintenance_risk)}</td>
                <td className="px-4 py-3 font-bold text-white">{currency} {fmt(row.total_cost)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TopCostAHUsTable;
