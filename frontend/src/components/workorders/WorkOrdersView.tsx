import { useState } from 'react';
import { usePolling } from '../../hooks/usePolling';
import WorkOrderDetailModal from './WorkOrderDetailModal';
import WorkOrderFilters from './WorkOrderFilters';
import WorkOrderStatsBar from './WorkOrderStatsBar';
import WorkOrderTable, { WorkOrderRow } from './WorkOrderTable';

// Mock fetch function - replace with actual API
async function fetchWorkOrders(): Promise<WorkOrderRow[]> {
    // TODO: Replace with actual API call
    // return await fetch('/api/work-orders').then(r => r.json());
    return [];
}

export default function WorkOrdersView() {
    const { data: workOrders = [], isLoading: isLoadingWOs } = usePolling(fetchWorkOrders, 5000);
    const [selectedStatus, setSelectedStatus] = useState('all');
    const [selectedSeverity, setSelectedSeverity] = useState('all');
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedRow, setSelectedRow] = useState<WorkOrderRow | null>(null);
    const [detailModalOpen, setDetailModalOpen] = useState(false);

    // Calculate stats
    const stats = {
        drafts: workOrders.filter((wo) => wo.status === 'draft').length,
        pending: workOrders.filter((wo) => wo.status === 'pending').length,
        approved: workOrders.filter((wo) => wo.status === 'approved').length,
        dismissed: workOrders.filter((wo) => wo.status === 'dismissed').length,
    };

    // Filter rows
    const filteredRows = workOrders.filter((wo) => {
        if (selectedStatus !== 'all' && wo.status !== selectedStatus) return false;
        if (selectedSeverity !== 'all' && wo.severity !== selectedSeverity) return false;
        if (searchTerm && !wo.title.toLowerCase().includes(searchTerm.toLowerCase()) && !wo.ahu_id.includes(searchTerm)) {
            return false;
        }
        return true;
    });

    const handleRowClick = (row: WorkOrderRow) => {
        setSelectedRow(row);
        setDetailModalOpen(true);
    };

    return (
        <div className="space-y-6">
            {/* Stats bar */}
            <WorkOrderStatsBar stats={stats} />

            {/* Filters */}
            <WorkOrderFilters
                selectedStatus={selectedStatus}
                onStatusChange={setSelectedStatus}
                selectedSeverity={selectedSeverity}
                onSeverityChange={setSelectedSeverity}
                searchTerm={searchTerm}
                onSearchChange={setSearchTerm}
            />

            {/* Table */}
            <WorkOrderTable
                rows={filteredRows}
                onRowClick={handleRowClick}
                isLoading={isLoadingWOs}
            />

            {/* Detail modal */}
            {selectedRow && (
                <WorkOrderDetailModal
                    isOpen={detailModalOpen}
                    workOrder={{
                        ...selectedRow,
                        timeline: [
                            {
                                status: 'draft',
                                timestamp: selectedRow.created_at,
                                label: 'Created',
                            },
                            {
                                status: 'pending',
                                timestamp: new Date().toISOString(),
                                label: 'Submitted',
                            },
                        ],
                    }}
                    onClose={() => setDetailModalOpen(false)}
                    onApprove={(id) => {
                        console.log('Approve:', id);
                        setDetailModalOpen(false);
                    }}
                    onDismiss={(id) => {
                        console.log('Dismiss:', id);
                        setDetailModalOpen(false);
                    }}
                />
            )}
        </div>
    );
}
