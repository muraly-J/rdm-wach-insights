import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { saveFinancialConfig } from '../../api/financial';
import type { FinancialConfig } from '../../types';

interface Props {
  config: FinancialConfig;
  onClose: () => void;
  onSaved: (config: FinancialConfig) => void;
}

const FIELDS: { key: keyof FinancialConfig; label: string; hint: string; step?: string }[] = [
  { key: 'currency',                 label: 'Currency symbol',          hint: 'e.g. RM, USD, SGD' },
  { key: 'tariff_rate',              label: 'Electricity tariff (per kWh)', hint: 'TNB C1 default: 0.365', step: '0.001' },
  { key: 'max_demand_rate',          label: 'Max demand charge (per kVA/month)', hint: 'TNB C1 default: 30.30', step: '0.01' },
  { key: 'planned_maintenance_cost', label: 'Planned maintenance cost (per visit)', hint: 'e.g. 500', step: '1' },
  { key: 'emergency_multiplier',     label: 'Emergency repair multiplier', hint: 'e.g. 3 = 3× planned cost', step: '0.1' },
];

const FinancialSettingsDrawer: React.FC<Props> = ({ config, onClose, onSaved }) => {
  const [form, setForm] = React.useState<FinancialConfig>(config);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const saved = await saveFinancialConfig(form);
      onSaved(saved);
      onClose();
    } catch (e: any) {
      setError(e.message ?? 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  return (
    <AnimatePresence>
      {/* Backdrop */}
      <motion.div
        className="fixed inset-0 bg-black/40 z-40"
        onClick={onClose}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
      />
      {/* Drawer */}
      <motion.div
        className="fixed right-0 top-0 h-dvh w-[360px] bg-[#1c2431] border-l border-[#2e3f55] z-50 flex flex-col shadow-2xl"
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="flex items-center justify-between px-6 py-5 border-b border-[#2e3f55]">
          <h2 className="font-display text-[18px] font-bold">Financial Settings</h2>
          <button onClick={onClose} className="text-[#6d6e71] hover:text-white transition-colors text-xl">✕</button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
          {FIELDS.map(({ key, label, hint, step }) => (
            <div key={key}>
              <label className="block text-xs font-medium text-[#6d6e71] mb-1.5">{label}</label>
              <input
                type={key === 'currency' ? 'text' : 'number'}
                step={step}
                value={form[key] as string | number}
                onChange={e => setForm(prev => ({
                  ...prev,
                  [key]: key === 'currency' ? e.target.value : parseFloat(e.target.value) || 0,
                }))}
                className="w-full bg-[#2a3649] border border-[#2e3f55] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#4fbd95] transition-colors"
              />
              <p className="text-[11px] text-[#4A5568] mt-1">{hint}</p>
            </div>
          ))}
          {error && <p className="text-red-400 text-xs">{error}</p>}
        </div>
        <div className="px-6 py-4 border-t border-[#2e3f55] flex gap-3">
          <button onClick={onClose} className="flex-1 py-2 rounded-lg border border-[#2e3f55] text-[#6d6e71] text-sm hover:border-[#2A3A4A] transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-2 rounded-lg bg-[#4fbd95] text-[#1c2431] text-sm font-semibold hover:bg-[#00CC8E] transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

export default FinancialSettingsDrawer;
