import { useState } from 'react';
import { motion } from 'framer-motion';
import type { ActionItem } from '../../../types/chat';
import { HEALTH_TIER_COLORS } from '../../../types/chat';
import { approveWorkOrder, dismissWorkOrder, editWorkOrder } from '../../../api/client';
import StateBadge from '../../shared/StateBadge';
import type { OperationalState } from '../../../types';

interface WorkOrderCardProps {
  actions: ActionItem[];
  operational_state?: OperationalState;
  last_on_timestamp?: string | null;
}

export default function WorkOrderCard({ actions, operational_state, last_on_timestamp }: WorkOrderCardProps) {
  const [states, setStates] = useState<Record<number, 'idle' | 'loading' | 'done' | 'dismissed'>>(
    {}
  );
  const [editing, setEditing] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editDesc, setEditDesc] = useState('');

  // Group actions by work_order_id
  const byId: Record<number, ActionItem[]> = {};
  for (const a of actions) {
    if (!byId[a.work_order_id]) byId[a.work_order_id] = [];
    byId[a.work_order_id].push(a);
  }

  const handleApprove = async (woId: number) => {
    setStates((prev) => ({ ...prev, [woId]: 'loading' }));
    try {
      await approveWorkOrder(woId);
      setStates((prev) => ({ ...prev, [woId]: 'done' }));
    } catch {
      setStates((prev) => ({ ...prev, [woId]: 'idle' }));
    }
  };

  const handleDismiss = async (woId: number) => {
    setStates((prev) => ({ ...prev, [woId]: 'loading' }));
    try {
      await dismissWorkOrder(woId);
      setStates((prev) => ({ ...prev, [woId]: 'dismissed' }));
    } catch {
      setStates((prev) => ({ ...prev, [woId]: 'idle' }));
    }
  };

  const handleEdit = async (woId: number) => {
    await editWorkOrder(woId, { title: editTitle, description: editDesc });
    setEditing(null);
  };

  return (
    <div className="flex flex-col gap-2 mt-2">
      {Object.entries(byId).map(([idStr, items]) => {
        const woId = parseInt(idStr);
        const state = states[woId] ?? 'idle';
        const approveItem = items.find((i) => i.type === 'approve_work_order');
        const dismissItem = items.find((i) => i.type === 'dismiss');
        const editItem = items.find((i) => i.type === 'edit_draft');
        const severity =
          approveItem?.description.match(/severity[:\s]*([\w\s]+?)(?:[,\.]|$)/i)?.[1]?.trim() ??
          'Monitor';
        const severityColor =
          HEALTH_TIER_COLORS[severity as keyof typeof HEALTH_TIER_COLORS] ?? '#4DA6FF';

        if (state === 'dismissed') return null;

        return (
          <motion.div
            key={woId}
            layout
            className="rounded-[10px] px-3.5 py-2.5"
            style={{
              background: '#141920',
              border: `1px solid ${severityColor}33`,
            }}
          >
            {state === 'done' ? (
              <div className="flex items-center gap-1.5 text-[#00E5A0] text-[13px]">
                <span>✓</span> Ticket Submitted
              </div>
            ) : editing === woId ? (
              <div className="flex flex-col gap-1.5">
                <input
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  placeholder="Title"
                  className="bg-[#0D1520] border border-[#1a2638] rounded-md px-2 py-1.5 text-[#E8ECF1] text-xs outline-none"
                />
                <textarea
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                  placeholder="Description"
                  rows={2}
                  className="bg-[#0D1520] border border-[#1a2638] rounded-md px-2 py-1.5 text-[#E8ECF1] text-xs outline-none resize-none"
                />
                <div className="flex gap-1.5">
                  <button
                    onClick={() => handleEdit(woId)}
                    className="bg-[#00E5A0] text-[#0B0F14] rounded-full px-3 py-1 text-[11px] font-semibold cursor-pointer border-none"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setEditing(null)}
                    className="bg-transparent text-[#6d6e71] border border-[#1a2638] rounded-full px-3 py-1 text-[11px] cursor-pointer"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span
                    className="inline-block w-1.5 h-1.5 rounded-full"
                    style={{ background: severityColor }}
                  />
                  <span className="text-[12px] font-semibold text-[#E8ECF1]">
                    Work Order #{woId}
                  </span>
                  <span
                    className="text-[10px] font-semibold uppercase"
                    style={{ color: severityColor }}
                  >
                    {severity}
                  </span>
                  {operational_state && (
                    <StateBadge
                      state={operational_state}
                      lastMeasured={last_on_timestamp}
                    />
                  )}
                </div>
                <p className="text-[11px] text-[#8899aa] mb-2">
                  {approveItem?.description ?? dismissItem?.description ?? ''}
                </p>
                <div className="flex gap-1.5 flex-wrap">
                  {approveItem && (
                    <button
                      disabled={state === 'loading'}
                      onClick={() => handleApprove(woId)}
                      className="bg-[#00E5A0] text-[#0B0F14] border-none rounded-full px-3 py-1 text-[11px] font-semibold cursor-pointer disabled:opacity-50 min-h-[28px]"
                    >
                      {state === 'loading' ? '...' : approveItem.label}
                    </button>
                  )}
                  {editItem && (
                    <button
                      onClick={() => {
                        setEditing(woId);
                        setEditTitle('');
                        setEditDesc('');
                      }}
                      className="bg-transparent text-[#8899aa] border border-[#1a2638] rounded-full px-3 py-1 text-[11px] cursor-pointer"
                    >
                      {editItem.label}
                    </button>
                  )}
                  {dismissItem && (
                    <button
                      disabled={state === 'loading'}
                      onClick={() => handleDismiss(woId)}
                      className="bg-transparent text-[#6d6e71] border border-[#1a2638] rounded-full px-3 py-1 text-[11px] cursor-pointer disabled:opacity-50 min-h-[28px]"
                    >
                      {dismissItem.label}
                    </button>
                  )}
                </div>
              </div>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}
