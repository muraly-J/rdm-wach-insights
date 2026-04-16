import { motion } from 'framer-motion';

interface StatsData {
    drafts: number;
    pending: number;
    approved: number;
    dismissed: number;
}

interface WorkOrderStatsBarProps {
    stats: StatsData;
}

export default function WorkOrderStatsBar({ stats }: WorkOrderStatsBarProps) {
    const statItems = [
        { label: 'Draft', value: stats.drafts, color: '#FFA31A', icon: 'draft' },
        { label: 'Pending', value: stats.pending, color: '#4DA6FF', icon: 'pending' },
        { label: 'Approved', value: stats.approved, color: '#00E5A0', icon: 'approved' },
        { label: 'Dismissed', value: stats.dismissed, color: '#8899aa', icon: 'dismissed' },
    ];

    return (
        <div className="grid grid-cols-4 gap-4 mb-6">
            {statItems.map((item, idx) => (
                <motion.div
                    key={item.label}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="bg-[#1a2234] border border-[#2a3649] rounded-lg p-4"
                >
                    <div className="flex items-center gap-2 mb-2">
                        <div
                            style={{
                                width: 8,
                                height: 8,
                                borderRadius: '50%',
                                background: item.color,
                            }}
                        />
                        <span className="text-xs text-[#8899aa]">{item.label}</span>
                    </div>
                    <div className="text-2xl font-bold text-[#E8ECF1]">{item.value}</div>
                </motion.div>
            ))}
        </div>
    );
}
