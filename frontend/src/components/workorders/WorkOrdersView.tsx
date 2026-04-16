import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchWorkOrders } from '../../api/client';
import { WorkOrder } from '../../types/chat';
import { useAppStore } from '../../store/useAppStore';
import { usePolling } from '../../hooks/usePolling';
import WorkOrderStatsBar from './WorkOrderStatsBar';
import WorkOrderFilters, { WorkOrderFilterState } from './WorkOrderFilters';
import WorkOrderTable from './WorkOrderTable';
import WorkOrderDetailModal from './WorkOrderDetailModal';

const WorkOrdersView: React.FC = () => {
  const setWorkOrderDraftsCount = useAppStore((s) => s.setWorkOrderDraftsCount);

  const [orders, setOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<WorkOrder | null>(null);
  const [filters, setFilters] = useState<WorkOrderFilterState>({
    status: 'all',
    severity: 'all',
    search: '',
  });

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
    load();
  }, [load]);

  // Poll every 60 s, pausing when tab hidden
  usePolling(load, { interval: 60_000, runOnMount: false });

  const filteredOrders = useMemo(() => {
    return orders.filter((o) => {
      if (filters.status !== 'all' && o.status !== filters.status) return false;
      if (filters.severity !== 'all' && o.severity?.toLowerCase() !== filters.severity) return false;
      if (filters.search) {
        const q = filters.search.toLowerCase();
        if (
          !o.title.toLowerCase().includes(q) &&
          !(o.description ?? '').toLowerCase().includes(q) &&
          !o.ahu_id.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [orders, filters]);

  return (
    <div style={{ paddingTop: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#E8ECF1' }}>Work Orders</h2>
        <button
          onClick={load}
          disabled={loading}
          style={{
            background: 'transparent',
            border: '1px solid #2a3649',
            borderRadius: 6,
            padding: '6px 12px',
            color: '#8899aa',
            fontSize: 12,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.6 : 1,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div style={{ marginBottom: 16, padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: '1px solid #ef4444', borderRadius: 8, color: '#ef4444', fontSize: 12 }}>
          {error}
        </div>
      )}

      <WorkOrderStatsBar orders={orders} />

      <div style={{ background: '#111827', border: '1px solid #2a3649', borderRadius: 12, padding: '16px 16px' }}>
        <WorkOrderFilters filters={filters} onChange={setFilters} />
        <WorkOrderTable
          orders={filteredOrders}
          onRefresh={load}
          onSelectOrder={setSelectedOrder}
        />
      </div>

      <WorkOrderDetailModal
        order={selectedOrder}
        onClose={() => setSelectedOrder(null)}
        onUpdated={() => { setSelectedOrder(null); load(); }}
      />
    </div>
  );
};

export default WorkOrdersView;
