/**
 * WhatsApp Leads List Component
 * Left sidebar with paginated list of WhatsApp leads.
 */
import { WhatsAppLeadSummary } from '../../types/whatsapp';

interface WhatsAppLeadsListProps {
    leads: WhatsAppLeadSummary[];
    loading: boolean;
    selectedLeadId: number | null;
    onSelectLead: (id: number) => void;
    totalCount: number;
    currentPage: number;
    onPageChange: (page: number) => void;
    pageLimit: number;
    sourceFilter: string;
    onSourceFilterChange: (source: string) => void;
    selectedForBulk: Set<number>;
    onToggleBulk: (id: number) => void;
    onClearBulk: () => void;
}

export default function WhatsAppLeadsList({
    leads,
    loading,
    selectedLeadId,
    onSelectLead,
    totalCount,
    currentPage,
    onPageChange,
    pageLimit,
    sourceFilter,
    onSourceFilterChange,
    selectedForBulk,
    onToggleBulk,
    onClearBulk
}: WhatsAppLeadsListProps) {
    const totalPages = Math.ceil(totalCount / pageLimit);

    const getStatusBadge = (lead: WhatsAppLeadSummary) => {
        if (!lead.is_wa_sent) {
            return <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">Not Sent</span>;
        }

        switch (lead.last_delivery_status) {
            case 'SENT':
                return <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">Sent</span>;
            case 'DELIVERED':
                return <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">Delivered</span>;
            case 'READ':
                return <span className="px-2 py-0.5 bg-green-200 text-green-800 text-xs rounded-full">Read ✓</span>;
            case 'FAILED':
                return <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full">Failed</span>;
            default:
                return <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 text-xs rounded-full">Pending</span>;
        }
    };

    const getSourceBadge = (source?: string) => {
        switch (source) {
            case 'manual':
                return <span className="px-1.5 py-0.5 bg-purple-100 text-purple-600 text-xs rounded">Manual</span>;
            case 'email_import':
                return <span className="px-1.5 py-0.5 bg-blue-100 text-blue-600 text-xs rounded">Email</span>;
            case 'linkedin_import':
                return <span className="px-1.5 py-0.5 bg-cyan-100 text-cyan-600 text-xs rounded">LinkedIn</span>;
            default:
                return null;
        }
    };

    return (
        <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between mb-3">
                    <h2 className="font-semibold text-gray-800">
                        Leads ({totalCount})
                    </h2>
                    {selectedForBulk.size > 0 && (
                        <button
                            onClick={onClearBulk}
                            className="text-xs text-gray-500 hover:text-gray-700"
                        >
                            Clear ({selectedForBulk.size})
                        </button>
                    )}
                </div>

                {/* Source Filter */}
                <select
                    value={sourceFilter}
                    onChange={(e) => onSourceFilterChange(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                >
                    <option value="">All Sources</option>
                    <option value="manual">Manual</option>
                    <option value="email_import">Email Import</option>
                    <option value="linkedin_import">LinkedIn Import</option>
                </select>
            </div>

            {/* Leads List */}
            <div className="flex-1 overflow-y-auto">
                {loading ? (
                    <div className="flex items-center justify-center h-32">
                        <div className="animate-spin text-2xl">⏳</div>
                    </div>
                ) : leads.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                        <span className="text-3xl mb-2">📭</span>
                        <span>No leads found</span>
                    </div>
                ) : (
                    leads.map((lead) => (
                        <div
                            key={lead.id}
                            onClick={() => onSelectLead(lead.id)}
                            className={`p-3 border-b border-gray-100 cursor-pointer transition-colors ${selectedLeadId === lead.id
                                    ? 'bg-green-50 border-l-4 border-l-green-500'
                                    : 'hover:bg-gray-50'
                                }`}
                        >
                            <div className="flex items-start gap-2">
                                {/* Bulk Checkbox */}
                                <input
                                    type="checkbox"
                                    checked={selectedForBulk.has(lead.id)}
                                    onChange={(e) => {
                                        e.stopPropagation();
                                        onToggleBulk(lead.id);
                                    }}
                                    className="mt-1 rounded border-gray-300 text-green-600 focus:ring-green-500"
                                />

                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="font-medium text-gray-800 truncate">
                                            {lead.first_name} {lead.last_name}
                                        </span>
                                        {getSourceBadge(lead.source)}
                                    </div>

                                    <div className="text-sm text-gray-500 truncate">
                                        📱 {lead.mobile_number}
                                    </div>

                                    {lead.company_name && (
                                        <div className="text-sm text-gray-400 truncate">
                                            🏢 {lead.company_name}
                                        </div>
                                    )}

                                    <div className="mt-1">
                                        {getStatusBadge(lead)}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="p-3 border-t border-gray-200 flex items-center justify-between">
                    <button
                        onClick={() => onPageChange(currentPage - 1)}
                        disabled={currentPage === 0}
                        className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
                    >
                        ← Prev
                    </button>
                    <span className="text-sm text-gray-600">
                        {currentPage + 1} / {totalPages}
                    </span>
                    <button
                        onClick={() => onPageChange(currentPage + 1)}
                        disabled={currentPage >= totalPages - 1}
                        className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
                    >
                        Next →
                    </button>
                </div>
            )}
        </div>
    );
}
