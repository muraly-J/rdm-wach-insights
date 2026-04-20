import { AnimatePresence, motion } from 'framer-motion';
import React, { useState } from 'react';
import { approveWorkOrder, deleteWorkOrder, dismissWorkOrder, editWorkOrder } from '../../api/client';
import { useToast } from '../../hooks/useToast';
import { WorkOrder } from '../../types/chat';
import StatusTimeline from './StatusTimeline';

interface WorkOrderDetailModalProps {
  order: WorkOrder | null;
  onClose: () => void;
  onUpdated: () => void;
}

const SEVERITY_COLOR: Record<string, string> = {
  Critical: '#FF4D4D',
  'Maintenance Soon': '#FFB020',
  Monitor: '#4DA6FF',
  Healthy: '#00E5A0',
};

const WorkOrderDetailModal: React.FC<WorkOrderDetailModalProps> = ({
  order,
  onClose,
  onUpdated,
}) => {
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [loading, setLoading] = useState<'approve' | 'dismiss' | 'save' | 'delete' | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const { showToast } = useToast();

  React.useEffect(() => {
    if (order) {
      setEditTitle(order.title);
      setEditDesc(order.description ?? '');
      setEditing(false);
    }
  }, [order]);

  const handleApprove = async () => {
    if (!order) return;
    setLoading('approve');
    try {
      await approveWorkOrder(order.id);
      showToast(`Work order #${order.id} approved`, 'success');
      onUpdated();
      onClose();
    } catch {
      showToast('Failed to approve work order', 'error');
    } finally {
      setLoading(null);
    }
  };

  const handleDismiss = async () => {
    if (!order) return;
    setLoading('dismiss');
    try {
      await dismissWorkOrder(order.id);
      showToast(`Work order #${order.id} dismissed`, 'info');
      onUpdated();
      onClose();
    } catch {
      showToast('Failed to dismiss work order', 'error');
    } finally {
      setLoading(null);
    }
  };

  const handleSaveEdit = async () => {
    if (!order) return;
    setLoading('save');
    try {
      await editWorkOrder(order.id, { title: editTitle, description: editDesc });
      showToast('Work order updated', 'success');
      onUpdated();
      setEditing(false);
    } catch {
      showToast('Failed to save changes', 'error');
    } finally {
      setLoading(null);
    }
  };

  const handleDelete = async () => {
    if (!order) return;
    setLoading('delete');
    try {
      await deleteWorkOrder(order.id);
      showToast(`Work order #${order.id} deleted`, 'success');
      setShowDeleteConfirm(false);
      onUpdated();
      onClose();
    } catch {
      showToast('Failed to delete work order', 'error');
    } finally {
      setLoading(null);
    }
  };

  const severityColor = order ? (SEVERITY_COLOR[order.severity] ?? '#8899aa') : '#8899aa';

  return (
    <AnimatePresence>
      {order && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.6)',
              zIndex: 90,
            }}
          />

          {/* Modal — wrapper handles centering, inner div handles animation */}
          <div
            style={{
              position: 'fixed',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 91,
              pointerEvents: 'none',
            }}
          >
            <motion.div
              key="modal"
              initial={{ opacity: 0, scale: 0.95, y: 16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 8 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              style={{
                width: 'min(600px, 90vw)',
                maxHeight: '85vh',
                background: '#111827',
                border: '1px solid #2a3649',
                borderRadius: 12,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                pointerEvents: 'auto',
              }}
            >
              {/* Header */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  padding: '20px 20px 16px',
                  borderBottom: '1px solid #1a2234',
                  gap: 12,
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
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
                  <h2
                    style={{
                      margin: 0,
                      fontSize: 16,
                      fontWeight: 700,
                      color: '#E8ECF1',
                      lineHeight: 1.3,
                    }}
                  >
                    {order.title}
                  </h2>
                  <div style={{ fontSize: 11, color: '#556677', marginTop: 4 }}>
                    AHU {order.ahu_id} · Level {order.level} · {order.trigger_source}
                  </div>
                </div>
                <button
                  onClick={onClose}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#8899aa',
                    cursor: 'pointer',
                    padding: 4,
                    flexShrink: 0,
                  }}
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>

              {/* Body */}
              <div
                style={{
                  flex: 1,
                  overflowY: 'auto',
                  padding: '16px 20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 20,
                }}
              >
                {/* Description */}
                <div>
                  <div
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      color: '#556677',
                      textTransform: 'uppercase',
                      letterSpacing: '0.06em',
                      marginBottom: 8,
                    }}
                  >
                    Description
                  </div>
                  {editing ? (
                    <textarea
                      value={editDesc}
                      onChange={(e) => setEditDesc(e.target.value)}
                      rows={4}
                      style={{
                        width: '100%',
                        background: '#1a2234',
                        border: '1px solid #2a3649',
                        borderRadius: 6,
                        padding: '8px 10px',
                        color: '#E8ECF1',
                        fontSize: 12,
                        resize: 'vertical',
                        outline: 'none',
                        boxSizing: 'border-box',
                      }}
                    />
                  ) : (
                    <p
                      style={{
                        margin: 0,
                        fontSize: 13,
                        color: order.description ? '#C8D4E0' : '#556677',
                        lineHeight: 1.6,
                      }}
                    >
                      {order.description ?? 'No description provided.'}
                    </p>
                  )}
                </div>

                {/* FAIR Snapshot */}
                {(() => {
                  let snapshot: Record<string, number> | null = null;
                  if (order.fair_snapshot) {
                    if (typeof order.fair_snapshot === 'string') {
                      try {
                        snapshot = JSON.parse(order.fair_snapshot);
                      } catch {
                        snapshot = null;
                      }
                    } else {
                      snapshot = order.fair_snapshot;
                    }
                  }
                  if (!snapshot || Object.keys(snapshot).length === 0) return null;
                  const FAIR_ORDER = ['F', 'A', 'I', 'R', 'composite'];
                  const entries = FAIR_ORDER.filter((k) => k in snapshot!).map(
                    (k) => [k, snapshot![k]] as [string, number]
                  );
                  return (
                    <div>
                      <div
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          color: '#556677',
                          textTransform: 'uppercase',
                          letterSpacing: '0.06em',
                          marginBottom: 8,
                        }}
                      >
                        FAIR Snapshot
                      </div>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {entries.map(([key, val]) => {
                          const score = typeof val === 'number' ? val : parseFloat(String(val));
                          const barColor =
                            score >= 70 ? '#00E5A0' : score >= 40 ? '#FFB020' : '#FF4D4D';
                          const isComposite = key === 'composite';
                          return (
                            <div
                              key={key}
                              style={{
                                background: '#1a2234',
                                border: `1px solid ${isComposite ? barColor + '55' : '#2a3649'}`,
                                borderRadius: 8,
                                padding: '10px 14px',
                                minWidth: isComposite ? 90 : 70,
                                flex: isComposite ? '1 1 auto' : '0 0 auto',
                              }}
                            >
                              <div
                                style={{
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'baseline',
                                  marginBottom: 6,
                                }}
                              >
                                <div
                                  style={{
                                    fontSize: 10,
                                    color: '#556677',
                                    textTransform: 'uppercase',
                                    fontWeight: 700,
                                    letterSpacing: '0.05em',
                                  }}
                                >
                                  {key}
                                </div>
                                <div
                                  style={{
                                    fontSize: 15,
                                    fontWeight: 700,
                                    color: isComposite ? barColor : '#E8ECF1',
                                    fontVariantNumeric: 'tabular-nums',
                                  }}
                                >
                                  {isNaN(score) ? String(val) : score.toFixed(1)}
                                </div>
                              </div>
                              <div
                                style={{
                                  height: 3,
                                  borderRadius: 2,
                                  background: '#0d1520',
                                  overflow: 'hidden',
                                }}
                              >
                                <div
                                  style={{
                                    height: '100%',
                                    width: `${Math.min(100, Math.max(0, isNaN(score) ? 0 : score))}%`,
                                    background: barColor,
                                    borderRadius: 2,
                                    transition: 'width 400ms ease',
                                  }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })()}

                {/* Timeline */}
                <div>
                  <div
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      color: '#556677',
                      textTransform: 'uppercase',
                      letterSpacing: '0.06em',
                      marginBottom: 12,
                    }}
                  >
                    Timeline
                  </div>
                  <StatusTimeline order={order} />
                </div>

                {/* Meta */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  {[
                    { label: 'Created by', value: order.created_by },
                    { label: 'Approved by', value: order.approved_by ?? '—' },
                    { label: 'Notified via', value: order.notified_via },
                    { label: 'Status', value: order.status },
                  ].map(({ label, value }) => (
                    <div
                      key={label}
                      style={{
                        background: '#1a2234',
                        border: '1px solid #2a3649',
                        borderRadius: 6,
                        padding: '8px 12px',
                      }}
                    >
                      <div style={{ fontSize: 10, color: '#556677', marginBottom: 2 }}>{label}</div>
                      <div style={{ fontSize: 12, color: '#E8ECF1', fontWeight: 600 }}>{value}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Footer */}
              {order.status === 'draft' && (
                <div
                  style={{
                    padding: '12px 20px',
                    borderTop: '1px solid #1a2234',
                    display: 'flex',
                    gap: 8,
                    justifyContent: 'space-between',
                  }}
                >
                  <button
                    onClick={() => setShowDeleteConfirm(true)}
                    disabled={loading !== null}
                    style={{
                      background: '#FF4D4D',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 6,
                      padding: '8px 16px',
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: loading !== null ? 'not-allowed' : 'pointer',
                      opacity: loading !== null ? 0.7 : 1,
                    }}
                  >
                    Delete
                  </button>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {editing ? (
                      <>
                        <button
                          onClick={() => setEditing(false)}
                          style={{
                            background: 'transparent',
                            color: '#8899aa',
                            border: '1px solid #2a3649',
                            borderRadius: 6,
                            padding: '8px 16px',
                            fontSize: 12,
                            cursor: 'pointer',
                          }}
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleSaveEdit}
                          disabled={loading === 'save'}
                          style={{
                            background: '#00E5A0',
                            color: '#000',
                            border: 'none',
                            borderRadius: 6,
                            padding: '8px 16px',
                            fontSize: 12,
                            fontWeight: 700,
                            cursor: loading === 'save' ? 'not-allowed' : 'pointer',
                            opacity: loading === 'save' ? 0.7 : 1,
                          }}
                        >
                          {loading === 'save' ? 'Saving…' : 'Save Changes'}
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => setEditing(true)}
                          style={{
                            background: 'transparent',
                            color: '#8899aa',
                            border: '1px solid #2a3649',
                            borderRadius: 6,
                            padding: '8px 16px',
                            fontSize: 12,
                            cursor: 'pointer',
                          }}
                        >
                          Edit
                        </button>
                        <button
                          onClick={handleDismiss}
                          disabled={loading !== null}
                          style={{
                            background: 'transparent',
                            color: '#8899aa',
                            border: '1px solid #2a3649',
                            borderRadius: 6,
                            padding: '8px 16px',
                            fontSize: 12,
                            cursor: loading !== null ? 'not-allowed' : 'pointer',
                            opacity: loading !== null ? 0.7 : 1,
                          }}
                        >
                          {loading === 'dismiss' ? 'Dismissing…' : 'Dismiss'}
                        </button>
                        <button
                          onClick={handleApprove}
                          disabled={loading !== null}
                          style={{
                            background: '#00E5A0',
                            color: '#000',
                            border: 'none',
                            borderRadius: 6,
                            padding: '8px 20px',
                            fontSize: 12,
                            fontWeight: 700,
                            cursor: loading !== null ? 'not-allowed' : 'pointer',
                            opacity: loading !== null ? 0.7 : 1,
                          }}
                        >
                          {loading === 'approve' ? 'Approving…' : 'Approve'}
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </motion.div>
          </div>
        </>
      )}

      {/* Delete Confirmation Dialog */}
      <AnimatePresence>
        {showDeleteConfirm && (
          <>
            <motion.div
              key="confirm-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={() => setShowDeleteConfirm(false)}
              style={{
                position: 'fixed',
                inset: 0,
                background: 'rgba(0,0,0,0.6)',
                zIndex: 92,
              }}
            />
            <div
              style={{
                position: 'fixed',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 93,
                pointerEvents: 'none',
              }}
            >
              <motion.div
                key="confirm-dialog"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2 }}
                style={{
                  width: 'min(400px, 90vw)',
                  background: '#111827',
                  border: '1px solid #2a3649',
                  borderRadius: 12,
                  padding: '24px',
                  pointerEvents: 'auto',
                }}
              >
                <h3
                  style={{
                    margin: '0 0 8px 0',
                    fontSize: 16,
                    fontWeight: 700,
                    color: '#E8ECF1',
                  }}
                >
                  Delete Work Order?
                </h3>
                <p
                  style={{
                    margin: '0 0 24px 0',
                    fontSize: 13,
                    color: '#C8D4E0',
                    lineHeight: 1.5,
                  }}
                >
                  This will permanently delete work order #{order?.id}. This action cannot be undone.
                </p>
                <div
                  style={{
                    display: 'flex',
                    gap: 12,
                    justifyContent: 'flex-end',
                  }}
                >
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    disabled={loading === 'delete'}
                    style={{
                      background: 'transparent',
                      color: '#8899aa',
                      border: '1px solid #2a3649',
                      borderRadius: 6,
                      padding: '8px 16px',
                      fontSize: 12,
                      cursor: loading === 'delete' ? 'not-allowed' : 'pointer',
                      opacity: loading === 'delete' ? 0.7 : 1,
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleDelete}
                    disabled={loading === 'delete'}
                    style={{
                      background: '#FF4D4D',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 6,
                      padding: '8px 16px',
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: loading === 'delete' ? 'not-allowed' : 'pointer',
                      opacity: loading === 'delete' ? 0.7 : 1,
                    }}
                  >
                    {loading === 'delete' ? 'Deleting…' : 'Delete'}
                  </button>
                </div>
              </motion.div>
            </div>
          </>
        )}
      </AnimatePresence>
    </AnimatePresence>
  );
};

export default WorkOrderDetailModal;
