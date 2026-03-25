import { AnimatePresence, motion } from 'framer-motion';
import React from 'react';
import { formatTickByRange } from './utils/formatTick';

// ZONE A — Welcome Hero
import HeroScrollWrapper from './components/welcome/HeroScrollWrapper';

// ZONE C — Dashboard Components
import CombinedScoresChart from './components/dashboard/CombinedScoresChart';
import HealthIndexChart from './components/dashboard/HealthIndexChart';

// Nav
import SiteNavBar from './components/nav/SiteNavBar';

// Site Summary
import SiteSummaryView from './components/summary/SiteSummaryView';
import { generateSiteSummaryData } from './mocks/generateMockData';
import ScoreCardsGrid from './components/dashboard/ScoreCardsGrid';

// Health Rankings and Safety Flags
import ExpandableHealthRankings from './components/dashboard/ExpandableHealthRankings';

// Score Derivation (lazy-loaded — Section 12)
const ScoreDerivationSection = React.lazy(
  () => import('./components/dashboard/derivation/ScoreDerivationSection')
);

// Prediction View (lazy-loaded — per-device predictions)
const PredictionView = React.lazy(
  () => import('./components/prediction/PredictionView')
);

const FinancialImpactView = React.lazy(
  () => import('./components/financial/FinancialImpactView')
);

// ZONE D — Chat Widget
import ChatWidget from './components/chat/ChatWidget';

// State
import { useAppStore } from './store/useAppStore';

// API
import { fetchHealthIndex, fetchRawScoreRelationship, fetchScoreBreakdown } from './api/client';
import type { HealthIndexResponse, RawScoreResponse, ScoresResponse } from './types';

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
  const { selectedLevel, selectedDevice, timeRange, setSiteSummaryData } = useAppStore();

  // ── API State ────────────────────────────────────────────────────────────────
  const [healthData, setHealthData] = React.useState<HealthIndexResponse | null>(null);
  const [scoresData, setScoresData] = React.useState<ScoresResponse | null>(null);
  const [rawData, setRawData] = React.useState<RawScoreResponse | null>(null);
  const [safetyFlagsData, setSafetyFlagsData] = React.useState<Record<string, Array<{ flag_id: string; label: string; severity: string }>> | null>(null);
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

  // ── Load site summary data on mount ─────────────────────────────────────────
  React.useEffect(() => {
    setSiteSummaryData(generateSiteSummaryData());
  }, [setSiteSummaryData]);

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
      const timestamp = formatTickByRange(point.timestamp, timeRange);
      const entry: Record<string, any> = { timestamp };
      series.forEach(({ name, data }) => {
        entry[name] = data[idx]?.value ?? null;
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
      {/* ZONE A — Hero (collapses to nav on scroll) */}
      <HeroScrollWrapper />

      {/* ZONE C — Dashboard */}
      <div id="dashboard">
        {/* Unified controls strip */}
        <SiteNavBar devices={devices} />

        {/* Dashboard content — only shown when a level is selected */}
        <AnimatePresence mode="wait">
          {selectedLevel ? (
            <motion.main
              key={`level-${selectedLevel}`}
              className="max-w-[1280px] mx-auto px-4 sm:px-6 pt-6 sm:pt-8 pb-16 sm:pb-24"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            >
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

              {/* Health Index Chart */}
              <div id="section-health-index" style={{ scrollMarginTop: '56px' }} className="mb-8">
                <HealthIndexChart data={healthChartData} devices={chartDevices} />
              </div>

              {/* Five-Score Cards */}
              <ScoreCardsGrid scoreData={scoreCardData} />

              {/* Expandable Health Rankings */}
              {selectedLevel && (
                <div id="section-rankings" style={{ scrollMarginTop: '56px' }}>
                  <ExpandableHealthRankings
                    level={selectedLevel}
                    timeRange={timeRange}
                    scoresData={scoresData || null}
                  />
                </div>
              )}

              {/* Combined Scores Chart */}
              <CombinedScoresChart scoreData={scoreCardData} timeRange={timeRange} />

              {/* Score Derivation (single-device mode only) */}
              <AnimatePresence>
                {showDerivation && rawData && (
                  <div id="section-score-derivation" style={{ scrollMarginTop: '56px' }}>
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
                        deviceId={selectedDevice ?? ''}
                        rawData={rawData.scores}
                        timeRange={timeRange}
                      />
                    </React.Suspense>
                  </div>
                )}
              </AnimatePresence>

              {/* Prediction View (single-device mode only) */}
              {selectedDevice && selectedDevice !== 'all' && (
                <div id="section-predictions" style={{ scrollMarginTop: '56px' }}>
                  <React.Suspense fallback={<div className="h-48 animate-pulse bg-[#1E2A3A] rounded-xl" />}>
                    <PredictionView deviceId={selectedDevice} />
                  </React.Suspense>
                </div>
              )}

              {/* Financial Impact Section */}
              {selectedLevel && (
                <div id="section-financial" style={{ scrollMarginTop: '56px' }}>
                  <React.Suspense fallback={<div className="card h-48 animate-pulse bg-[#1A2230] rounded-xl" />}>
                    <FinancialImpactView
                      level={selectedLevel}
                      range={timeRange}
                      deviceId={selectedDevice !== 'all' ? selectedDevice : null}
                    />
                  </React.Suspense>
                </div>
              )}
            </motion.main>
          ) : (
            <motion.div
              key="no-level"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            >
              <SiteSummaryView />
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
