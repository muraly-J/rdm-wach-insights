import { motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';

const ease = [0.22, 1, 0.36, 1] as const;

interface ChipConfig {
  label: string;
  value: string;
  color: string;
  borderColor: string;
}

export default function KPIStrip() {
  const data = useAppStore((s) => s.siteSummaryData);
  if (!data) return null;

  const chips: ChipConfig[] = [
    {
      label: 'Total AHUs',
      value: String(data.totalAHUs),
      color: '#E8ECF1',
      borderColor: 'rgba(255,255,255,0.08)',
    },
    {
      label: 'Avg Site Health',
      value: `${data.avgSiteHealth}`,
      color: '#00E5A0',
      borderColor: 'rgba(255,255,255,0.08)',
    },
    {
      label: 'AHUs in Alert',
      value: String(data.ahusInAlert),
      color: '#FF4D6A',
      borderColor: 'rgba(255,77,106,0.3)',
    },
    {
      label: 'Est. Monthly Cost',
      value: `RM ${data.estMonthlyCostMYR.toLocaleString()}`,
      color: '#E8ECF1',
      borderColor: 'rgba(255,255,255,0.08)',
    },
  ];

  return (
    <div className="flex flex-wrap gap-3 mb-8">
      {chips.map((chip, i) => (
        <motion.div
          key={chip.label}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: i * 0.07, ease }}
          style={{
            background: 'rgba(255,255,255,0.04)',
            backdropFilter: 'blur(16px) saturate(160%)',
            WebkitBackdropFilter: 'blur(16px) saturate(160%)',
            border: `1px solid ${chip.borderColor}`,
            borderRadius: '12px',
            padding: '14px 20px',
            flex: '1 1 160px',
            minWidth: '160px',
            boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06)',
          }}
        >
          <div
            style={{
              fontSize: '10px',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: '#8A95A5',
              marginBottom: '6px',
            }}
          >
            {chip.label}
          </div>
          <div
            style={{
              fontSize: '28px',
              fontWeight: 700,
              fontFamily: 'var(--font-display)',
              color: chip.color,
              lineHeight: 1.1,
            }}
          >
            {chip.value}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
