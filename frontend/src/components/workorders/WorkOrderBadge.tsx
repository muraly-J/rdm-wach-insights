import { useAppStore } from '../../store/useAppStore';

interface WorkOrderBadgeProps {
    draftsCount: number;
    onClick?: () => void;
}

export default function WorkOrderBadge({ draftsCount, onClick }: WorkOrderBadgeProps) {
    const { workOrderDraftsCount } = useAppStore();
    const count = draftsCount || workOrderDraftsCount;

    if (count === 0) return null;

    return (
        <button
            onClick={onClick}
            className="relative"
            title={`${count} draft work orders`}
            style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                padding: 0,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
            }}
        >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00E5A0" strokeWidth="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
            <span
                className="inline-flex items-center justify-center text-xs font-bold text-black"
                style={{
                    width: 20,
                    height: 20,
                    background: '#00E5A0',
                    borderRadius: '50%',
                    animation: 'pulse 2s ease-in-out infinite',
                }}
            >
                {count}
            </span>
        </button>
    );
}
