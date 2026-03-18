import React from 'react';
import { motion } from 'framer-motion';
import { fetchFinancialConfig, fetchFinancialImpact } from '../../api/financial';
import CostBreakdownCard from './CostBreakdownCard';
import TopCostAHUsTable from './TopCostAHUsTable';
import FinancialSettingsDrawer from './FinancialSettingsDrawer';
import { useAppStore } from '../../store/useAppStore';
import type { FinancialConfig, FinancialImpact } from '../../types';

interface Props {
  level: number;
  range?: '24h' | '7d' | '30d';
  deviceId?: string | null;
}

const FinancialImpactView: React.FC<Props> = ({ level, range = '30d', deviceId }) => {
  const setFinancialImpact = useAppStore((s) => s.setFinancialImpact);
  const [config, setConfig]           = React.useState<FinancialConfig | null>(null);
  const [impact, setImpact]           = React.useState<FinancialImpact | null>(null);
  const [loading, setLoading]         = React.useState(true);
  const [error, setError]             = React.useState<string | null>(null);
  const [drawerOpen, setDrawerOpen]   = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cfg, imp] = await Promise.all([
        fetchFinancialConfig(),
        fetchFinancialImpact(level, range, deviceId),
      ]);
      setConfig(cfg);
      setImpact(imp);
      setFinancialImpact(imp);
    } catch (e: any) {
      setError(e.message ?? 'Failed to load financial data');
    } finally {
      setLoading(false);
    }
  }, [level, range, deviceId]);

  React.useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div className="space-y-4">
      <div className="card h-32 animate-pulse bg-[#1A2230]" />
      <div className="grid grid-cols-3 gap-4">
        {[0,1,2].map(i => <div key={i} className="card h-28 animate-pulse bg-[#1A2230]" />)}
      </div>
    </div>
  );

  if (error || !impact || !config) return (
    <div className="card p-6 flex items-center justify-center h-32">
      <span className="text-[#8A95A5] text-sm">Financial data unavailable</span>
    </div>
  );

  const cur = impact.currency;

  return (
    <motion.div
      className="mb-12 space-y-6"
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-display text-[28px] font-bold tracking-[-0.01em]">
            Financial Impact
          </h3>
          <p className="text-[#8A95A5] mt-1 text-sm">
            {deviceId ? `${deviceId} · ` : ''}Estimated cost of current AHU health issues · Last {range}
          </p>
        </div>
        <button
          onClick={() => setDrawerOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[#1E2A3A] text-[#8A95A5] text-sm hover:border-[#00E5A0] hover:text-[#00E5A0] transition-colors"
        >
          ⚙ Configure
        </button>
      </div>

      {/* Headline card */}
      <div className="card p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <p className="text-[#8A95A5] text-sm mb-1">Estimated monthly savings opportunity</p>
          <div className="text-[42px] font-bold font-mono text-[#00E5A0]">
            {cur} {impact.grand_total.toLocaleString('en-MY', { minimumFractionDigits: 2 })}
          </div>
          <p className="text-xs text-[#4A5568] mt-1">
            {deviceId
              ? `${deviceId} on Level ${level}`
              : `Across ${impact.top_ahus.length} AHUs on Level ${level} · ${impact.top_ahus.filter(a => a.health_index < 60).length} at elevated risk`
            }
          </p>
        </div>
        <div className="text-[#8A95A5] text-xs text-right hidden md:block max-w-[200px]">
          Based on TNB tariff {cur} {config.tariff_rate}/kWh and{' '}
          {cur} {config.planned_maintenance_cost} planned maintenance cost.{' '}
          Maintenance risk is a projection.
        </div>
      </div>

      {/* Three breakdown cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <CostBreakdownCard
          label="Excess Energy Waste"
          amount={impact.excess_energy_cost}
          currency={cur}
          color="#60A5FA"
          description="kWh consumed above predicted baseline × tariff rate. Driven by energy anomaly scores."
        />
        <CostBreakdownCard
          label="TNB Power Factor Penalty"
          amount={impact.pf_penalty_cost}
          currency={cur}
          color="#F97316"
          description="TNB surcharge: 1.5% per 0.01 that average monthly PF falls below 0.85 (ASHRAE / IEEE 141)."
        />
        <CostBreakdownCard
          label="Maintenance Risk Exposure"
          amount={impact.maintenance_risk}
          currency={cur}
          color="#C084FC"
          description="AHUs with health index < 60 risk emergency repairs. Saving = (multiplier − 1) × planned cost."
          isProjection
        />
      </div>

      {/* Top AHUs table */}
      <TopCostAHUsTable ahus={impact.top_ahus} currency={cur} />

      {/* Settings drawer */}
      {drawerOpen && config && (
        <FinancialSettingsDrawer
          config={config}
          onClose={() => setDrawerOpen(false)}
          onSaved={(saved) => { setConfig(saved); load(); }}
        />
      )}
    </motion.div>
  );
};

export default FinancialImpactView;
