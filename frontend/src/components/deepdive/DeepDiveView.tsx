import React from 'react';
import { useAppStore, DeepDiveSubMode } from '../../store/useAppStore';
import { DeviceInfo } from '../../utils/deviceLabel';
import SingleDeviceChart from './SingleDeviceChart';
import CompareMode from './CompareMode';

interface DeepDiveViewProps {
  levelDevices: DeviceInfo[];
  labelMap: Record<string, string>;
  timeRange: string;
}

const DeepDiveView: React.FC<DeepDiveViewProps> = ({ levelDevices, labelMap, timeRange }) => {
  const { selectedDevice, deepDiveSubMode, setDeepDiveSubMode, compareDevices } = useAppStore();

  const hasDevice = Boolean(selectedDevice && selectedDevice !== 'all');
  const hasCompareDevices = compareDevices.length >= 2;

  return (
    <div>
      <div style={{ display: 'inline-flex', background: '#1a2234', border: '1px solid #2a3649', borderRadius: 10, padding: 3, marginBottom: 20 }}>
        {(['single', 'compare'] as DeepDiveSubMode[]).map((mode) => {
          const isActive = deepDiveSubMode === mode;
          return (
            <button
              key={mode}
              onClick={() => setDeepDiveSubMode(mode)}
              style={{
                background: isActive ? 'rgba(0,229,160,0.15)' : 'transparent',
                color: isActive ? '#00E5A0' : '#8899aa',
                border: isActive ? '1px solid #00E5A044' : '1px solid transparent',
                borderRadius: 8, padding: '5px 14px', fontSize: 12,
                fontWeight: isActive ? 600 : 400, cursor: 'pointer',
              }}
            >
              {mode === 'single' ? 'Single Device' : 'Compare Mode'}
            </button>
          );
        })}
      </div>

      {deepDiveSubMode === 'single' ? (
        hasDevice ? (
          <SingleDeviceChart
            deviceId={selectedDevice!}
            deviceLabel={labelMap[selectedDevice!] ?? selectedDevice!}
            timeRange={timeRange}
          />
        ) : (
          <div style={{ padding: 40, textAlign: 'center', color: '#556677', fontSize: 13 }}>
            Select a device to begin deep dive analysis.
          </div>
        )
      ) : (
        hasCompareDevices ? (
          <CompareMode
            deviceIds={compareDevices}
            labelMap={labelMap}
            timeRange={timeRange}
          />
        ) : (
          <div style={{ padding: 40, textAlign: 'center', color: '#556677', fontSize: 13 }}>
            Select 2–3 devices using the Device filter above to compare them.
          </div>
        )
      )}
    </div>
  );
};

export default DeepDiveView;
