import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { formatTickByRange } from './utils/formatTick';
import { buildLabelMap } from './utils/deviceLabel';

// Nav
import FilterBar from './components/nav/FilterBar';

// Dashboard
import KPIStrip from './components/dashboard/KPIStrip';
import ModeToggle from './components/dashboard/ModeToggle';
import AHURankingsTable, { AHURankRow, AHUStatus } from './components/dashboard/AHURankingsTable';
import DeviceDetailCard from './components/dashboard/DeviceDetailCard';
import HealthIndexChart from './components/dashboard/HealthIndexChart';
import ScoreCardsGrid from './components/dashboard/ScoreCardsGrid';
import CombinedScoresChart from './components/dashboard/CombinedScoresChart';

// Deep Dive (lazy)
const DeepDiveView = React.lazy(() => import('./components/deepdive/DeepDiveView'));

// Score Derivation (lazy, device-only)
const ScoreDerivationSection = React.lazy(
  () => import('./components/dashboard/derivation/ScoreDerivationSection')
);

// Prediction (lazy, device-only)
const PredictionView = React.lazy(() => import('./components/prediction/PredictionView'));

// Chat
import ChatWidget from './components/chat/ChatWidget';

// State
import { useAppStore } from './store/useAppStore';

// API
import {
  fetchHealthIndex, fetchLevelDevices, fetchRawScoreRelationship,
  fetchScoreBreakdown, fetchSiteSummary, fetchDashboardRanking, fetchOffPeriods,
} from './api/client';
import { fetchFinancialImpact } from './api/financial';
import type { HealthIndexResponse, RawScoreResponse, ScoresResponse, OffPeriod } from './types';
import type { TimeRange } from './utils/formatTick';

interface ScoreEntry {
  current: number;
  trend: number;
  data: Array<{ timestamp: string; value: number }>;
}

function getStatus(score: number): AHUStatus {
  if (score >= 80) return 'Good';
  if (score >= 60) return 'Warning';
  return 'Critical';
}

/** Pass through the app's TimeRange, including 'all' if set */
function toApiRange(timeRange: string): '24h' | '7d' | '30d' | 'all' {
  if (timeRange === '24h') return '24h';
  if (timeRange === '7d') return '7d';
  if (timeRange === 'all') return 'all';
  return '30d';
}

function App() {
  const {
    selectedLevel, selectedDevice, timeRange,
    setSiteSummaryData, siteSummaryData,
    dashboardMode,
    setFinancialImpact,
  } = useAppStore();

  const [healthData, setHealthData] = React.useState<HealthIndexResponse | null>(null);
  const [scoresData, setScoresData] = React.useState<ScoresResponse | null>(null);
  const [rawData, setRawData] = React.useState<RawScoreResponse | null>(null);
  const [rankingRows, setRankingRows] = React.useState<AHURankRow[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [offPeriods, setOffPeriods] = React.useState<OffPeriod[]>([]);

  const [levelDevices, setLevelDevices] = React.useState<
    Array<{ id: string; label: string; department: string; area: string }>
  >([]);

  React.useEffect(() => {
    if (!selectedLevel) { setLevelDevices([]); return; }
    fetchLevelDevices(selectedLevel)
      .then((r) => setLevelDevices(r.devices))
      .catch(() => setLevelDevices([]));
  }, [selectedLevel]);

  const labelMap = React.useMemo(() => buildLabelMap(levelDevices), [levelDevices]);

  React.useEffect(() => {
    if (!selectedLevel) return;
    setIsLoading(true);
    setError(null);
    const range = toApiRange(timeRange);
    Promise.all([
      fetchHealthIndex(selectedLevel, range as '24h' | '7d' | '30d' | 'all', selectedDevice),
      fetchScoreBreakdown(selectedLevel, range as '24h' | '7d' | '30d' | 'all'),
    ])
      .then(([health, scores]) => {
        setHealthData(health);
        setScoresData(scores);
      })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, [selectedLevel, selectedDevice, timeRange]);

  React.useEffect(() => {
    if (!selectedDevice || selectedDevice === 'all') { setRawData(null); return; }
    const range = toApiRange(timeRange);
    fetchRawScoreRelationship(selectedDevice, range as '24h' | '7d' | '30d' | 'all')
      .then((data) => setRawData(data as RawScoreResponse))
      .catch(() => setRawData(null));
  }, [selectedDevice, timeRange]);

  // Fetch off-periods when a single device is selected
  React.useEffect(() => {
    if (!selectedDevice || selectedDevice === 'all') {
      setOffPeriods([]);
      return;
    }
    const range = toApiRange(timeRange);
    fetchOffPeriods(selectedDevice, range as '24h' | '7d' | '30d').then(setOffPeriods);
  }, [selectedDevice, timeRange]);

  React.useEffect(() => {
    const range = toApiRange(timeRange);
    fetchSiteSummary(range as '24h' | '7d' | '30d' | 'all')
      .then((data) => setSiteSummaryData(data))
      .catch(() => {});
  }, [timeRange, setSiteSummaryData]);

  React.useEffect(() => {
    if (!selectedLevel) return;
    const range = toApiRange(timeRange);
    fetchFinancialImpact(selectedLevel, range as '24h' | '7d' | '30d' | 'all', selectedDevice !== 'all' ? selectedDevice : null)
      .then((data) => setFinancialImpact(data))
      .catch(() => {});
  }, [selectedLevel, selectedDevice, timeRange, setFinancialImpact]);

  React.useEffect(() => {
    if (!selectedLevel) { setRankingRows([]); return; }
    const rangeMap: Record<string, 'last_24h' | 'last_7d' | 'last_30d'> = {
      '24h': 'last_24h', '7d': 'last_7d', '30d': 'last_30d', 'all': 'last_30d',
    };
    const apiRange = rangeMap[timeRange] ?? 'last_7d';
    fetchDashboardRanking(selectedLevel, apiRange)
      .then((data: any) => {
        const allDevices = [...(data.best ?? []), ...(data.worst ?? [])];
        const seen = new Set<string>();
        const rows: AHURankRow[] = allDevices
          .filter((d: any) => { if (seen.has(d.ahu_id)) return false; seen.add(d.ahu_id); return true; })
          .map((d: any) => ({
            id: d.ahu_id,
            label: labelMap[d.ahu_id] ?? d.ahu_id,
            level: selectedLevel,
            healthScore: d.index,
            trend: d.trend ?? 0,
            status: getStatus(d.index),
          }));
        setRankingRows(rows);
      })
      .catch(() => setRankingRows([]));
  }, [selectedLevel, timeRange, labelMap]);

  const chartRange = toApiRange(timeRange) as TimeRange;

  const healthChartData = React.useMemo(() => {
    if (!healthData?.devices?.length) return [];
    const series = selectedDevice && selectedDevice !== 'all'
      ? healthData.devices.filter((d) => d.id === selectedDevice)
      : healthData.devices;

    // For single device: preserve all data points with is_on field
    if (selectedDevice && selectedDevice !== 'all') {
      const deviceName = labelMap[series[0]?.id] ?? series[0]?.id;
      return series[0]?.data?.map((point: any) => ({
        timestamp: formatTickByRange(point.timestamp, chartRange),
        [deviceName]: point.value,
        is_on: point.is_on,
      })) || [];
    }

    // For all devices: merge by index (simple approach), no on/off logic
    const refData = series[0]?.data ?? [];
    return refData.map((point, idx) => {
      const timestamp = formatTickByRange(point.timestamp, chartRange);
      const entry: Record<string, any> = { timestamp };
      series.forEach(({ id, data }) => {
        entry[labelMap[id] ?? id] = data[idx]?.value ?? null;
      });
      return entry;
    });
  }, [healthData, selectedDevice, chartRange, labelMap]);

  const isSingleDevice = selectedDevice && selectedDevice !== 'all';

  const chartDevices = React.useMemo(() => {
    if (selectedDevice && selectedDevice !== 'all') {
      return levelDevices
        .filter((d) => d.id === selectedDevice)
        .map((d) => ({ id: d.id, name: labelMap[d.id] ?? d.id, label: d.label, department: d.department, level: selectedLevel! }));
    }
    return levelDevices.map((d) => ({
      id: d.id, name: labelMap[d.id] ?? d.id,
      label: d.label, department: d.department, level: selectedLevel!,
    }));
  }, [levelDevices, selectedDevice, labelMap, selectedLevel]);

  const scoreCardData = React.useMemo<Record<string, ScoreEntry>>(() => {
    if (!scoresData?.devices?.length) return {};
    const scoreNames = ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload'] as const;
    const relevantDevices = selectedDevice && selectedDevice !== 'all'
      ? scoresData.devices.filter((d) => d.id === selectedDevice)
      : scoresData.devices;
    if (relevantDevices.length === 0) return {};
    const result: Record<string, ScoreEntry> = {};
    scoreNames.forEach((name) => {
      const allScores = relevantDevices.map((d) => d.scores[name]).filter(Boolean);
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

  const deviceHealth = React.useMemo(() => {
    if (!selectedDevice || selectedDevice === 'all' || !healthData) return null;
    const dev = healthData.devices.find((d) => d.id === selectedDevice);
    if (!dev?.data?.length) return null;
    return dev.data[dev.data.length - 1]?.value ?? null;
  }, [healthData, selectedDevice]);

  const deviceLabel = selectedDevice ? (labelMap[selectedDevice] ?? selectedDevice) : null;
  const showDerivation = Boolean(selectedDevice && selectedDevice !== 'all');
  const selectedDeviceRow = rankingRows.find((r) => r.id === selectedDevice);

  const isSelectedDeviceOn = React.useMemo(() => {
    if (!selectedDevice || selectedDevice === 'all' || !healthData) return true;
    const dev = healthData.devices.find((d) => d.id === selectedDevice);
    return dev?.is_on ?? true;
  }, [healthData, selectedDevice]);

  return (
    <div className="min-h-screen bg-[#0B0F14] text-[#E8ECF1]">
      <FilterBar levelDevices={levelDevices} />

      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 pt-6 pb-16">
        <KPIStrip
          summary={siteSummaryData}
          selectedLevel={selectedLevel}
          selectedDevice={selectedDevice}
          deviceLabel={deviceLabel}
          deviceHealth={deviceHealth}
        />

        <ModeToggle />

        {isLoading && (
          <div className="flex justify-center py-4">
            <span className="text-[#556677] text-sm animate-pulse">Loading data…</span>
          </div>
        )}
        {error && !isLoading && (
          <div className="mb-4 px-4 py-3 rounded bg-red-900/20 border border-red-700 text-red-400 text-sm">
            Failed to load data: {error}
          </div>
        )}

        <AnimatePresence mode="wait">
          {dashboardMode === 'simple' ? (
            <motion.div
              key="simple"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
            >
              {selectedLevel ? (
                <>
                  <div className="mb-8">
                    <HealthIndexChart
                      data={healthChartData as any}
                      devices={chartDevices}
                      showColorSegments={isSingleDevice}
                      offPeriods={
                        isSingleDevice
                          ? offPeriods.map((p) => ({
                              start: formatTickByRange(p.start, chartRange),
                              end: formatTickByRange(p.end, chartRange),
                            }))
                          : undefined
                      }
                    />
                  </div>

                  <ScoreCardsGrid scoreData={scoreCardData} />

                  <CombinedScoresChart
                    scoreData={scoreCardData}
                    timeRange={chartRange}
                    offPeriods={isSingleDevice ? offPeriods : undefined}
                  />

                  {selectedDevice && selectedDevice !== 'all' && selectedDeviceRow ? (
                    <DeviceDetailCard
                      label={selectedDeviceRow.label}
                      level={selectedDeviceRow.level}
                      healthScore={selectedDeviceRow.healthScore}
                      trend={selectedDeviceRow.trend}
                      status={selectedDeviceRow.status}
                      isOn={isSelectedDeviceOn}
                    />
                  ) : (
                    <AHURankingsTable rows={rankingRows} />
                  )}

                  {showDerivation && rawData && (
                    <React.Suspense fallback={<div className="card p-6 h-40 flex items-center justify-center"><span className="text-[#556677]">Loading derivation…</span></div>}>
                      <ScoreDerivationSection
                        deviceName={deviceLabel ?? selectedDevice ?? ''}
                        deviceId={selectedDevice ?? ''}
                        rawData={rawData}
                        timeRange={chartRange}
                      />
                    </React.Suspense>
                  )}

                  {selectedDevice && selectedDevice !== 'all' && (
                    <div className="mt-8">
                      <React.Suspense fallback={<div className="h-48 animate-pulse bg-[#2e3f55] rounded-xl" />}>
                        <PredictionView deviceId={selectedDevice} />
                      </React.Suspense>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex items-center justify-center h-48 text-[#556677]">
                  Select a level to view dashboard data.
                </div>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="deepdive"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
            >
              <React.Suspense fallback={<div className="h-64 animate-pulse bg-[#1a2234] rounded-xl" />}>
                <DeepDiveView levelDevices={levelDevices} labelMap={labelMap} timeRange={timeRange} isSelectedDeviceOn={isSelectedDeviceOn} />
              </React.Suspense>
            </motion.div>
          )}
        </AnimatePresence>

        <p className="text-center text-xs mt-12 pb-4" style={{ color: '#3a4a5a' }}>
          ⚠ Data shown covers monitored AHUs only. Not all devices may be represented.
        </p>
      </div>

      <ChatWidget />
    </div>
  );
}

export default App;
