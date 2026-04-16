import { motion } from 'framer-motion';

export interface TimelineStep {
    status: string;
    timestamp: string;
    label: string;
    description?: string;
}

interface StatusTimelineProps {
    steps: TimelineStep[];
    currentStatus?: string;
}

const STATUS_COLORS: Record<string, string> = {
    draft: '#FFA31A',
    pending: '#4DA6FF',
    approved: '#00E5A0',
    dismissed: '#8899aa',
};

export default function StatusTimeline({ steps, currentStatus }: StatusTimelineProps) {
    const formatTime = (timeStr: string) => {
        const date = new Date(timeStr);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    return (
        <div className="space-y-4">
            {steps.map((step, idx) => {
                const isActive = step.status === currentStatus;
                const isPast = steps.findIndex((s) => s.status === currentStatus) > idx;
                const color = STATUS_COLORS[step.status] || '#8899aa';

                return (
                    <motion.div
                        key={step.status}
                        initial={{ opacity: 0, x: -8 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        className="flex gap-4"
                    >
                        {/* Timeline dot */}
                        <div className="flex flex-col items-center">
                            <motion.div
                                animate={{
                                    scale: isActive ? 1.2 : 1,
                                    boxShadow: isActive ? `0 0 12px ${color}` : 'none',
                                }}
                                className="w-4 h-4 rounded-full border-2"
                                style={{
                                    borderColor: color,
                                    background: isPast || isActive ? color : 'transparent',
                                }}
                            />
                            {idx < steps.length - 1 && (
                                <div
                                    className="w-0.5 flex-1 my-2"
                                    style={{ background: isPast ? color : '#2a3649', minHeight: 32 }}
                                />
                            )}
                        </div>

                        {/* Content */}
                        <div className="pb-4">
                            <h4
                                className="text-sm font-semibold"
                                style={{ color: isActive ? color : '#E8ECF1' }}
                            >
                                {step.label}
                            </h4>
                            {step.description && (
                                <p className="text-xs text-[#8899aa] mt-1">{step.description}</p>
                            )}
                            <p className="text-xs text-[#556677] mt-2">{formatTime(step.timestamp)}</p>
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
}
