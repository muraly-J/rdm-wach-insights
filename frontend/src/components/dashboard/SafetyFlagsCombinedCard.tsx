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
        return 'border-[#e96852] bg-[#e96852]/5 text-[#e96852]';
      case 'Moderate':
        return 'border-[#f9a020] bg-[#f9a020]/5 text-[#f9a020]';
      case 'Low':
        return 'border-[#4fbd95] bg-[#4fbd95]/5 text-[#4fbd95]';
      default:
        return 'border-[#6d6e71] bg-[#6d6e71]/5 text-[#6d6e71]';
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
        <div className="text-[#4fbd95] flex items-center gap-2">
          <span className="text-xl">✓</span>
          <p className="text-sm text-[#6d6e71]">No safety flags detected for this device</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-6 mb-6">
      {/* Header */}
      <h4 className="text-[20px] font-semibold text-[#E8ECF1] mb-4 flex items-center gap-2">
        <span className="text-[#6d6e71]">⚠️</span>
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
                  <p className="text-[11px] text-[#6d6e71] mt-0.5">
                    Threshold: {flag.threshold}
                  </p>
                )}
              </div>
            </div>

            <span
              className={`text-[10px] font-bold uppercase px-2 py-1 rounded ${
                flag.severity === 'High'
                  ? 'bg-[#e96852]/20 text-[#e96852]'
                  : flag.severity === 'Moderate'
                  ? 'bg-[#f9a020]/20 text-[#f9a020]'
                  : 'bg-[#4fbd95]/20 text-[#4fbd95]'
              }`}
            >
              {getSeverityLabel(flag.severity)}
            </span>
          </div>
        ))}
      </div>

      {/* Summary footer */}
      <div className="border-t border-[#2e3f55] pt-4 mt-4">
        <p className="text-[11px] text-[#6d6e71]">
          {safetyFlags.length} safety flag{safetyFlags.length === 1 ? '' : 's'} detected for {deviceName || deviceId}
        </p>
      </div>
    </div>
  );
};

export default SafetyFlagsCombinedCard;
