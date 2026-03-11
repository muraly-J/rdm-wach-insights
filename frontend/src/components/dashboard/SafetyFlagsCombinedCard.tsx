import React from 'react';

export interface SafetyFlag {
  flag_id: string;
  label: string;
  severity: 'High' | 'Moderate' | 'Low';
  threshold?: string;
}

interface SafetyFlagsCombinedCardProps {
  deviceId: string;
  deviceName?: string;
  safetyFlags: SafetyFlag[];
}

/**
 * SafetyFlagsCombinedCard — Displays all safety flags for a single device.
 * Used in Single Device view below the score cards.
 */
const SafetyFlagsCombinedCard: React.FC<SafetyFlagsCombinedCardProps> = ({
  deviceId,
  deviceName,
  safetyFlags,
}) => {
  // Severity color mappings
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'High':
        return 'border-[#FF4D6A] bg-[#FF4D6A]/5 text-[#FF4D6A]';
      case 'Moderate':
        return 'border-[#FFB020] bg-[#FFB020]/5 text-[#FFB020]';
      case 'Low':
        return 'border-[#00E5A0] bg-[#00E5A0]/5 text-[#00E5A0]';
      default:
        return 'border-[#8A95A5] bg-[#8A95A5]/5 text-[#8A95A5]';
    }
  };

  const getSeverityLabel = (severity: string) => {
    switch (severity) {
      case 'High':
        return 'Critical';
      case 'Moderate':
        return 'Warning';
      case 'Low':
        return 'Info';
      default:
        return severity;
    }
  };

  const getFlagIcon = (flagId: string) => {
    switch (flagId) {
      case 'THD_CHRONIC_HIGH':
        return '⚡';
      case 'IMBALANCE_SEVERE':
        return '⚖️';
      case 'PF_CHRONIC_LOW':
        return '📉';
      case 'OVERLOAD_CHRONIC':
        return '⚠️';
      default:
        return '🚩';
    }
  };

  if (safetyFlags.length === 0) {
    return (
      <div className="card p-6 mb-6">
        <h4 className="text-[20px] font-semibold text-[#E8ECF1] mb-4">Safety Flags</h4>
        <div className="text-[#00E5A0] flex items-center gap-2">
          <span className="text-xl">✓</span>
          <p className="text-sm text-[#8A95A5]">No safety flags detected for this device</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-6 mb-6">
      {/* Header */}
      <h4 className="text-[20px] font-semibold text-[#E8ECF1] mb-4 flex items-center gap-2">
        <span className="text-[#8A95A5]">⚠️</span>
        Safety Flags
      </h4>

      {/* Flag List */}
      <div className="space-y-3">
        {safetyFlags.map((flag, index) => (
          <div
            key={`${deviceId}-${flag.flag_id}`}
            className={`flex items-center justify-between p-3 rounded-lg border ${getSeverityColor(flag.severity)}`}
          >
            <div className="flex items-center gap-3">
              <span className="text-xl">{getFlagIcon(flag.flag_id)}</span>
              <div>
                <p className="font-medium text-[#E8ECF1]">{flag.label}</p>
                {flag.threshold && (
                  <p className="text-[11px] text-[#8A95A5] mt-0.5">
                    Threshold: {flag.threshold}
                  </p>
                )}
              </div>
            </div>

            <span
              className={`text-[10px] font-bold uppercase px-2 py-1 rounded ${
                flag.severity === 'High'
                  ? 'bg-[#FF4D6A]/20 text-[#FF4D6A]'
                  : flag.severity === 'Moderate'
                  ? 'bg-[#FFB020]/20 text-[#FFB020]'
                  : 'bg-[#00E5A0]/20 text-[#00E5A0]'
              }`}
            >
              {getSeverityLabel(flag.severity)}
            </span>
          </div>
        ))}
      </div>

      {/* Summary footer */}
      <div className="border-t border-[#1E2A3A] pt-4 mt-4">
        <p className="text-[11px] text-[#8A95A5]">
          {safetyFlags.length} safety flag{safetyFlags.length === 1 ? '' : 's'} detected for {deviceName || deviceId}
        </p>
      </div>
    </div>
  );
};

export default SafetyFlagsCombinedCard;
