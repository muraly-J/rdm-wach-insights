import { motion } from 'framer-motion';
import { useState } from 'react';

export interface WorkOrder {
    id: number;
    title: string;
    description: string;
    status: 'draft' | 'pending' | 'approved' | 'dismissed';
    severity: 'critical' | 'warning' | 'info';
    created_at: string;
    ahu_id: string;
}

interface WorkOrderPanelItemProps {
    workOrder: WorkOrder;
    onApprove?: (id: number) => void;
    onDismiss?: (id: number) => void;
    onEdit?: (id: number) => void;
    isLoading?: boolean;
}

const SEVERITY_COLORS: Record<string, string> = {
    critical: '#FF4D4D',
    warning: '#FFA31A',
    info: '#4DA6FF',
};

export default function WorkOrderPanelItem({
    workOrder,
    onApprove,
    onDismiss,
    onEdit,
    isLoading = false,
}: WorkOrderPanelItemProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    const severityColor = SEVERITY_COLORS[workOrder.severity] || '#4DA6FF';

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="px-4 py-3 bg-[#1a2234] border border-[#2a3649] rounded-lg"
        >
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                style={{ width: '100%', background: 'transparent', border: 'none', cursor: 'pointer' }}
            >
                <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 flex-1">
                        <div
                            style={{
                                width: 12,
                                height: 12,
                                borderRadius: '50%',
                                background: severityColor,
                                marginTop: 4,
                                flexShrink: 0,
                            }}
                        />
                        <div className="text-left flex-1">
                            <h4 className="text-sm font-semibold text-[#E8ECF1]">{workOrder.title}</h4>
                            <p className="text-xs text-[#8899aa] mt-1">{workOrder.ahu_id}</p>
                        </div>
                    </div>
                    <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="#8899aa"
                        strokeWidth="2"
                        style={{
                            transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                            transition: 'transform 0.2s',
                            marginTop: 2,
                        }}
                    >
                        <polyline points="6 9 12 15 18 9" />
                    </svg>
                </div>
            </button>

            {isExpanded && (
                <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="mt-3 pt-3 border-t border-[#2a3649]"
                >
                    <p className="text-xs text-[#8899aa] mb-3">{workOrder.description}</p>

                    <div className="flex gap-2">
                        {workOrder.status === 'draft' && (
                            <>
                                <button
                                    onClick={() => onApprove?.(workOrder.id)}
                                    disabled={isLoading}
                                    className="flex-1 px-2 py-1 text-xs bg-[#00E5A0] text-black rounded font-semibold hover:opacity-90 disabled:opacity-50"
                                >
                                    {isLoading ? 'Approving…' : 'Approve'}
                                </button>
                                <button
                                    onClick={() => onDismiss?.(workOrder.id)}
                                    disabled={isLoading}
                                    className="flex-1 px-2 py-1 text-xs bg-[#2a3649] text-[#E8ECF1] rounded hover:bg-[#1a2234] disabled:opacity-50"
                                >
                                    {isLoading ? 'Dismissing…' : 'Dismiss'}
                                </button>
                            </>
                        )}
                        {workOrder.status !== 'draft' && (
                            <span
                                className="flex-1 px-2 py-1 text-xs text-center rounded font-semibold"
                                style={{
                                    background: `${severityColor}20`,
                                    color: severityColor,
                                    borderColor: severityColor,
                                    border: '1px solid',
                                }}
                            >
                                {workOrder.status === 'pending' && 'Pending Review'}
                                {workOrder.status === 'approved' && 'Approved'}
                                {workOrder.status === 'dismissed' && 'Dismissed'}
                            </span>
                        )}
                    </div>
                </motion.div>
            )}
        </motion.div>
    );
}
