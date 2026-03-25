import { motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import { TrendDelta } from '../../types';

function getDeltaColor(delta: TrendDelta): string {
  const isGood =
    (delta.direction === 'up' && delta.label === 'Health') ||
    (delta.direction === 'down' && delta.label !== 'Health');
  return isGood ? '#00E5A0' : '#FF4D6A';
}

export default function TrendDeltas() {
  const data = useAppStore((s) => s.siteSummaryData);
  if (!data) return null;

  return (
    <div style={{ marginBottom: '2rem' }}>
      <div
        style={{
          fontSize: '12px',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: '#8A95A5',
          marginBottom: '12px',
        }}
      >
        This week vs last week
      </div>

      <div className="flex flex-wrap gap-3 mb-8">
        {data.trendDeltas.map((delta, i) => {
          const color = getDeltaColor(delta);
          const arrow = delta.value > 0 ? '↑' : '↓';

          return (
            <motion.div
              key={delta.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.38, delay: i * 0.06, ease: [0.22, 1, 0.36, 1] }}
              style={{
                flex: '1 1 120px',
                minWidth: '120px',
                background: '#111820',
                border: '1px solid #1E2A3A',
                borderRadius: '10px',
                padding: '12px 16px',
              }}
            >
              <div style={{ fontSize: '11px', color: '#8A95A5', marginBottom: '6px' }}>
                {delta.label}
              </div>
              <div
                style={{
                  fontSize: '20px',
                  fontWeight: 700,
                  fontFamily: 'var(--font-display)',
                  color,
                }}
              >
                {arrow} {Math.abs(delta.value)}{delta.unit}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
