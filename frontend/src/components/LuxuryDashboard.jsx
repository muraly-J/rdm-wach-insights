import { useState, useEffect } from 'react';
import api from '../api.js';
import { motion } from 'framer-motion';
import FloatingChatButton from './FloatingChatButton.jsx';
import { MAPPED_COUNT } from '../deviceMap.js';

// ─────────────────────────────────────────────────────────────────────────────
// HealthGauge Component
// ─────────────────────────────────────────────────────────────────────────────

const HealthGauge = ({ value = 85, size = 320 }) => {
  const radius = size * 0.375;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(Math.max(value, 0), 100);

  const dashOffset = circumference - (progress / 100) * circumference;

  const getColor = () => {
    if (value >= 80) return '#10b981';
    if (value >= 60) return '#f59e0b';
    if (value >= 40) return '#f97316';
    return '#ef4444';
  };

  const color = getColor();

  return (
    <div
      style={{
        position: 'relative',
        width: size,
        height: size,
        margin: '0 auto',
      }}
    >
      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${size} ${size}`}
        style={{ transform: 'rotate(-90deg)' }}
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#2A3040"
          strokeWidth={size * 0.05}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={size * 0.05}
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={dashOffset}
        />
      </svg>

      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div
          style={{
            fontSize: 'clamp(4rem, 10vw, 6rem)',
            fontWeight: 800,
            color: color,
          }}
        >
          {Math.round(value)}
        </div>
        <div
          style={{
            fontSize: 'clamp(1rem, 2vw, 1.5rem)',
            color: '#a3aab5',
            marginTop: '8px',
          }}
        >
          {value >= 80 ? 'Healthy' : value >= 60 ? 'Monitor' : value >= 40 ? 'Maintenance Soon' : 'Critical'}
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// BentoCards Component
// ─────────────────────────────────────────────────────────────────────────────

const BentoCards = ({
  healthIndex,
  tier,
  summaryText,
  latestInsight,
}) => {
  const getTierColor = () => {
    switch (tier) {
      case 'Healthy':
        return '#10b981';
      case 'Monitor':
        return '#f59e0b';
      case 'Maintenance Soon':
        return '#f97316';
      default:
        return '#ef4444';
    }
  };

  const tierColor = getTierColor();

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
        gap: '32px',
      }}
    >
      <div
        style={{
          background: 'rgba(31, 35, 46, 0.7)',
          backdropFilter: 'blur(12px)',
          border: '1px solid rgba(42, 48, 64, 0.3)',
          borderLeft: `3px solid ${tierColor}`,
          borderRadius: '20px',
          padding: '28px',
        }}
      >
        <div
          style={{
            fontSize: '0.75rem',
            textTransform: 'uppercase',
            letterSpacing: '0.15em',
            color: '#a3aab5',
            marginBottom: '16px',
          }}
        >
          Health Summary
        </div>
        <div
          style={{
            fontSize: '1.25rem',
            color: '#eaf0fb',
            lineHeight: '1.7',
          }}
        >
          {summaryText || 'System operating within normal parameters.'}
        </div>
        <div
          style={{
            marginTop: '12px',
            fontSize: '0.875rem',
            color: '#6b7280',
          }}
        >
          {latestInsight || 'Data updated within the last hour.'}
        </div>
      </div>

      <div
        style={{
          background: 'rgba(31, 35, 46, 0.7)',
          backdropFilter: 'blur(12px)',
          border: '1px solid rgba(42, 48, 64, 0.3)',
          borderRight: '3px solid var(--gold)',
          borderRadius: '20px',
          padding: '28px',
        }}
      >
        <div
          style={{
            fontSize: '0.75rem',
            textTransform: 'uppercase',
            letterSpacing: '0.15em',
            color: '#a3aab5',
            marginBottom: '16px',
          }}
        >
          Latest Insight
        </div>
        <div
          style={{
            fontSize: '1.25rem',
            color: '#eaf0fb',
          }}
        >
          {latestInsight || 'Waiting for new data points...'}
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// ExpandableMetricCard Component
// ─────────────────────────────────────────────────────────────────────────────

const ExpandableMetricCard = ({
  title,
  metricKey,
  value,
  summaryText,
  latestData,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

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
        return { primary: '#10b981', secondary: '#059669' };
    }
  };

  const colors = getColors();

  return (
    <motion.div
      style={{
        background: 'rgba(23, 26, 33, 0.8)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(42, 48, 64, 0.3)',
        borderRadius: '24px',
        overflow: 'hidden',
      }}
    >
      <motion.div
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '24px 32px',
          cursor: 'pointer',
        }}
        whileHover={{ background: 'rgba(16, 185, 129, 0.05)' }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
          }}
        >
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              background: `linear-gradient(135deg, ${colors.primary}40, ${colors.secondary}20)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke={colors.primary}
              strokeWidth="2"
            >
              <path d="M3 3v18h18" strokeLinecap="round" />
              <path d="M18 9l-5 5-7-7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <h3
              style={{
                fontSize: '1.5rem',
                fontWeight: 700,
                color: '#eaf0fb',
              }}
            >
              {title}
            </h3>
            <div
              style={{
                fontSize: '0.875rem',
                color: '#a3aab5',
              }}
            >
              Current: {value}
            </div>
          </div>
        </div>

        <motion.div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 16px',
            background: `${colors.primary}20`,
            border: `1px solid ${colors.primary}40`,
            borderRadius: '8px',
            color: colors.primary,
            fontWeight: 600,
          }}
          whileHover={{ scale: 1.05, background: `${colors.primary}30` }}
          whileTap={{ scale: 0.95 }}
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
          {isExpanded ? 'Collapse' : 'Expand Analysis'}
        </motion.div>
      </motion.div>

      {isExpanded && (
        <motion.div
          style={{
            padding: '24px 32px',
            borderBottom: '1px solid rgba(42, 48, 64, 0.3)',
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '280px minmax(0, 1fr) 300px',
              gap: '24px',
            }}
          >
            <div>
              <div
                style={{
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: '#a3aab5',
                  marginBottom: '8px',
                }}
              >
                AI Analysis
              </div>
              <div
                style={{
                  fontSize: '0.9375rem',
                  color: '#eaf0fb',
                  lineHeight: '1.7',
                }}
              >
                {summaryText}
              </div>
              <div
                style={{
                  marginTop: '16px',
                  padding: '12px 16px',
                  background: '#10b98115',
                  borderLeft: '3px solid #10b981',
                  borderRadius: '8px',
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
                  Latest Reading
                </div>
                <div style={{ fontSize: '0.875rem', color: '#10b981' }}>
                  {latestData}
                </div>
              </div>
            </div>

            <div
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
                <div style={{ display: 'flex', gap: '8px' }}>
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
                </div>
              </div>

              <div
                style={{
                  height: '250px',
                  position: 'relative',
                  background: `linear-gradient(180deg, ${colors.primary}20 0%, transparent 100%)`,
                  borderRadius: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <div style={{ padding: '30px', textAlign: 'center' }}>
                  <div
                    style={{
                      fontSize: '4rem',
                      marginBottom: '16px',
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
                  <p style={{ color: '#a3aab5' }}>
                    Interactive chart with time-series data
                  </p>
                </div>
              </div>
            </div>

            <div
              style={{
                background: 'rgba(23, 26, 33, 0.5)',
                borderRadius: '16px',
                padding: '24px',
              }}
            >
              <div
                style={{
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: '#a3aab5',
                  marginBottom: '16px',
                }}
              >
                Key Metrics
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {[
                  { label: 'Current', value: value },
                  { label: 'Baseline', value: (parseFloat(value) * 0.75).toFixed(2) },
                  { label: 'Peak', value: (parseFloat(value) * 1.3).toFixed(2) },
                  { label: 'Average', value: (parseFloat(value) * 0.9).toFixed(2) },
                ].map((item, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '10px 16px',
                      background: 'rgba(255, 255, 255, 0.03)',
                      borderRadius: '8px',
                    }}
                  >
                    <span style={{ color: '#a3aab5', fontSize: '0.875rem' }}>
                      {item.label}
                    </span>
                    <span style={{ color: '#eaf0fb', fontWeight: 600 }}>
                      {item.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// ExpandableMetricList Component
// ─────────────────────────────────────────────────────────────────────────────

const ExpandableMetricList = () => {
  const metrics = [
    {
      key: 'energy_anomaly',
      title: 'Energy Anomaly',
      value: '0.45',
      summary: 'Energy consumption is 15% above baseline over the last 24 hours. Peak demand occurred at 10:30 AM.',
      latest: 'Peak: 45.2 kW at 10:30 AM',
    },
    {
      key: 'pf_degradation',
      title: 'PF Degradation',
      value: '0.23',
      summary: 'Power factor has decreased by 0.08 compared to last week. Two devices showing significant PF drop.',
      latest: 'Lowest PF: 0.68 on e0105',
    },
    {
      key: 'phase_imbalance',
      title: 'Phase Imbalance',
      value: '0.18',
      summary: 'Three-phase balance is stable, but some AHUs show slightly uneven load distribution.',
      latest: 'Maximum imbalance: 4.2% on e0109',
    },
    {
      key: 'thd_drift',
      title: 'THD Drift',
      value: '0.32',
      summary: 'Total Harmonic Distortion has increased slightly. Consider checking VFD settings.',
      latest: 'Highest THD: 12.4% on e0203',
    },
    {
      key: 'overload',
      title: 'Overload',
      value: '0.28',
      summary: 'No critical overloads detected, but two AHUs are approaching 90% capacity.',
      latest: 'Peak load: 92% on e0112',
    },
  ];

  return (
    <div
      style={{
        scrollSnapType: 'y proximity',
        overflowY: 'auto',
        maxHeight: 'calc(100vh - 800px)',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
        {metrics.map((metric, index) => (
          <ExpandableMetricCard
            key={metric.key}
            title={`0${index + 1} ${metric.title}`}
            metricKey={metric.key}
            value={metric.value}
            summaryText={metric.summary}
            latestData={metric.latest}
          />
        ))}
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// LuxuryDashboard Component
// Main dashboard with Golden Thread transition from Landing
// ─────────────────────────────────────────────────────────────────────────────

const LuxuryDashboard = ({ onBack }) => {
  const [selectedLevel, setSelectedLevel] = useState('1');
  const [timeRange, setTimeRange] = useState('24h');
  const [healthIndex, setHealthIndex] = useState(85);
  const [tier, setTier] = useState('Healthy');
  const [summaryText, setSummaryText] = useState('');
  const [latestInsight, setLatestInsight] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        const rankingRes = await api.get('/dashboard/ranking', {
          params: { level: selectedLevel, time_range: 'last_24h' },
        });

        const trendRes = await api.get('/dashboard/trend', {
          params: { level: selectedLevel, range: timeRange },
        });

        if (trendRes.data && trendRes.data.series) {
          const latest = trendRes.data.series[trendRes.data.series.length - 1];
          if (latest) {
            const ahuValues = Object.values(latest).filter(
              (v) => typeof v === 'number' && !isNaN(v)
            );
            if (ahuValues.length > 0) {
              const avg = ahuValues.reduce((a, b) => a + b, 0) / ahuValues.length;
              setHealthIndex(Math.round(avg));
            }
          }
        }

        try {
          const summaryRes = await api.get('/dashboard/summary', {
            params: { level: selectedLevel, range: timeRange },
          });
          if (summaryRes.data && summaryRes.data.summaries) {
            const healthSummary = summaryRes.data.summaries.health_index;
            if (healthSummary) {
              setSummaryText(healthSummary);
            }
          }
        } catch (err) {
          console.log('No summary available');
        }

        if (trendRes.data && trendRes.data.series) {
          const series = trendRes.data.series;
          if (series.length > 0) {
            const lastPoint = series[series.length - 1];
            if (lastPoint && lastPoint.health_index) {
              setLatestInsight(`Current Health Index: ${Math.round(lastPoint.health_index)}`);
            }
          }
        }
      } catch (err) {
        console.error('Error loading dashboard:', err);
      }
    };

    loadData();
  }, [selectedLevel, timeRange]);

  useEffect(() => {
    if (healthIndex >= 80) setTier('Healthy');
    else if (healthIndex >= 60) setTier('Monitor');
    else if (healthIndex >= 40) setTier('Maintenance Soon');
    else setTier('Critical');
  }, [healthIndex]);

  const getTierColor = () => {
    switch (tier) {
      case 'Healthy':
        return '#10b981';
      case 'Monitor':
        return '#f59e0b';
      case 'Maintenance Soon':
        return '#f97316';
      default:
        return '#ef4444';
    }
  };

  const tierColor = getTierColor();

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-logo">
          <div className="header-logo-mark">
            <svg viewBox="0 0 16 16" fill="none">
              <path
                d="M2 8h3l2-5 2 10 2-5h3"
                stroke="#0a0e1a"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div>
            <div className="header-title">WACH Insight</div>
            <div className="header-subtitle">
              Women &amp; Child Ward · Hospital KL · AHU Analytics
            </div>
          </div>
        </div>

        <div className="header-right">
          <button
            onClick={onBack}
            style={{
              cursor: 'pointer',
              padding: '8px 16px',
              background: '#2A3040',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              borderRadius: '8px',
              color: '#10b981',
            }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M19 12H5" strokeLinecap="round" />
              <path d="m12 19-7-7 7-7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span style={{ marginLeft: '8px' }}>Back to Chat</span>
          </button>

          <div
            className="unmapped-badge"
            title={`${MAPPED_COUNT} of ~150 device IDs have confirmed location records.`}
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            Some devices unidentified
          </div>
        </div>
      </header>

      {/* Dashboard Content */}
      <main
        style={{
          padding: '40px 32px',
          overflowX: 'hidden',
        }}
      >
        {/* Dynamic Background Gradient based on health */}
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            zIndex: -1,
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: '-20%',
              left: '-10%',
              width: '120%',
              height: '120%',
              background: `radial-gradient(circle at top left, ${tierColor}15, transparent 40%)`,
            }}
          />
        </div>

        {/* Header Section */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '40px',
          }}
        >
          <div>
            <h1
              style={{
                fontSize: 'clamp(2.5rem, 5vw, 3.5rem)',
                fontWeight: 800,
                color: '#eaf0fb',
                margin: '0 0 8px',
              }}
            >
              Dashboard Overview
            </h1>
            <div
              style={{
                fontSize: '1rem',
                color: '#a3aab5',
              }}
            >
              Level {selectedLevel} · {timeRange.toUpperCase()}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <div
              style={{
                padding: '10px 20px',
                background: '#2A3040',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
              }}
            >
              <div
                style={{
                  fontSize: '0.75rem',
                  color: '#6b7280',
                  marginBottom: '4px',
                }}
              >
                Tier
              </div>
              <div
                style={{
                  fontSize: '1rem',
                  fontWeight: 700,
                  color: tierColor,
                }}
              >
                {tier}
              </div>
            </div>
          </div>
        </div>

        {/* Health Index Section */}
        <section style={{ marginBottom: '48px' }}>
          <div
            style={{
              textAlign: 'center',
              marginBottom: '40px',
            }}
          >
            <h2
              style={{
                fontSize: '1rem',
                textTransform: 'uppercase',
                letterSpacing: '0.2em',
                color: '#a3aab5',
                marginBottom: '24px',
              }}
            >
              Health Index
            </h2>
          </div>

          <HealthGauge value={healthIndex} size={320} />
        </section>

        {/* Bento Cards Section */}
        <section style={{ marginBottom: '48px' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '24px',
            }}
          >
            <h2
              style={{
                fontSize: '1.1rem',
                textTransform: 'uppercase',
                letterSpacing: '0.2em',
                color: '#a3aab5',
              }}
            >
              Strategic Overview
            </h2>
          </div>

          <BentoCards
            healthIndex={healthIndex}
            tier={tier}
            summaryText={
              summaryText ||
              `Level ${selectedLevel} AHUs are operating with ${healthIndex}% overall health index. System status is currently ${tier.toLowerCase()}`
            }
            latestInsight={
              latestInsight ||
              `Last update: ${new Date().toLocaleTimeString()}`
            }
          />
        </section>

        {/* Metrics Cards Section */}
        <section style={{ marginBottom: '48px' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '24px',
            }}
          >
            <h2
              style={{
                fontSize: '1.1rem',
                textTransform: 'uppercase',
                letterSpacing: '0.2em',
                color: '#a3aab5',
              }}
            >
              Detailed Metrics
            </h2>
          </div>

          <ExpandableMetricList />
        </section>
      </main>

      {/* Floating Chat Button */}
      <FloatingChatButton isOpen={false} onToggle={() => {}} />
    </div>
  );
};

export default LuxuryDashboard;
