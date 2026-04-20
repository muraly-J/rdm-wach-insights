import React from 'react';
import { WorkOrder, HEALTH_TIER_COLORS } from '../../types/chat';
import { approveWorkOrder, dismissWorkOrder, deleteWorkOrder } from '../../api/client';
import { useToast } from '../../hooks/useToast';

interface WorkOrderTableProps {
  orders: WorkOrder[];
  onRefresh: () => void;
  onSelectOrder: (order: WorkOrder) => void;
}

const STATUS_COLOR: Record<string, string> = {
  draft: '#f59e0b',
  approved: '#00E5A0',
  dismissed: '#556677',
};

const WorkOrderTable: React.FC<WorkOrderTableProps> = ({ orders, onRefresh, onSelectOrder }) => {
  const [loadingId, setLoadingId] = React.useState<number | null>(null);
  const [selectedIds, setSelectedIds] = React.useState<Set<number>>(new Set());
  const [bulkDeleting, setBulkDeleting] = React.useState(false);
  const { showToast } = useToast();

  const allSelected = orders.length > 0 && selectedIds.size === orders.length;
  const someSelected = selectedIds.size > 0 && !allSelected;

  const toggleAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(orders.map((o) => o.id)));
    }
  };

  const toggleRow = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleApprove = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    setLoadingId(id);
    try {
      await approveWorkOrder(id);
      showToast(`Work order #${id} approved`, 'success');
      onRefresh();
    } catch {
      showToast('Failed to approve work order', 'error');
    } finally {
      setLoadingId(null);
    }
  };

  const handleDismiss = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    setLoadingId(id);
    try {
      await dismissWorkOrder(id);
      showToast(`Work order #${id} dismissed`, 'info');
      onRefresh();
    } catch {
      showToast('Failed to dismiss work order', 'error');
    } finally {
      setLoadingId(null);
    }
  };

  const handleBulkDelete = async () => {
    const ids = Array.from(selectedIds);
    setBulkDeleting(true);
    let failed = 0;
    for (const id of ids) {
      try {
        await deleteWorkOrder(id);
      } catch {
        failed++;
      }
    }
    setBulkDeleting(false);
    setSelectedIds(new Set());
    if (failed === 0) {
      showToast(`${ids.length} work order${ids.length > 1 ? 's' : ''} deleted`, 'success');
    } else {
      showToast(`${ids.length - failed} deleted, ${failed} failed`, 'error');
    }
    onRefresh();
  };

  const handleEditSelected = (e: React.MouseEvent) => {
    e.stopPropagation();
    const id = Array.from(selectedIds)[0];
    const order = orders.find((o) => o.id === id);
    if (order) onSelectOrder(order);
  };

  if (orders.length === 0) {
    return (
      <div style={{ color: '#556677', fontSize: 13, textAlign: 'center', padding: '40px 0' }}>
        No work orders match the current filters.
      </div>
    );
  }

  return (
    <div>
      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '8px 12px',
            marginBottom: 8,
            background: 'rgba(0,229,160,0.06)',
            border: '1px solid rgba(0,229,160,0.2)',
            borderRadius: 8,
          }}
        >
          <span style={{ fontSize: 12, color: '#00E5A0', fontWeight: 600 }}>
            {selectedIds.size} selected
          </span>
          <div style={{ flex: 1 }} />
          {selectedIds.size === 1 && (
            <button
              onClick={handleEditSelected}
              style={{
                background: 'transparent',
                color: '#8899aa',
                border: '1px solid #2a3649',
                borderRadius: 5,
                padding: '4px 12px',
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Edit
            </button>
          )}
          <button
            onClick={handleBulkDelete}
            disabled={bulkDeleting}
            style={{
              background: 'rgba(255,77,77,0.12)',
              color: '#FF4D4D',
              border: '1px solid rgba(255,77,77,0.3)',
              borderRadius: 5,
              padding: '4px 12px',
              fontSize: 11,
              fontWeight: 700,
              cursor: bulkDeleting ? 'not-allowed' : 'pointer',
              opacity: bulkDeleting ? 0.6 : 1,
            }}
          >
            {bulkDeleting ? 'Deleting…' : `Delete (${selectedIds.size})`}
          </button>
          <button
            onClick={() => setSelectedIds(new Set())}
            style={{
              background: 'transparent',
              color: '#556677',
              border: 'none',
              padding: '4px 6px',
              fontSize: 11,
              cursor: 'pointer',
            }}
          >
            ✕ Clear
          </button>
        </div>
      )}

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #2a3649' }}>
              {/* Select all checkbox */}
              <th style={{ padding: '8px 10px', width: 32 }}>
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = someSelected;
                  }}
                  onChange={toggleAll}
                  style={{ cursor: 'pointer', accentColor: '#00E5A0' }}
                />
              </th>
              {['#', 'Title', 'AHU', 'Level', 'Severity', 'Status', 'Created', 'Actions'].map(
                (h) => (
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
                )
              )}
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => {
              const severityColor =
                HEALTH_TIER_COLORS[order.severity as keyof typeof HEALTH_TIER_COLORS] ?? '#8899aa';
              const statusColor = STATUS_COLOR[order.status] ?? '#8899aa';
              const createdDate = new Date(order.created_at).toLocaleDateString();
              const isSelected = selectedIds.has(order.id);

              return (
                <tr
                  key={order.id}
                  onClick={() => onSelectOrder(order)}
                  style={{
                    borderBottom: '1px solid #1a2234',
                    cursor: 'pointer',
                    transition: 'background 0.1s',
                    background: isSelected ? 'rgba(0,229,160,0.04)' : 'transparent',
                  }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.background = isSelected
                      ? 'rgba(0,229,160,0.07)'
                      : '#1a2234')
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.background = isSelected
                      ? 'rgba(0,229,160,0.04)'
                      : 'transparent')
                  }
                >
                  {/* Row checkbox */}
                  <td
                    style={{ padding: '10px 10px', width: 32 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleRow(order.id);
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleRow(order.id)}
                      style={{ cursor: 'pointer', accentColor: '#00E5A0' }}
                    />
                  </td>
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
                    <div style={{ display: 'flex', gap: 6 }}>
                      {/* Edit button — always visible */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectOrder(order);
                        }}
                        style={{
                          background: 'transparent',
                          color: '#8899aa',
                          border: '1px solid #2a3649',
                          borderRadius: 4,
                          padding: '4px 10px',
                          fontSize: 10,
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        Edit
                      </button>
                      {order.status === 'draft' && (
                        <>
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
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default WorkOrderTable;
