import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// ─────────────────────────────────────────────────────────────────────────────
// ExpandableMetricCard Component
// Scroll-to-enlarge plot system with Sparkline preview and lazy-loaded chart
//
// Props:
//   - title: Metric title (e.g., "Energy Anomaly")
//   - metricKey: Internal key for the metric
//   - value: Current value
//   - sparklineData: Data for the small preview chart
//   - fullChartData: Data for the expanded chart (loaded lazily)
//   - summaryText: AI-generated summary
//   - latestData: Most recent data point
// ─────────────────────────────────────────────────────────────────────────────

const ExpandableMetricCard = ({
  title,
  metricKey,
  value,
  sparklineData = [],
  summaryText = '',
  latestData = '',
  accentColor = '#10b981',
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [hasLoadedChart, setHasLoadedChart] = useState(false);

  // Lazy load chart on expansion
  const handleExpand = () => {
    if (!hasLoadedChart) {
      setHasLoadedChart(true);
    }
    setIsExpanded(!isExpanded);
  };

  // Close on second click if already expanded
  const handleToggle = () => {
    if (isExpanded) {
      setIsExpanded(false);
    } else {
      handleExpand();
    }
  };

  // Color mapping
  const getColors = () => {
    switch (metricKey) {
      case 'energy_anomaly':
        return { primary: '#ef4444', secondary: '#b91c1c' };
      case 'pf_degradation':
        return { primary: '#f59e0b', secondary: '#d97706' };
      case 'phase_imbalance':
        return { primary: '#fbbf24', secondary: '#ca8a04' };
      case 'thd_drift':
        return { primary: '#60a5fa', secondary: '#3b82f6' };
      case 'overload':
        return { primary: '#f97316', secondary: '#ea580c' };
      default:
        return { primary: accentColor, secondary: '#10b981' };
    }
  };

  const colors = getColors();

  // Sparkline component (lightweight)
  const Sparkline = ({ data }) => {
    if (!data || data.length === 0) {
      return (
        <div style={{ height: '60px', display: 'flex', alignItems: 'center' }}>
          <span style={{ color: '#6b7280', fontSize: '0.75rem' }}>No data</span>
        </div>
      );
    }

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    // Create smooth SVG path
    const points = data.map((val, i) => {
      const x = (i / (data.length - 1)) * 100;
      const y = 60 - ((val - min) / range) * 50;
      return `${x},${y}`;
    }).join(' ');

    return (
      <svg width="100%" height="60" viewBox="0 0 100 60" preserveAspectRatio="none">
        <polyline
          points={points}
          fill="none"
          stroke={colors.primary}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d={`${points} 100,60 0,60`}
          fill={colors.primary}
          opacity="0.1"
        />
      </svg>
    );
  };

  // Chart loader component
  const ChartLoader = () => (
    <motion.div
      style={{
        height: '400px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <motion.div
        style={{
          textAlign: 'center',
        }}
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 2, repeat: Infinity }}
      >
        <div
          style={{
            width: '40px',
            height: '40px',
            border: `3px solid ${colors.primary}`,
            borderRadius: '50%',
            margin: '0 auto 16px',
          }}
        />
        <div style={{ color: colors.primary, fontSize: '0.875rem' }}>
          Loading chart...
        </div>
      </motion.div>
    </motion.div>
  );

  // Placeholder chart (since we don't have Recharts import yet)
  const ChartPlaceholder = () => (
    <div
      style={{
        height: '400px',
        width: '100%',
        position: 'relative',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `linear-gradient(180deg, ${colors.primary}20 0%, transparent 100%)`,
          borderRadius: '16px',
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div
          style={{
            padding: '40px',
            textAlign: 'center',
            background: 'rgba(23, 26, 33, 0.9)',
            borderRadius: '16px',
          }}
        >
          <div
            style={{
              fontSize: '4rem',
              marginBottom: '20px',
              background: `linear-gradient(135deg, ${colors.primary}, ${colors.secondary})`,
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            📊
          </div>
          <h3 style={{ color: '#eaf0fb', marginBottom: '8px' }}>
            {title} Analysis
          </h3>
          <p style={{ color: '#a3aab5', marginBottom: '16px' }}>
            Interactive chart with time-series data
          </p>
          <div style={{ display: 'flex', gap: '12px' }}>
            <span
              style={{
                background: '#10b98120',
                color: '#10b981',
                padding: '6px 12px',
                borderRadius: '4px',
                fontSize: '0.75rem',
              }}
            >
              Real-time
            </span>
            <span
              style={{
                background: '#f59e0b20',
                color: '#f59e0b',
                padding: '6px 12px',
                borderRadius: '4px',
                fontSize: '0.75rem',
              }}
            >
              Predictive
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  // Expand trigger component
  const ExpandTrigger = () => (
    <motion.button
      className="card-expand-trigger"
      onClick={handleToggle}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke={colors.primary}
        strokeWidth="2"
      >
        {isExpanded ? (
          <path d="M19 12H5" strokeLinecap="round" />
        ) : (
          <>
            <path d="M12 5v14" strokeLinecap="round" />
            <path d="m19 12-7 7-7-7" strokeLinecap="round" strokeLinejoin="round" />
          </>
        )}
      </svg>
      {isExpanded ? 'Collapse Chart' : 'Expand Analysis'}
    </motion.button>
  );

  return (
    <motion.div
      className="expandable-card"
      initial={false}
      animate={{
        height: isExpanded ? 'auto' : undefined,
      }}
    >
      {/* Collapsed State */}
      <motion.div
        className="card-header"
        onClick={handleToggle}
        layoutId={`header-${metricKey}`}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <motion.div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '12px',
              background: `linear-gradient(135deg, ${colors.primary}40, ${colors.secondary}20)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <span style={{ fontSize: '1.5rem' }}>📈</span>
          </motion.div>
          <div>
            <h3 className="card-title">{title}</h3>
            <div style={{ fontSize: '0.75rem', color: '#a3aab5' }}>
              Current: {value}
            </div>
          </div>
        </div>
        <ExpandTrigger />
      </motion.div>

      {/* Expanded Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            className="card-content expanded"
            layoutId={`content-${metricKey}`}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          >
            {/* Summary Panel (Left) */}
            <motion.div className="summary-panel" layoutId={`summary-${metricKey}`}>
              <div className="summary-header">AI Analysis</div>
              <motion.div
                style={{
                  fontSize: '0.9375rem',
                  color: '#eaf0fb',
                  lineHeight: '1.8',
                }}
              >
                {summaryText || (
                  <span style={{ opacity: 0.6 }}>
                    No AI analysis available for this metric.
                  </span>
                )}
              </motion.div>

              {latestData && (
                <div
                  style={{
                    marginTop: '16px',
                    padding: '12px 16px',
                    background: '#10b98115',
                    borderRadius: '8px',
                    borderLeft: `3px solid #10b981`,
                  }}
                >
                  <div className="summary-header">Latest Reading</div>
                  <div style={{ color: '#10b981', fontSize: '0.875rem' }}>
                    {latestData}
                  </div>
                </div>
              )}
            </motion.div>

            {/* Chart Container */}
            <motion.div
              style={{
                flex: 1,
                background: 'rgba(23, 26, 33, 0.5)',
                borderRadius: '16px',
                padding: '24px',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '20px',
                }}
              >
                <div
                  style={{
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    color: '#a3aab5',
                  }}
                >
                  Time Series Analysis
                </div>
                <motion.div
                  style={{
                    display: 'flex',
                    gap: '8px',
                  }}
                >
                  <span
                    style={{
                      padding: '4px 8px',
                      background: '#10b98120',
                      color: '#10b981',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                    }}
                  >
                    Live
                  </span>
                  <span
                    style={{
                      padding: '4px 8px',
                      background: '#f59e0b20',
                      color: '#f59e0b',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                    }}
                  >
                    30d
                  </span>
                </motion.div>
              </div>

              {/* Lazy loaded chart */}
              {hasLoadedChart ? (
                <motion.div
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.4 }}
                >
                  <ChartPlaceholder />
                </motion.div>
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <ChartLoader />
                </motion.div>
              )}
            </motion.div>

            {/* Sparkline Preview (Bottom) */}
            <motion.div
              style={{
                width: '100%',
                marginTop: '24px',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  marginBottom: '8px',
                }}
              >
                <div className="summary-header">Overview</div>
                <Sparkline data={sparklineData} />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sparkline Preview (Always Visible) */}
      {!isExpanded && (
        <div
          style={{
            padding: '16px 32px',
            borderBottom: '1px solid rgba(42, 48, 64, 0.3)',
          }}
        >
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Sparkline data={sparklineData} />
          </motion.div>
        </div>
      )}
    </motion.div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Metric Card List - Scroll container with snap points
// ─────────────────────────────────────────────────────────────────────────────

export const MetricCardList = ({ children }) => (
  <div
    style={{
      padding: '40px 32px',
      scrollSnapType: 'y proximity',
      overflowY: 'auto',
    }}
  >
    <div
      style={{
        maxWidth: 1200,
        margin: '0 auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '32px',
      }}
    >
      {children}
    </div>
  </div>
);

export default ExpandableMetricCard;
