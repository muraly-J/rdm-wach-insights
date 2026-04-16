import { AnimatePresence, motion } from 'framer-motion';
import StatusTimeline, { TimelineStep } from './StatusTimeline';

export interface WorkOrderDetail {
    id: number;
    title: string;
    description: string;
    ahu_id: string;
    status: 'draft' | 'pending' | 'approved' | 'dismissed';
    severity: 'critical' | 'warning' | 'info';
    created_at: string;
    updated_at: string;
    timeline: TimelineStep[];
    assigned_to?: string;
    due_date?: string;
}

interface WorkOrderDetailModalProps {
    isOpen: boolean;
    workOrder?: WorkOrderDetail | null;
    onClose: () => void;
    onApprove?: (id: number) => void;
    onDismiss?: (id: number) => void;
    isLoading?: boolean;
}

const SEVERITY_COLORS: Record<string, string> = {
    critical: '#FF4D4D',
    warning: '#FFA31A',
    info: '#4DA6FF',
};

export default function WorkOrderDetailModal({
    isOpen,
    workOrder,
    onClose,
    onApprove,
    onDismiss,
    isLoading,
}: WorkOrderDetailModalProps) {
    if (!workOrder) return null;

    const severityColor = SEVERITY_COLORS[workOrder.severity] || '#4DA6FF';

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="absolute inset-0 bg-black/50"
                    />

                    {/* Modal */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="relative bg-[#0B0F14] border border-[#2a3649] rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
                    >
                        {/* Header */}
                        <div className="sticky top-0 px-6 py-4 border-b border-[#2a3649] bg-[#0B0F14] flex items-start justify-between">
                            <div>
                                <div className="flex items-center gap-3 mb-2">
                                    <div
                                        style={{
                                            width: 12,
                                            height: 12,
                                            borderRadius: '50%',
                                            background: severityColor,
                                        }}
                                    />
                                    <span
                                        className="text-xs font-semibold"
                                        style={{
                                            color: severityColor,
                                        }}
                                    >
                                        {workOrder.severity.toUpperCase()}
                                    </span>
                                </div>
                                <h3 className="text-lg font-bold text-[#E8ECF1]">{workOrder.title}</h3>
                            </div>
                            <button
                                onClick={onClose}
                                className="w-8 h-8 rounded hover:bg-[#2a3649] flex items-center justify-center"
                            >
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#E8ECF1" strokeWidth="2">
                                    <line x1="18" y1="6" x2="6" y2="18" />
                                    <line x1="6" y1="6" x2="18" y2="18" />
                                </svg>
                            </button>
                        </div>

                        {/* Content */}
                        <div className="px-6 py-4 space-y-6">
                            {/* Info grid */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-xs text-[#8899aa] mb-1">AHU ID</p>
                                    <p className="text-sm font-mono text-[#E8ECF1]">{workOrder.ahu_id}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-[#8899aa] mb-1">Status</p>
                                    <p className="text-sm text-[#E8ECF1] font-semibold capitalize">{workOrder.status}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-[#8899aa] mb-1">Created</p>
                                    <p className="text-sm text-[#E8ECF1]">
                                        {new Date(workOrder.created_at).toLocaleDateString()}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-[#8899aa] mb-1">Updated</p>
                                    <p className="text-sm text-[#E8ECF1]">
                                        {new Date(workOrder.updated_at).toLocaleDateString()}
                                    </p>
                                </div>
                            </div>

                            {/* Description */}
                            <div>
                                <p className="text-xs text-[#8899aa] mb-2">Description</p>
                                <p className="text-sm text-[#E8ECF1] leading-relaxed">{workOrder.description}</p>
                            </div>

                            {/* Timeline */}
                            <div>
                                <p className="text-xs text-[#8899aa] mb-3">Status History</p>
                                <StatusTimeline steps={workOrder.timeline} currentStatus={workOrder.status} />
                            </div>
                        </div>

                        {/* Footer */}
                        {workOrder.status === 'draft' && (
                            <div className="sticky bottom-0 px-6 py-4 border-t border-[#2a3649] bg-[#0B0F14] flex gap-3">
                                <button
                                    onClick={() => onApprove?.(workOrder.id)}
                                    disabled={isLoading}
                                    className="flex-1 px-4 py-2 text-sm bg-[#00E5A0] text-black rounded font-semibold hover:opacity-90 disabled:opacity-50"
                                >
                                    {isLoading ? 'Approving…' : 'Approve'}
                                </button>
                                <button
                                    onClick={() => onDismiss?.(workOrder.id)}
                                    disabled={isLoading}
                                    className="flex-1 px-4 py-2 text-sm bg-[#2a3649] text-[#E8ECF1] rounded hover:bg-[#1a2234] disabled:opacity-50"
                                >
                                    {isLoading ? 'Dismissing…' : 'Dismiss'}
                                </button>
                            </div>
                        )}
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}
