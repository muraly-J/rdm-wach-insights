import React from 'react';
import { DeepDiveSubMode, useAppStore } from '../../store/useAppStore';
import { DeviceInfo } from '../../utils/deviceLabel';
// import { fetchOffPeriods } from '../../api/client';
import type { OffPeriod } from '../../types';
import CompareMode from './CompareMode';
import SingleDeviceChart from './SingleDeviceChart';

interface DeepDiveViewProps {
  levelDevices: DeviceInfo[];
  labelMap: Record<string, string>;
  timeRange: string;
  isSelectedDeviceOn?: boolean;
  healthChartData?: Array<{ timestamp?: string; is_on?: boolean; [key: string]: any }>;
  isOnByTimestamp?: Record<string, boolean>;
}

const DeepDiveView: React.FC<DeepDiveViewProps> = ({
  levelDevices,
  labelMap,
  timeRange,
  isSelectedDeviceOn = true,
  healthChartData,
  isOnByTimestamp = {},
}) => {
  const { selectedDevice, deepDiveSubMode, setDeepDiveSubMode, compareDevices } = useAppStore();
  const [offPeriods, setOffPeriods] = React.useState<OffPeriod[]>([]);

  React.useEffect(() => {
    if (!selectedDevice || selectedDevice === 'all') {
      setOffPeriods([]);
      return;
    }
    // Temporarily disabled until backend is redeployed with on-off-periods endpoint
    // fetchOffPeriods(selectedDevice, timeRange as '24h' | '7d' | '30d').then(setOffPeriods);
    setOffPeriods([]);
  }, [selectedDevice, timeRange]);

  const hasDevice = Boolean(selectedDevice && selectedDevice !== 'all');
  const hasCompareDevices = compareDevices.length >= 2;

  return (
    <div>
      <div
        style={{
          display: 'inline-flex',
          background: '#1a2234',
          border: '1px solid #2a3649',
          borderRadius: 10,
          padding: 3,
          marginBottom: 20,
        }}
      >
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
                borderRadius: 8,
                padding: '5px 14px',
                fontSize: 12,
                fontWeight: isActive ? 600 : 400,
                cursor: 'pointer',
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
            isOn={isSelectedDeviceOn}
            healthChartData={healthChartData}
            isOnByTimestamp={isOnByTimestamp}
          />
        ) : (
          <div style={{ padding: 40, textAlign: 'center', color: '#556677', fontSize: 13 }}>
            Select a Device to Begin Deep Dive Analysis.
          </div>
        )
      ) : hasCompareDevices ? (
        <CompareMode deviceIds={compareDevices} labelMap={labelMap} timeRange={timeRange} />
      ) : (
        <div style={{ padding: 40, textAlign: 'center', color: '#556677', fontSize: 13 }}>
          Select 2–3 Devices Using the Device Filter Above to Compare Them.
        </div>
      )}
    </div>
  );
};

export default DeepDiveView;
