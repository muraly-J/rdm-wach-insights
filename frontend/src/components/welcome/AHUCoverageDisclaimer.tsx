import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * AHUCoverageDisclaimer
 *
 * Compact collapsible notice surfacing AHUs that could not be correlated
 * to monitoring device IDs from the physical asset list.
 *
 * Data sourced from docs/ahu_relationships.tsv audit.
 */

type GapGroup = {
  level: string;
  department: string;
  count: number;
  reason: string;
};

// Derived from docs/ahu_relationships.tsv — AHUs with no device_id or ambiguous mapping
const UNLINKED_AHUS: GapGroup[] = [
  { level: 'L01', department: 'Crèche / Nursery',                  count: 1,  reason: 'No matching device prefix found (L1-CN)' },
  { level: 'L02', department: 'ART Centre (O&G)',                   count: 4,  reason: 'No matching device prefix found (L2-AC)' },
  { level: 'L03', department: 'Genetic Department',                 count: 2,  reason: 'No matching device prefix found (L3-GL)' },
  { level: 'L03', department: 'Paediatric Specialist Clinic',       count: 2,  reason: 'No matching device prefix found (L3-EOA)' },
  { level: 'L04', department: 'Bone Marrow Transplant Unit',        count: 13, reason: 'L4-SCT range partially mapped; 13 units unresolved' },
  { level: 'L04', department: 'Inpatient Pharmacy (TPN)',           count: 2,  reason: 'No matching device prefix found (AHU-TPN)' },
  { level: 'L04', department: 'Labour and Delivery Unit',           count: 3,  reason: 'No matching device prefix found (L4-LDS)' },
  { level: 'L04', department: 'Neonatal ICU',                       count: 2,  reason: 'No matching device prefix found (L4-NI)' },
];

const AMBIGUOUS_AHUS: GapGroup[] = [
  { level: 'L04', department: 'Bone Marrow Transplant (SCT-01)',    count: 1,  reason: 'Duplicate mapping — same device ID as another AHU (e0409)' },
  { level: 'L05', department: 'Main Operation Theatre (OT-10)',     count: 1,  reason: 'Duplicate mapping — shares e0622 with another AHU' },
  { level: 'L05', department: 'Operation Theatre (L6-OT)',          count: 1,  reason: 'Level prefix mismatch — AHU label says L6 but located on L5' },
  { level: 'L06', department: 'Specialist Office Complex (SOC-01)', count: 1,  reason: 'Duplicate mapping — shares e0607 with another AHU' },
  { level: 'L08', department: 'Inpatient Wards — Gynaecology 1',   count: 1,  reason: 'Duplicate mapping — shares e0804 with another AHU' },
  { level: 'L08', department: 'Inpatient Wards — Gynaecology 2',   count: 1,  reason: 'Duplicate mapping — shares e0805 with another AHU' },
];

const totalUnlinked  = UNLINKED_AHUS.reduce((s, g) => s + g.count, 0);
const totalAmbiguous = AMBIGUOUS_AHUS.reduce((s, g) => s + g.count, 0);
const totalGap       = totalUnlinked + totalAmbiguous;

const AHUCoverageDisclaimer: React.FC = () => {
  const [open, setOpen] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.75 }}
      className="mt-3 w-full max-w-[600px] mx-auto"
    >
      {/* Trigger row */}
      <button
        onClick={() => setOpen(v => !v)}
        className="
          w-full flex items-center gap-2.5 px-3 py-2 rounded-md
          border border-[#F59E0B]/20 bg-[#F59E0B]/5
          hover:bg-[#F59E0B]/10 hover:border-[#F59E0B]/35
          transition-colors duration-200 group text-left
        "
      >
        {/* Warning icon */}
        <span className="text-[#F59E0B] text-[13px] flex-shrink-0">⚠</span>

        <span className="text-[12px] text-[#A89060] flex-1 leading-snug">
          <span className="text-[#D4A847] font-medium">{totalGap} AHUs</span> could not be correlated to monitoring points and are excluded from this dashboard.
        </span>

        {/* Chevron */}
        <motion.span
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="text-[#6B7280] text-[10px] flex-shrink-0"
        >
          ▾
        </motion.span>
      </button>

      {/* Expanded detail */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="
              mt-1 rounded-md border border-[#1E2530]
              bg-[#0D1117] text-left divide-y divide-[#1A2030]
            ">
              {/* Unlinked section */}
              <div className="px-3 py-2">
                <p className="text-[11px] text-[#F59E0B]/70 font-medium uppercase tracking-wider mb-1.5">
                  Unlinked — {totalUnlinked} AHUs
                </p>
                <div className="space-y-1">
                  {UNLINKED_AHUS.map((g, i) => (
                    <div key={i} className="flex gap-2 items-baseline">
                      <span className="text-[11px] text-[#4B5563] w-7 flex-shrink-0 font-mono">{g.level}</span>
                      <span className="text-[11px] text-[#6B7280] flex-1">{g.department}</span>
                      <span className="text-[11px] text-[#D4A847] flex-shrink-0 tabular-nums">{g.count}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Ambiguous section */}
              <div className="px-3 py-2">
                <p className="text-[11px] text-[#F59E0B]/70 font-medium uppercase tracking-wider mb-1.5">
                  Duplicate / Mismatched — {totalAmbiguous} AHUs
                </p>
                <div className="space-y-1">
                  {AMBIGUOUS_AHUS.map((g, i) => (
                    <div key={i} className="flex gap-2 items-baseline">
                      <span className="text-[11px] text-[#4B5563] w-7 flex-shrink-0 font-mono">{g.level}</span>
                      <span className="text-[11px] text-[#6B7280] flex-1">{g.department}</span>
                      <span className="text-[11px] text-[#D4A847] flex-shrink-0 tabular-nums">{g.count}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Footer note */}
              <div className="px-3 py-2">
                <p className="text-[11px] text-[#4B5563] leading-relaxed">
                  These AHUs exist in the physical asset register but their monitoring device IDs could not be confirmed.
                  Data gaps are under investigation. Currently <span className="text-[#00E5A0]">121 AHUs</span> across 11 levels are actively monitored.
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default AHUCoverageDisclaimer;
