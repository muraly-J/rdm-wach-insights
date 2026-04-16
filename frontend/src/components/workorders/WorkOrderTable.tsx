import { motion } from 'framer-motion';

export interface WorkOrderRow {
    id: number;
    title: string;
    ahu_id: string;
    status: 'draft' | 'pending' | 'approved' | 'dismissed';
    severity: 'critical' | 'warning' | 'info';
    created_at: string;
}

interface WorkOrderTableProps {
    rows: WorkOrderRow[];
    onRowClick?: (row: WorkOrderRow) => void;
    isLoading?: boolean;
}

const SEVERITY_COLORS: Record<string, string> = {
    critical: '#FF4D4D',
    warning: '#FFA31A',
    info: '#4DA6FF',
};

export default function WorkOrderTable({ rows, onRowClick, isLoading }: WorkOrderTableProps) {
    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' });
    };

    if (isLoading) {
        return (
            <div className="flex justify-center py-8">
                <span className="text-[#556677] text-sm animate-pulse">Loading work orders…</span>
            </div>
        );
    }

    if (rows.length === 0) {
        return (
            <div className="flex items-center justify-center py-12 bg-[#1a2234] rounded-lg border border-[#2a3649]">
                <span className="text-[#556677] text-sm">No work orders found</span>
            </div>
        );
    }

    return (
        <div className="overflow-x-auto rounded-lg border border-[#2a3649]">
            <table className="w-full">
                <thead className="bg-[#1a2234]">
                    <tr className="border-b border-[#2a3649]">
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#8899aa]">Title</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#8899aa]">AHU</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#8899aa]">Severity</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#8899aa]">Status</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#8899aa]">Created</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row, idx) => (
                        <motion.tr
                            key={row.id}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: idx * 0.05 }}
                            onClick={() => onRowClick?.(row)}
                            className="border-b border-[#2a3649] hover:bg-[#1a2234] cursor-pointer"
                        >
                            <td className="px-4 py-3 text-sm text-[#E8ECF1] font-medium">{row.title}</td>
                            <td className="px-4 py-3 text-sm text-[#8899aa] font-mono">{row.ahu_id}</td>
                            <td className="px-4 py-3 text-sm">
                                <span
                                    className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold"
                                    style={{
                                        background: `${SEVERITY_COLORS[row.severity]}20`,
                                        color: SEVERITY_COLORS[row.severity],
                                        border: `1px solid ${SEVERITY_COLORS[row.severity]}`,
                                    }}
                                >
                                    {row.severity.charAt(0).toUpperCase() + row.severity.slice(1)}
                                </span>
                            </td>
                            <td className="px-4 py-3 text-sm">
                                <span
                                    className="inline-block px-2 py-1 rounded text-xs font-semibold"
                                    style={{
                                        background:
                                            row.status === 'draft'
                                                ? '#FFA31A20'
                                                : row.status === 'pending'
                                                    ? '#4DA6FF20'
                                                    : row.status === 'approved'
                                                        ? '#00E5A020'
                                                        : '#55667720',
                                        color:
                                            row.status === 'draft'
                                                ? '#FFA31A'
                                                : row.status === 'pending'
                                                    ? '#4DA6FF'
                                                    : row.status === 'approved'
                                                        ? '#00E5A0'
                                                        : '#8899aa',
                                    }}
                                >
                                    {row.status.charAt(0).toUpperCase() + row.status.slice(1)}
                                </span>
                            </td>
                            <td className="px-4 py-3 text-sm text-[#556677]">{formatDate(row.created_at)}</td>
                        </motion.tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
