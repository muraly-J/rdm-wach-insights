import React, { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import { Toast, ToastVariant } from '../../hooks/useToast';

const VARIANT_STYLES: Record<ToastVariant, { border: string; icon: string; color: string }> = {
  success: { border: '#00E5A0', icon: '✓', color: '#00E5A0' },
  error: { border: '#ef4444', icon: '✕', color: '#ef4444' },
  warning: { border: '#f59e0b', icon: '⚠', color: '#f59e0b' },
  info: { border: '#60a5fa', icon: 'ℹ', color: '#60a5fa' },
};

const ToastItem: React.FC<{ toast: Toast }> = ({ toast }) => {
  const removeToast = useAppStore((s) => s.removeToast);
  const { border, icon, color } = VARIANT_STYLES[toast.variant];
  const duration = toast.duration ?? 4000;

  useEffect(() => {
    const timer = setTimeout(() => removeToast(toast.id), duration);
    return () => clearTimeout(timer);
  }, [toast.id, duration, removeToast]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 40, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 40, scale: 0.9 }}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 10,
        background: '#1c2431',
        border: `1px solid ${border}44`,
        borderLeft: `3px solid ${border}`,
        borderRadius: 8,
        padding: '10px 14px',
        minWidth: 240,
        maxWidth: 340,
        boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
        cursor: 'pointer',
      }}
      onClick={() => removeToast(toast.id)}
    >
      <span style={{ color, fontSize: 13, fontWeight: 700, flexShrink: 0, marginTop: 1 }}>
        {icon}
      </span>
      <span style={{ fontSize: 12, color: '#E8ECF1', lineHeight: 1.5 }}>{toast.message}</span>
    </motion.div>
  );
};

const ToastContainer: React.FC = () => {
  const toasts = useAppStore((s) => s.toasts);

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 200,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        alignItems: 'center',
        pointerEvents: 'none',
      }}
    >
      <AnimatePresence mode="sync">
        {toasts.map((t) => (
          <div key={t.id} style={{ pointerEvents: 'auto' }}>
            <ToastItem toast={t} />
          </div>
        ))}
      </AnimatePresence>
    </div>
  );
};

export default ToastContainer;
