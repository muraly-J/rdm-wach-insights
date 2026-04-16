import { AnimatePresence, motion } from 'framer-motion';
import React, { useState } from 'react';
import { usePolling } from '../../hooks/usePolling';
import { useAppStore } from '../../store/useAppStore';
import WorkOrderPanelItem, { WorkOrder } from './WorkOrderPanelItem';

// Mock fetch function - replace with actual API call
async function fetchWorkOrders(): Promise<WorkOrder[]> {
    // TODO: Replace with actual API call
    // return await fetch('/api/work-orders?status=draft').then(r => r.json());
    return [];
}

export default function WorkOrderPanel() {
    const { workOrderPanelOpen, toggleWorkOrderPanel, setWorkOrderDraftsCount } = useAppStore();
    const { data: workOrders = [], refetch } = usePolling(fetchWorkOrders, 5000);
    const [loadingIds, setLoadingIds] = useState<number[]>([]);

    React.useEffect(() => {
        if (workOrders) {
            setWorkOrderDraftsCount(workOrders.filter((wo) => wo.status === 'draft').length);
        }
    }, [workOrders, setWorkOrderDraftsCount]);

    const handleApprove = async (id: number) => {
        setLoadingIds((prev) => [...prev, id]);
        try {
            // TODO: Call API to approve work order
            // await approveWorkOrder(id);
            await refetch();
        } finally {
            setLoadingIds((prev) => prev.filter((wid) => wid !== id));
        }
    };

    const handleDismiss = async (id: number) => {
        setLoadingIds((prev) => [...prev, id]);
        try {
            // TODO: Call API to dismiss work order
            // await dismissWorkOrder(id);
            await refetch();
        } finally {
            setLoadingIds((prev) => prev.filter((wid) => wid !== id));
        }
    };

    return (
        <AnimatePresence>
            {workOrderPanelOpen && (
                <motion.div
                    initial={{ x: 380, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: 380, opacity: 0 }}
                    transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                    onClick={(e) => e.stopPropagation()}
                    className="fixed right-0 top-0 bottom-0 w-[380px] bg-[#0B0F14] border-l border-[#2a3649] z-40 flex flex-col"
                >
                    {/* Header */}
                    <div className="px-4 py-4 border-b border-[#2a3649] flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-[#00E5A0]">
                            Work Orders ({workOrders.filter((wo) => wo.status === 'draft').length} Draft)
                        </h3>
                        <button
                            onClick={toggleWorkOrderPanel}
                            className="w-8 h-8 rounded hover:bg-[#2a3649] flex items-center justify-center"
                            title="Close panel"
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#E8ECF1" strokeWidth="2">
                                <line x1="18" y1="6" x2="6" y2="18" />
                                <line x1="6" y1="6" x2="18" y2="18" />
                            </svg>
                        </button>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto px-2 py-3">
                        <AnimatePresence mode="popLayout">
                            {workOrders.length === 0 ? (
                                <div className="flex items-center justify-center h-40 text-[#556677] text-sm">
                                    No pending work orders
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {workOrders.map((wo) => (
                                        <WorkOrderPanelItem
                                            key={wo.id}
                                            workOrder={wo}
                                            onApprove={handleApprove}
                                            onDismiss={handleDismiss}
                                            isLoading={loadingIds.includes(wo.id)}
                                        />
                                    ))}
                                </div>
                            )}
                        </AnimatePresence>
                    </div>

                    {/* Footer */}
                    <div className="px-4 py-3 border-t border-[#2a3649]">
                        <button
                            onClick={() => {
                                // Navigate to Work Orders dashboard
                                // TODO: Implement navigation
                            }}
                            className="w-full px-3 py-2 text-xs bg-[#00E5A0] text-black rounded font-semibold hover:opacity-90"
                        >
                            View All
                        </button>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
