import React, { useCallback, useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import { fetchWorkOrders } from '../../api/client';
import { WorkOrder } from '../../types/chat';
import WorkOrderPanelItem from './WorkOrderPanelItem';

const WorkOrderPanel: React.FC = () => {
  const { workOrderPanelOpen, setWorkOrderPanelOpen, setWorkOrderDraftsCount } = useAppStore();
  const [orders, setOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWorkOrders();
      setOrders(res.work_orders);
      setWorkOrderDraftsCount(res.work_orders.filter((o) => o.status === 'draft').length);
    } catch {
      setError('Failed to load work orders');
    } finally {
      setLoading(false);
    }
  }, [setWorkOrderDraftsCount]);

  useEffect(() => {
    if (workOrderPanelOpen) load();
  }, [workOrderPanelOpen, load]);

  const drafts = orders.filter((o) => o.status === 'draft');
  const others = orders.filter((o) => o.status !== 'draft');

  return (
    <AnimatePresence>
      {workOrderPanelOpen && (
        <motion.div
          key="wo-panel"
          initial={{ x: '100%', opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: '100%', opacity: 0 }}
          transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          style={{
            position: 'fixed',
            top: 0,
            right: 0,
            width: 340,
            height: '100vh',
            background: '#111827',
            borderLeft: '1px solid #2a3649',
            zIndex: 80,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '16px 16px',
              borderBottom: '1px solid #2a3649',
              flexShrink: 0,
            }}
          >
            <span style={{ fontWeight: 700, fontSize: 14, color: '#E8ECF1' }}>Work Orders</span>
            <button
              onClick={() => setWorkOrderPanelOpen(false)}
              style={{
                background: 'none',
                border: 'none',
                color: '#8899aa',
                cursor: 'pointer',
                padding: 4,
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          {/* Body */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 12px' }}>
            {loading && (
              <div style={{ color: '#556677', fontSize: 12, textAlign: 'center', paddingTop: 24 }}>
                Loading…
              </div>
            )}
            {error && !loading && (
              <div style={{ color: '#ef4444', fontSize: 12, paddingTop: 12 }}>{error}</div>
            )}
            {!loading && !error && orders.length === 0 && (
              <div style={{ color: '#556677', fontSize: 12, textAlign: 'center', paddingTop: 24 }}>
                No work orders yet.
              </div>
            )}

            {drafts.length > 0 && (
              <>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#f59e0b', letterSpacing: '0.07em', marginBottom: 8, textTransform: 'uppercase' }}>
                  Drafts · {drafts.length}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
                  {drafts.map((o) => (
                    <WorkOrderPanelItem key={o.id} order={o} onUpdated={load} />
                  ))}
                </div>
              </>
            )}

            {others.length > 0 && (
              <>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#556677', letterSpacing: '0.07em', marginBottom: 8, textTransform: 'uppercase' }}>
                  Recent · {others.length}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {others.map((o) => (
                    <WorkOrderPanelItem key={o.id} order={o} onUpdated={load} />
                  ))}
                </div>
              </>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default WorkOrderPanel;
