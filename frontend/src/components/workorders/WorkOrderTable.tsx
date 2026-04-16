import React from 'react';
import { WorkOrder } from '../../types/chat';
import { approveWorkOrder, dismissWorkOrder } from '../../api/client';

interface WorkOrderTableProps {
  orders: WorkOrder[];
  onRefresh: () => void;
  onSelectOrder: (order: WorkOrder) => void;
}

const SEVERITY_COLOR: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#f59e0b',
  low: '#22c55e',
};

const STATUS_COLOR: Record<string, string> = {
  draft: '#f59e0b',
  approved: '#00E5A0',
  dismissed: '#556677',
};

const WorkOrderTable: React.FC<WorkOrderTableProps> = ({ orders, onRefresh, onSelectOrder }) => {
  const [loadingId, setLoadingId] = React.useState<number | null>(null);

  const handleApprove = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    setLoadingId(id);
    try {
      await approveWorkOrder(id);
      onRefresh();
    } finally {
      setLoadingId(null);
    }
  };

  const handleDismiss = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    setLoadingId(id);
    try {
      await dismissWorkOrder(id);
      onRefresh();
    } finally {
      setLoadingId(null);
    }
  };

  if (orders.length === 0) {
    return (
      <div style={{ color: '#556677', fontSize: 13, textAlign: 'center', padding: '40px 0' }}>
        No work orders match the current filters.
      </div>
    );
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #2a3649' }}>
            {['#', 'Title', 'AHU', 'Level', 'Severity', 'Status', 'Created', 'Actions'].map((h) => (
              <th
                key={h}
                style={{
                  padding: '8px 10px',
                  textAlign: 'left',
                  color: '#556677',
                  fontWeight: 600,
                  fontSize: 10,
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  whiteSpace: 'nowrap',
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => {
            const severityColor = SEVERITY_COLOR[order.severity?.toLowerCase()] ?? '#8899aa';
            const statusColor = STATUS_COLOR[order.status] ?? '#8899aa';
            const createdDate = new Date(order.created_at).toLocaleDateString();

            return (
              <tr
                key={order.id}
                onClick={() => onSelectOrder(order)}
                style={{
                  borderBottom: '1px solid #1a2234',
                  cursor: 'pointer',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = '#1a2234')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={{ padding: '10px 10px', color: '#556677', fontWeight: 600 }}>
                  #{order.id}
                </td>
                <td style={{ padding: '10px 10px', color: '#E8ECF1', maxWidth: 260 }}>
                  <span
                    style={{
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}
                  >
                    {order.title}
                  </span>
                </td>
                <td style={{ padding: '10px 10px', color: '#8899aa', whiteSpace: 'nowrap' }}>
                  {order.ahu_id}
                </td>
                <td style={{ padding: '10px 10px', color: '#8899aa', whiteSpace: 'nowrap' }}>
                  L{order.level}
                </td>
                <td style={{ padding: '10px 10px', whiteSpace: 'nowrap' }}>
                  <span
                    style={{
                      color: severityColor,
                      fontWeight: 700,
                      fontSize: 10,
                      textTransform: 'uppercase',
                    }}
                  >
                    {order.severity}
                  </span>
                </td>
                <td style={{ padding: '10px 10px', whiteSpace: 'nowrap' }}>
                  <span
                    style={{
                      color: statusColor,
                      fontWeight: 600,
                      fontSize: 10,
                      textTransform: 'uppercase',
                    }}
                  >
                    {order.status}
                  </span>
                </td>
                <td style={{ padding: '10px 10px', color: '#556677', whiteSpace: 'nowrap' }}>
                  {createdDate}
                </td>
                <td style={{ padding: '10px 10px', whiteSpace: 'nowrap' }}>
                  {order.status === 'draft' && (
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button
                        onClick={(e) => handleApprove(e, order.id)}
                        disabled={loadingId === order.id}
                        style={{
                          background: '#00E5A0',
                          color: '#000',
                          border: 'none',
                          borderRadius: 4,
                          padding: '4px 10px',
                          fontSize: 10,
                          fontWeight: 700,
                          cursor: loadingId === order.id ? 'not-allowed' : 'pointer',
                          opacity: loadingId === order.id ? 0.6 : 1,
                        }}
                      >
                        Approve
                      </button>
                      <button
                        onClick={(e) => handleDismiss(e, order.id)}
                        disabled={loadingId === order.id}
                        style={{
                          background: 'transparent',
                          color: '#8899aa',
                          border: '1px solid #2a3649',
                          borderRadius: 4,
                          padding: '4px 10px',
                          fontSize: 10,
                          fontWeight: 600,
                          cursor: loadingId === order.id ? 'not-allowed' : 'pointer',
                          opacity: loadingId === order.id ? 0.6 : 1,
                        }}
                      >
                        Dismiss
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default WorkOrderTable;
