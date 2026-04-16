
interface WorkOrderFiltersProps {
    selectedStatus?: string;
    onStatusChange?: (status: string) => void;
    selectedSeverity?: string;
    onSeverityChange?: (severity: string) => void;
    searchTerm?: string;
    onSearchChange?: (term: string) => void;
}

const STATUS_OPTIONS = ['all', 'draft', 'pending', 'approved', 'dismissed'];
const SEVERITY_OPTIONS = ['all', 'critical', 'warning', 'info'];

export default function WorkOrderFilters({
    selectedStatus = 'all',
    onStatusChange,
    selectedSeverity = 'all',
    onSeverityChange,
    searchTerm = '',
    onSearchChange,
}: WorkOrderFiltersProps) {
    return (
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:gap-4">
            {/* Search */}
            <div className="flex-1">
                <label className="block text-xs text-[#8899aa] mb-2">Search</label>
                <input
                    type="text"
                    placeholder="Search by title or AHU ID…"
                    value={searchTerm}
                    onChange={(e) => onSearchChange?.(e.target.value)}
                    className="w-full px-3 py-2 bg-[#1a2234] border border-[#2a3649] rounded text-sm text-[#E8ECF1] placeholder-[#556677]"
                />
            </div>

            {/* Status */}
            <div>
                <label className="block text-xs text-[#8899aa] mb-2">Status</label>
                <select
                    value={selectedStatus}
                    onChange={(e) => onStatusChange?.(e.target.value)}
                    className="px-3 py-2 bg-[#1a2234] border border-[#2a3649] rounded text-sm text-[#E8ECF1]"
                >
                    {STATUS_OPTIONS.map((status) => (
                        <option key={status} value={status}>
                            {status.charAt(0).toUpperCase() + status.slice(1)}
                        </option>
                    ))}
                </select>
            </div>

            {/* Severity */}
            <div>
                <label className="block text-xs text-[#8899aa] mb-2">Severity</label>
                <select
                    value={selectedSeverity}
                    onChange={(e) => onSeverityChange?.(e.target.value)}
                    className="px-3 py-2 bg-[#1a2234] border border-[#2a3649] rounded text-sm text-[#E8ECF1]"
                >
                    {SEVERITY_OPTIONS.map((severity) => (
                        <option key={severity} value={severity}>
                            {severity.charAt(0).toUpperCase() + severity.slice(1)}
                        </option>
                    ))}
                </select>
            </div>
        </div>
    );
}
