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
            text-[13px] text-[#8A95A5]
          "
        >
          DEVICE
        </span>
        <div className="h-px flex-1 bg-[#1E2A3A]" />
      </div>

      <div className="flex flex-wrap items-center gap-2.5 scrollbar-hidden">
        {/* "All AHUs" option */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => onSelectDevice(allDevicesOption.id)}
          className={`
            px-4 py-2 text-xs font-medium rounded-full transition-all duration-0.25s
            border relative
            ${selectedDevice === null || selectedDevice === 'all'
              ? 'bg-[#00E5A0] text-[#0B0F14] border-0'
              : 'bg-transparent text-[#8A95A5] border-[#1E2A3A] hover:border-[#00E5A0]'
            }
          `}
        >
          {allDevicesOption.name}
        </motion.button>

        {/* Individual device chips */}
        {devices.slice(0, 20).map((device) => (
          <motion.button
            key={device.id}
            title={[device.label, device.department].filter(Boolean).join(' — ') || device.id}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onSelectDevice(device.id)}
            className={`
              px-4 py-2 text-xs font-medium rounded-full transition-all duration-0.25s
              border relative
              ${selectedDevice === device.id
                ? 'bg-[#00E5A0] text-[#0B0F14] border-0'
                : 'bg-transparent text-[#8A95A5] border-[#1E2A3A] hover:border-[#00E5A0]'
              }
            `}
          >
            {device.id}
          </motion.button>
        ))}

        {/* Expand indicator if more devices */}
        {devices.length > 20 && (
          <span className="text-xs text-[#8A95A5] px-2">+{devices.length - 20} more</span>
        )}
      </div>
    </div>
  );
};

export default DeviceSelector;
