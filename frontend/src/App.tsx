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
import { useAppStore, TimeRange } from './store/useAppStore';

// API
import { fetchHealthIndex, fetchScoreBreakdown, fetchRawScoreRelationship } from './api/client';
import type { HealthIndexResponse, ScoresResponse, RawScoreResponse } from './types';

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

interface ScoreEntry {
  current: number;
  trend: number;
  data: Array<{ timestamp: string; value: number }>;
}

const TIME_RANGES: TimeRange[] = ['24h', '7d', '30d'];

// ──────────────────────────────────────────────────────────────────────────────
// App
// ──────────────────────────────────────────────────────────────────────────────

function App() {
  const { selectedLevel, selectedDevice, selectDevice, timeRange, setTimeRange } = useAppStore();

  // ── API State ────────────────────────────────────────────────────────────────
  const [healthData, setHealthData] = React.useState<HealthIndexResponse | null>(null);
  const [scoresData, setScoresData] = React.useState<ScoresResponse | null>(null);
  const [rawData, setRawData] = React.useState<RawScoreResponse | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // ── Fetch health index + score breakdown whenever level/device/range changes ─
  React.useEffect(() => {
    if (!selectedLevel) return;
    setIsLoading(true);
    setError(null);

    Promise.all([
      fetchHealthIndex(selectedLevel, timeRange, selectedDevice),
      fetchScoreBreakdown(selectedLevel, timeRange),
    ])
      .then(([health, scores]) => {
        setHealthData(health);
        setScoresData(scores);
      })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, [selectedLevel, selectedDevice, timeRange]);

  // ── Fetch raw-score relationship when a single device is selected ────────────
  React.useEffect(() => {
    if (!selectedDevice || selectedDevice === 'all') {
      setRawData(null);
      return;
    }
    fetchRawScoreRelationship(selectedDevice, timeRange)
      .then((data) => setRawData(data as RawScoreResponse))
      .catch(() => setRawData(null));
  }, [selectedDevice, timeRange]);

  // ── Devices list derived from health data ────────────────────────────────────
  const devices = React.useMemo(
    () =>
      (healthData?.devices ?? []).map((d) => ({
        id: d.id,
        name: d.name,
        label: d.label,
        department: d.department,
        level: selectedLevel!,
      })),
    [healthData, selectedLevel]
  );

  // ── Health Index chart data ──────────────────────────────────────────────────
  const healthChartData = React.useMemo(() => {
    if (!healthData?.devices?.length) return [];

    const series =
      selectedDevice && selectedDevice !== 'all'
        ? healthData.devices.filter((d) => d.id === selectedDevice)
        : healthData.devices;

    const refData = series[0]?.data ?? [];
    return refData.map((point, idx) => {
      const d = new Date(point.timestamp);
      const timestamp =
        timeRange === '24h'
          ? d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
          : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

      const entry: Record<string, any> = { timestamp };
      series.forEach(({ name, data }) => {
        const val = data[idx]?.value;
        entry[name] = val !== undefined && val !== null ? parseFloat((100 - val).toFixed(2)) : null;
      });
      return entry;
    });
  }, [healthData, selectedDevice, timeRange]);

  // Devices visible in the chart
  const chartDevices = React.useMemo(() => {
    if (selectedDevice && selectedDevice !== 'all') {
      return devices.filter((d) => d.id === selectedDevice);
    }
    return devices;
  }, [devices, selectedDevice]);

  // ── Score card data ──────────────────────────────────────────────────────────
  const scoreCardData = React.useMemo<Record<string, ScoreEntry>>(() => {
    if (!scoresData?.devices?.length) return {};

    const scoreNames = ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload'] as const;

    const relevantDevices =
      selectedDevice && selectedDevice !== 'all'
        ? scoresData.devices.filter((d) => d.id === selectedDevice)
        : scoresData.devices;

    if (relevantDevices.length === 0) return {};

    const result: Record<string, ScoreEntry> = {};
    scoreNames.forEach((name) => {
      const allScores = relevantDevices
        .map((d) => d.scores[name])
        .filter(Boolean);
      if (allScores.length === 0) return;
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
  }, [scoresData, selectedDevice]);

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
              {/* Time range picker */}
              <div className="flex gap-2 justify-end mb-4">
                {TIME_RANGES.map((range) => (
                  <button
                    key={range}
                    onClick={() => setTimeRange(range)}
                    className={`px-3 py-1 rounded text-sm border transition-colors ${
                      timeRange === range
                        ? 'bg-[#1E2A3A] border-[#3B82F6] text-white'
                        : 'bg-transparent border-[#1E2A3A] text-[#8A95A5] hover:border-[#3B82F6]'
                    }`}
                  >
                    {range}
                  </button>
                ))}
              </div>

              {/* Loading indicator */}
              {isLoading && (
                <div className="flex justify-center py-4">
                  <span className="text-[#8A95A5] text-sm animate-pulse">Loading data…</span>
                </div>
              )}

              {/* Error state */}
              {error && !isLoading && (
                <div className="mb-4 px-4 py-3 rounded bg-red-900/20 border border-red-700 text-red-400 text-sm">
                  Failed to load data: {error}
                </div>
              )}

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
              <CombinedScoresChart scoreData={scoreCardData} timeRange={timeRange} />

              {/* Score Derivation (single-device mode only) */}
              <AnimatePresence>
                {showDerivation && rawData && (
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
                      rawData={rawData.scores}
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
