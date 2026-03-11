import React from 'react';

interface DeviceRank {
  ahu_id: string;
  index: number; // health index (0-100)
  tier?: string;
  level?: string;
}

interface HealthRankSectionProps {
  bestDevices: DeviceRank[]; // Top 5 healthiest (highest index)
  worstDevices: DeviceRank[]; // Top 5 unhealthy (lowest index)
}

/**
 * HealthRankSection — Shows Top 5 best and worst devices when "All AHUs" view is selected.
 * Displays below HealthIndexChart component.
 */
const HealthRankSection: React.FC<HealthRankSectionProps> = ({
  bestDevices,
  worstDevices,
}) => {
  // Determine if devices exist for display
  const hasBest = bestDevices && bestDevices.length > 0;
  const hasWorst = worstDevices && worstDevices.length > 0;

  // Health index color and badge logic
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

  const RankCard: React.FC<{ rank: number; device: DeviceRank; isBest: boolean }> = ({
    rank,
    device,
    isBest,
  }) => {
    const colorClass = getHealthColor(device.index);
    const tierLabel = getTierLabel(device.index);

    return (
      <div
        className={`flex items-center justify-between p-4 rounded-xl border ${
          isBest ? 'border-[#00E5A0]/20' : 'border-[#FF4D6A]/20'
        } bg-gradient-to-r ${
          isBest
            ? 'from-[#00E5A0]/5 to-transparent'
            : 'from-[#FF4D6A]/5 to-transparent'
        }`}
      >
        {/* Rank number */}
        <div
          className={`w-10 h-10 flex items-center justify-center rounded-full text-sm font-bold mr-4 ${
            isBest
              ? 'bg-[#00E5A0]/10 text-[#00E5A0]'
              : 'bg-[#FF4D6A]/10 text-[#FF4D6A]'
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

  return (
    <div className="mb-8">
      {/* Section Header */}
      <h3 className="text-[20px] font-semibold text-[#E8ECF1] mb-6">
        Health Rankings
      </h3>

      {/* Best Devices Column */}
      <div className="mb-6">
        <h4 className="text-[14px] font-semibold text-[#8A95A5] uppercase tracking-wide mb-3 flex items-center gap-2">
          <span className="text-[#00E5A0]">✓</span>
          Top {bestDevices.length} Healthiest
        </h4>
        <div className="space-y-3">
          {hasBest ? (
            bestDevices.map((device, index) => (
              <RankCard
                key={device.ahu_id}
                rank={index + 1}
                device={device}
                isBest={true}
              />
            ))
          ) : (
            <div className="text-[#8A95A5] text-sm italic">
              No health data available
            </div>
          )}
        </div>
      </div>

      {/* Worst Devices Column */}
      <div>
        <h4 className="text-[14px] font-semibold text-[#8A95A5] uppercase tracking-wide mb-3 flex items-center gap-2">
          <span className="text-[#FF4D6A]">⚠</span>
          Top {worstDevices.length} Needs Attention
        </h4>
        <div className="space-y-3">
          {hasWorst ? (
            worstDevices.map((device, index) => (
              <RankCard
                key={device.ahu_id}
                rank={index + 1}
                device={device}
                isBest={false}
              />
            ))
          ) : (
            <div className="text-[#8A95A5] text-sm italic">
              No health data available
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HealthRankSection;
