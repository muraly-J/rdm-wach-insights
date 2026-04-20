import React, { useState } from 'react';
import { WorkOrder, HEALTH_TIER_COLORS } from '../../types/chat';
import { approveWorkOrder, dismissWorkOrder } from '../../api/client';
import { useToast } from '../../hooks/useToast';

interface WorkOrderPanelItemProps {
  order: WorkOrder;
  onUpdated: () => void;
}

const WorkOrderPanelItem: React.FC<WorkOrderPanelItemProps> = ({ order, onUpdated }) => {
  const [loading, setLoading] = useState<'approve' | 'dismiss' | null>(null);
  const { showToast } = useToast();

  const severityColor = HEALTH_TIER_COLORS[order.severity as keyof typeof HEALTH_TIER_COLORS] ?? '#8899aa';

  const handleApprove = async () => {
    setLoading('approve');
    try {
      await approveWorkOrder(order.id);
      showToast(`Work order #${order.id} approved`, 'success');
      onUpdated();
    } catch {
      showToast('Failed to approve work order', 'error');
    } finally {
      setLoading(null);
    }
  };

  const handleDismiss = async () => {
    setLoading('dismiss');
    try {
      await dismissWorkOrder(order.id);
      showToast(`Work order #${order.id} dismissed`, 'info');
      onUpdated();
    } catch {
      showToast('Failed to dismiss work order', 'error');
    } finally {
      setLoading(null);
    }
  };

  return (
    <div
      style={{
        background: '#0f1720',
        border: '1px solid #2a3649',
        borderRadius: 8,
        padding: '10px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            color: severityColor,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          {order.severity}
        </span>
        <span style={{ fontSize: 10, color: '#556677' }}>#{order.id}</span>
      </div>

      <p style={{ margin: 0, fontSize: 12, fontWeight: 600, color: '#E8ECF1', lineHeight: 1.4 }}>
        {order.title}
      </p>

      {order.description && (
        <p
          style={{
            margin: 0,
            fontSize: 11,
            color: '#8899aa',
            lineHeight: 1.4,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {order.description}
        </p>
      )}

      <div style={{ fontSize: 10, color: '#556677' }}>
        AHU {order.ahu_id} · Level {order.level}
      </div>

      {order.status === 'draft' && (
        <div style={{ display: 'flex', gap: 6, marginTop: 2 }}>
          <button
            onClick={handleApprove}
            disabled={loading !== null}
            style={{
              flex: 1,
              background: loading === 'approve' ? '#00b37e' : '#00E5A0',
              color: '#000',
              border: 'none',
              borderRadius: 6,
              padding: '5px 0',
              fontSize: 11,
              fontWeight: 700,
              cursor: loading !== null ? 'not-allowed' : 'pointer',
              opacity: loading !== null ? 0.7 : 1,
              transition: 'opacity 0.15s',
            }}
          >
            {loading === 'approve' ? '…' : 'Approve'}
          </button>
          <button
            onClick={handleDismiss}
            disabled={loading !== null}
            style={{
              flex: 1,
              background: 'transparent',
              color: '#8899aa',
              border: '1px solid #2a3649',
              borderRadius: 6,
              padding: '5px 0',
              fontSize: 11,
              fontWeight: 600,
              cursor: loading !== null ? 'not-allowed' : 'pointer',
              opacity: loading !== null ? 0.7 : 1,
              transition: 'opacity 0.15s',
            }}
          >
            {loading === 'dismiss' ? '…' : 'Dismiss'}
          </button>
        </div>
      )}

      {order.status !== 'draft' && (
        <div
          style={{
            fontSize: 10,
            color: order.status === 'approved' ? '#00E5A0' : '#556677',
            fontWeight: 600,
            textTransform: 'uppercase',
          }}
        >
          {order.status}
        </div>
      )}
    </div>
  );
};

export default WorkOrderPanelItem;
