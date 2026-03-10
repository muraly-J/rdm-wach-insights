import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';

// ZONE A — Welcome Hero
import WelcomeHero from './components/welcome/WelcomeHero';

// ZONE B — Dashboard Gate
import DashboardGate from './components/dashboard/DashboardGate';

// ZONE C — Dashboard Components
import LevelSelectorBar from './components/dashboard/LevelSelectorBar';
import DeviceSelector from './components/dashboard/DeviceSelector';
import HealthIndexChart from './components/dashboard/HealthIndexChart';
import ScoreCardsGrid from './components/dashboard/ScoreCardsGrid';
import CombinedScoresChart from './components/dashboard/CombinedScoresChart';

// Score Derivation (lazy-loaded — Section 12)
const ScoreDerivationSection = React.lazy(
  () => import('./components/dashboard/derivation/ScoreDerivationSection')
);

// ZONE D — Chat Widget
import ChatWidget from './components/chat/ChatWidget';

// State
import { useAppStore } from './store/useAppStore';

// Mock data
import {
  generateHealthIndex,
  generateScoreBreakdowns,
  generateRawScoreRelationship,
} from './mocks/generateMockData';

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

interface ScoreEntry {
  current: number;
  trend: number;
  data: Array<{ timestamp: string; value: number }>;
}

// ──────────────────────────────────────────────────────────────────────────────
// App
// ──────────────────────────────────────────────────────────────────────────────

function App() {
  const { selectedLevel, selectedDevice, selectDevice } = useAppStore();

  // ── Mock data per level ─────────────────────────────────────────────────────
  const mockHealthIndex = React.useMemo(
    () => (selectedLevel ? generateHealthIndex(selectedLevel, 48) : []),
    [selectedLevel]
  );

  const mockScoreBreakdowns = React.useMemo(
    () => (selectedLevel ? generateScoreBreakdowns(selectedLevel, 48) : []),
    [selectedLevel]
  );

  // ── Devices ─────────────────────────────────────────────────────────────────
  const devices = React.useMemo(
    () => mockHealthIndex.map((item) => item.device),
    [mockHealthIndex]
  );

  // ── Health Index chart data (merge by timestamp index) ───────────────────────
  const healthChartData = React.useMemo(() => {
    if (mockHealthIndex.length === 0) return [];

    // If a specific device is selected, show only that device
    const series =
      selectedDevice && selectedDevice !== 'all'
        ? mockHealthIndex.filter((d) => d.device.id === selectedDevice)
        : mockHealthIndex;

    // Use first device's timestamps as the reference
    const refData = series[0]?.data ?? [];
    return refData.map((point, idx) => {
      const entry: Record<string, any> = {
        timestamp: new Date(point.timestamp).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
        }),
      };
      series.forEach(({ device, data }) => {
        entry[device.name] = data[idx]?.value ?? null;
      });
      return entry;
    });
  }, [mockHealthIndex, selectedDevice]);

  // Devices visible in the chart (all or single)
  const chartDevices = React.useMemo(() => {
    if (selectedDevice && selectedDevice !== 'all') {
      return devices.filter((d) => d.id === selectedDevice);
    }
    return devices;
  }, [devices, selectedDevice]);

  // ── Score card data (aggregate across devices for "all", or single device) ──
  const scoreCardData = React.useMemo<Record<string, ScoreEntry>>(() => {
    if (mockScoreBreakdowns.length === 0) return {};

    const scoreNames = ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload'] as const;

    // Filter to selected device if applicable
    const relevantBreakdowns =
      selectedDevice && selectedDevice !== 'all'
        ? mockScoreBreakdowns.filter((d) => d.id === selectedDevice)
        : mockScoreBreakdowns;

    if (relevantBreakdowns.length === 0) return {};

    const result: Record<string, ScoreEntry> = {};

    scoreNames.forEach((name) => {
      const allScores = relevantBreakdowns.map((d) => d.scores[name]);
      const count = allScores.length;

      const avgCurrent = allScores.reduce((s, v) => s + v.current, 0) / count;
      const avgTrend = allScores.reduce((s, v) => s + v.trend, 0) / count;

      const pointCount = allScores[0]?.data.length ?? 0;
      const avgData = Array.from({ length: pointCount }, (_, i) => ({
        timestamp: allScores[0]?.data[i]?.timestamp ?? '',
        value: allScores.reduce((s, v) => s + (v.data[i]?.value ?? 0), 0) / count,
      }));

      result[name] = { current: avgCurrent, trend: avgTrend, data: avgData };
    });

    return result;
  }, [mockScoreBreakdowns, selectedDevice]);

  // ── Raw-score relationship data (single device only) ─────────────────────────
  const rawRelationData = React.useMemo(() => {
    if (!selectedDevice || selectedDevice === 'all') return null;
    return generateRawScoreRelationship(selectedDevice, 48);
  }, [selectedDevice]);

  const showDerivation = Boolean(selectedDevice && selectedDevice !== 'all');

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#0B0F14] text-[#E8ECF1]">
      {/* ZONE A — Welcome Hero (100 vh) */}
      <WelcomeHero />

      {/* ZONE B — Dashboard Gate */}
      <DashboardGate />

      {/* ZONE C — Dashboard */}
      <div id="dashboard">
        {/* Sticky level selector */}
        <LevelSelectorBar />

        {/* Dashboard content — only shown when a level is selected */}
        <AnimatePresence mode="wait">
          {selectedLevel ? (
            <motion.main
              key={`level-${selectedLevel}`}
              className="max-w-[1280px] mx-auto px-6 pt-8 pb-24"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            >
              {/* Device selector sub-bar */}
              <DeviceSelector
                devices={devices}
                selectedDevice={selectedDevice}
                onSelectDevice={selectDevice}
              />

              {/* Health Index Chart */}
              <div className="mb-8">
                <HealthIndexChart data={healthChartData} devices={chartDevices} />
              </div>

              {/* Five-Score Cards */}
              <ScoreCardsGrid scoreData={scoreCardData} />

              {/* Combined Scores Chart */}
              <CombinedScoresChart scoreData={scoreCardData} />

              {/* Score Derivation (single-device mode only) */}
              <AnimatePresence>
                {showDerivation && rawRelationData && (
                  <React.Suspense
                    fallback={
                      <div className="card p-6 h-40 flex items-center justify-center">
                        <span className="text-[#8A95A5]">Loading derivation charts…</span>
                      </div>
                    }
                  >
                    <ScoreDerivationSection
                      deviceName={
                        devices.find((d) => d.id === selectedDevice)?.name ?? selectedDevice ?? ''
                      }
                      rawData={rawRelationData.scores}
                    />
                  </React.Suspense>
                )}
              </AnimatePresence>
            </motion.main>
          ) : (
            <motion.div
              key="no-level"
              className="max-w-[1280px] mx-auto px-6 py-16 text-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <p className="text-[#8A95A5] text-lg">
                Select a building level above to start exploring AHU health data.
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ZONE D — Floating Chat Widget */}
      <ChatWidget />
    </div>
  );
}

export default App;
