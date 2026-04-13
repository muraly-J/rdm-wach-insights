import React from 'react';
import { motion } from 'framer-motion';

interface DeviceSelectorProps {
  devices: Array<{ id: string; name: string; label?: string; department?: string }>;
  selectedDevice: string | null;
  onSelectDevice: (deviceId: string | null) => void;
}

/**
 * DeviceSelector - Horizontal scrollable chip row for device selection (Section 5.4)
 *
 * Trigger: Within level view, below level selector
 * Default: "All AHUs" (aggregate / multi-line view)
 */
const DeviceSelector: React.FC<DeviceSelectorProps> = ({
  devices,
  selectedDevice,
  onSelectDevice,
}) => {
  const allDevicesOption = { id: 'all', name: 'All AHUs' };

  return (
    <div className="mb-6">
      <div className="flex items-center gap-3 mb-3 px-1">
        <span
          className="
            font-display uppercase tracking-[0.2em]
            text-xs text-[#6d6e71]
          "
        >
          DEVICE
        </span>
        <div className="h-px flex-1 bg-[#2e3f55]" />
      </div>

      <div className="flex flex-wrap items-center gap-2.5 scrollbar-hidden">
        {/* "All AHUs" option */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => onSelectDevice(allDevicesOption.id)}
          className={`
            px-4 py-3 min-h-[44px] sm:py-2 sm:min-h-0 text-xs font-medium rounded-full transition-all duration-0.25s flex items-center justify-center
            border relative
            ${
              selectedDevice === null || selectedDevice === 'all'
                ? 'bg-[#4fbd95] text-[#1c2431] border-0'
                : 'bg-transparent text-[#6d6e71] border-[#2e3f55] hover:border-[#4fbd95]'
            }
          `}
        >
          {allDevicesOption.name}
        </motion.button>

        {/* Individual device chips */}
        {devices.map((device) => (
          <motion.button
            key={device.id}
            title={[device.label, device.department].filter(Boolean).join(' — ') || device.id}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onSelectDevice(device.id)}
            className={`
              px-4 py-3 min-h-[44px] sm:py-2 sm:min-h-0 text-xs font-medium rounded-full transition-all duration-0.25s flex items-center justify-center
              border relative
              ${
                selectedDevice === device.id
                  ? 'bg-[#4fbd95] text-[#1c2431] border-0'
                  : 'bg-transparent text-[#6d6e71] border-[#2e3f55] hover:border-[#4fbd95]'
              }
            `}
          >
            {device.id}
          </motion.button>
        ))}
      </div>
    </div>
  );
};

export default DeviceSelector;
