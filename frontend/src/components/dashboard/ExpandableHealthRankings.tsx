import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { DeviceRank, ScoresResponse } from '../../types';

// ──────────────────────────────────────────────────────────────────────────────
// Expandable Health Rankings Component
// Shows Top 5 best and worst devices when expanded
// Uses existing scoresData prop to avoid slow InfluxDB queries
// ──────────────────────────────────────────────────────────────────────────────

interface ExpandableHealthRankingsProps {
  level: number;
  timeRange: '24h' | '7d' | '30d';
  scoresData?: ScoresResponse;
}

// ──────────────────────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────────────────────

const getHealthColor = (index: number) => {
  if (index >= 80) return 'text-[#00E5A0]';
  if (index >= 60) return 'text-[#FFB020]';
  if (index >= 40) return 'text-[#FFA500]';
  return 'text-[#FF4D6A]';
};

const getTierLabel = (index: number) => {
  if (index >= 80) return 'Healthy';
  if (index >= 60) return 'Monitor';
  if (index >= 40) return 'Maintenance Soon';
  return 'Critical';
};

const getTierColor = (index: number) => {
  if (index >= 80) return 'bg-[#00E5A0]/10 border-[#00E5A0]/30 text-[#00E5A0]';
  if (index >= 60) return 'bg-[#FFB020]/10 border-[#FFB020]/30 text-[#FFB020]';
  if (index >= 40) return 'bg-[#FFA500]/10 border-[#FFA500]/30 text-[#FFA500]';
  return 'bg-[#FF4D6A]/10 border-[#FF4D6A]/30 text-[#FF4D6A]';
};

const getRankBadgeColor = (index: number, isBest: boolean) => {
  if (isBest) {
    if (index >= 80) return 'bg-[#00E5A0]/10 text-[#00E5A0]';
    if (index >= 60) return 'bg-[#FFB020]/10 text-[#FFB020]';
    return 'bg-[#FFA500]/10 text-[#FFA500]';
  } else {
    if (index >= 40) return 'bg-[#FF4D6A]/10 text-[#FF4D6A]';
    return 'bg-[#7C5CFC]/10 text-[#7C5CFC]';
  }
};

// ──────────────────────────────────────────────────────────────────────────────
// Device Card Component
// ──────────────────────────────────────────────────────────────────────────────

const DeviceRankCard: React.FC<{ rank: number; device: DeviceRank; isBest: boolean }> = ({
  rank,
  device,
  isBest,
}) => {
  const colorClass = getHealthColor(device.index);
  const tierLabel = getTierLabel(device.index);

  return (
    <div
      className={`flex items-center justify-between p-4 rounded-xl border transition-all duration-200 hover:border-current ${
        isBest
          ? 'border-[#00E5A0]/20 hover:border-[#00E5A0]'
          : 'border-[#FF4D6A]/20 hover:border-[#FF4D6A]'
      } bg-gradient-to-r ${
        isBest
          ? 'from-[#00E5A0]/5 to-transparent'
          : 'from-[#FF4D6A]/5 to-transparent'
      }`}
    >
      {/* Rank number */}
      <div
        className={`w-10 h-10 flex items-center justify-center rounded-full text-sm font-bold mr-4 ${
          getRankBadgeColor(device.index, isBest)
        }`}
      >
        #{rank}
      </div>

      {/* Device info */}
      <div className="flex-1">
        <p className="text-[#E8ECF1] font-medium text-[15px]">{device.ahu_id}</p>
        <div className="flex items-center gap-2 mt-1">
          <span
            className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
              getTierColor(device.index)
            }`}
          >
            {tierLabel}
          </span>
        </div>
      </div>

      {/* Health index number */}
      <div className="text-right">
        <span className={`font-mono text-[24px] font-bold ${colorClass}`}>
          {device.index.toFixed(1)}
        </span>
        <span className="text-[#8A95A5] text-xs block">/ 100</span>
      </div>
    </div>
  );
};

// ──────────────────────────────────────────────────────────────────────────────
// Main Component
// ──────────────────────────────────────────────────────────────────────────────

const ExpandableHealthRankings: React.FC<ExpandableHealthRankingsProps> = ({
  level,
  timeRange,
  scoresData,
}) => {
  const [expanded, setExpanded] = useState(false);

  // Compute best/worst from existing scores data (no API call needed)
  const { best, worst } = React.useMemo(() => {
    // Handle null/undefined scoresData
    if (!scoresData || !Array.isArray(scoresData.devices) || scoresData.devices.length === 0) {
      return { best: [], worst: [] };
    }

    // Step 1: Find the LATEST timestamp across ALL devices and ALL scores
    let latestTimestamp = new Date('1970-01-01').getTime();
    for (const device of scoresData.devices) {
      const scores = device.scores || {};
      for (const scoreKey in scores) {
        const scoreData = scores[scoreKey];
        if (scoreData?.data && Array.isArray(scoreData.data)) {
          for (const point of scoreData.data) {
            if (point?.timestamp) {
              const ts = new Date(point.timestamp).getTime();
              if (ts > latestTimestamp) {
                latestTimestamp = ts;
              }
            }
          }
        }
      }
    }

    // Step 2: Compute health index for each device at the LATEST timestamp
    const devicesWithHealth = scoresData.devices.map((device) => {
      const scores = device.scores || {};
      
      // Use health_index directly if available
      const healthScoreData = scores['health_index'];
      let indexValue = 0;
      
      if (healthScoreData && healthScoreData.data && Array.isArray(healthScoreData.data)) {
        // Find the value at the latest timestamp
        const point = healthScoreData.data.find((p: any) => {
          return new Date(p.timestamp).getTime() === latestTimestamp;
        });
        
        if (point && typeof point.value === 'number') {
          indexValue = point.value;
        } else if (typeof healthScoreData.current === 'number') {
          indexValue = healthScoreData.current;
        }
      }

      return {
        ahu_id: device.id,
        name: device.name || '',
        index: Number.isFinite(indexValue) ? indexValue : 0,
        tier: getTierLabel(Number.isFinite(indexValue) ? indexValue : 0),
        level: `Level ${level}`,
      };
    });

    // Step 3: Sort by health index descending for best devices
    const sorted = devicesWithHealth.sort((a, b) => b.index - a.index);

    const top5 = sorted.slice(0, 5);
    const bottom5 = sorted.slice(-5).reverse(); // Reverse to show lowest first

    return {
      best: top5,
      worst: bottom5,
    };
  }, [scoresData, level]);

  // Compute averages for collapsed state
  const bestAvg = React.useMemo(() => {
    if (!best || best.length === 0) return 0;
    const total = best.reduce((sum: number, d) => sum + (d.index || 0), 0);
    return best.length > 0 ? total / best.length : 0;
  }, [best]);

  const worstAvg = React.useMemo(() => {
    if (!worst || worst.length === 0) return 0;
    const total = worst.reduce((sum: number, d) => sum + (d.index || 0), 0);
    return worst.length > 0 ? total / worst.length : 0;
  }, [worst]);

  // Render single rank card with animation
  const renderRankCard = (device: DeviceRank, index: number, isBest: boolean) => {
    return (
      <motion.div
        key={device.ahu_id}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: index * 0.05 }}
      >
        <DeviceRankCard rank={index + 1} device={device} isBest={isBest} />
      </motion.div>
    );
  };

  return (
    <div className="mb-10">
      {/* Header Section */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-[20px] font-semibold text-[#E8ECF1]">Health Rankings</h3>

        {/* Expand/Collapse Trigger */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="group flex items-center gap-2 text-sm font-medium transition-colors hover:text-[#3B82F6]"
        >
          <span className="text-[#8A95A5] group-hover:text-[#3B82F6]">
            {expanded ? 'Hide device rankings' : 'Click for more information'}
          </span>
          <motion.span
            animate={{ rotate: expanded ? 180 : 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
          >
            ↓
          </motion.span>
        </button>
      </div>

      {/* Expanded Content */}
      <AnimatePresence mode="wait">
        {expanded && (
          <motion.div
            key="rankings-content"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            {/* Best Devices Section */}
            <div className="mb-8">
              <h4 className="text-[14px] font-semibold text-[#8A95A5] uppercase tracking-wide mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#00E5A0]"></span>
                Top {best.length} Healthiest AHUs
              </h4>
              <div className="space-y-3">
                {best.length > 0 ? (
                  best.map((device, index) => renderRankCard(device, index, true))
                ) : (
                  <div className="text-[#8A95A5] text-sm italic pl-4">
                    No health data available for best devices
                  </div>
                )}
              </div>
            </div>

            {/* Worst Devices Section */}
            <div className="mb-2">
              <h4 className="text-[14px] font-semibold text-[#8A95A5] uppercase tracking-wide mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#FF4D6A]"></span>
                Top {worst.length} Needs Attention
              </h4>
              <div className="space-y-3">
                {worst.length > 0 ? (
                  worst.map((device, index) => renderRankCard(device, index, false))
                ) : (
                  <div className="text-[#8A95A5] text-sm italic pl-4">
                    No health data available for worst devices
                  </div>
                )}
              </div>
            </div>

            {/* Footer / Time Range Indicator */}
            <div className="pt-6 border-t border-[#1E2A3A]">
              <p className="text-center text-[10px] text-[#64748B]">
                Time range: {timeRange}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Collapsed State - Summary Only */}
      {!expanded && (
        <div className="grid grid-cols-2 gap-4">
          {/* Best Average Card */}
          <div className="card p-4 border border-[#00E5A0]/20 bg-[#00E5A0]/5">
            <p className="text-xs text-[#8A95A5] uppercase tracking-wide mb-1">Best AHUs Avg</p>
            <div className="flex items-baseline gap-2">
              <span className="text-[#00E5A0] font-mono text-2xl font-bold">
                {bestAvg.toFixed(1)}
              </span>
              <span className="text-[#8A95A5] text-sm">/ 100</span>
            </div>
          </div>

          {/* Worst Average Card */}
          <div className="card p-4 border border-[#FF4D6A]/20 bg-[#FF4D6A]/5">
            <p className="text-xs text-[#8A95A5] uppercase tracking-wide mb-1">Worst AHUs Avg</p>
            <div className="flex items-baseline gap-2">
              <span className="text-[#FF4D6A] font-mono text-2xl font-bold">
                {worstAvg.toFixed(1)}
              </span>
              <span className="text-[#8A95A5] text-sm">/ 100</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExpandableHealthRankings;
