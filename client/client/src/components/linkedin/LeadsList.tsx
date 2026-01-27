'use client';

import { Filter, Loader2, Search } from 'lucide-react';
import { LinkedInLead } from '../../types/linkedin';
import BulkActionBar from './BulkActionBar';
import LeadCard from './LeadCard';

interface LeadsListProps {
    leads: LinkedInLead[];
    loading: boolean;
    selectedLeadId: number | null;
    onSelectLead: (id: number) => void;
    availableKeywords: string[];
    selectedKeywordFilter: string;
    onKeywordFilterChange: (value: string) => void;
    totalCount: number;
    currentPage: number;
    onPageChange: (page: number) => void;
    pageLimit: number;
    selectedForBulk: Set<number>;
    onToggleBulk: (id: number) => void;
    onSelectAll: () => void;
    onBulkRefresh: () => void;
    onBulkSendConnection: () => void;
    onBulkSendDM: () => void;
    isBulkRefreshing: boolean;
    isBulkSendingConnection: boolean;
    isBulkSendingDM: boolean;
}

export default function LeadsList({
    leads,
    loading,
    selectedLeadId,
    onSelectLead,
    availableKeywords,
    selectedKeywordFilter,
    onKeywordFilterChange,
    totalCount,
    currentPage,
    onPageChange,
    pageLimit,
    selectedForBulk,
    onToggleBulk,
    onSelectAll,
    onBulkRefresh,
    onBulkSendConnection,
    onBulkSendDM,
    isBulkRefreshing,
    isBulkSendingConnection,
    isBulkSendingDM
}: LeadsListProps) {
    return (
        <div className="w-1/3 border-r border-pink-200 bg-stone-200 flex flex-col">
            <div className="p-4 border-b border-pink-100">
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                        <Filter className="w-4 h-4 text-pink-600" />
                        <select
                            value={selectedKeywordFilter}
                            onChange={(e) => onKeywordFilterChange(e.target.value)}
                            className="text-sm border border-pink-200 rounded-lg px-3 py-1.5 outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-900"
                        >
                            <option value="">All Keywords</option>
                            {availableKeywords.map(kw => (
                                <option key={kw} value={kw}>{kw}</option>
                            ))}
                        </select>
                    </div>
                    <span className="text-sm text-gray-500">
                        {totalCount} lead{totalCount !== 1 ? 's' : ''}
                    </span>
                </div>

                <BulkActionBar
                    selectedCount={selectedForBulk.size}
                    totalCount={leads.length}
                    onSelectAll={onSelectAll}
                    isAllSelected={leads.length > 0 && selectedForBulk.size === leads.length}
                    onBulkRefresh={onBulkRefresh}
                    onBulkSendConnection={onBulkSendConnection}
                    onBulkSendDM={onBulkSendDM}
                    isBulkRefreshing={isBulkRefreshing}
                    isBulkSendingConnection={isBulkSendingConnection}
                    isBulkSendingDM={isBulkSendingDM}
                />
            </div>

            <div className="flex-1 overflow-y-auto">
                {loading ? (
                    <div className="flex justify-center p-10">
                        <Loader2 className="animate-spin text-blue-600" />
                    </div>
                ) : leads.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-400 p-8">
                        <Search className="w-12 h-12 mb-4 opacity-30" />
                        <p className="text-center">No leads found.<br />Start by searching for keywords above.</p>
                    </div>
                ) : (
                    leads.map((lead) => (
                        <LeadCard
                            key={lead.id}
                            lead={lead}
                            isSelected={selectedLeadId === lead.id}
                            isBulkSelected={selectedForBulk.has(lead.id)}
                            onSelect={onSelectLead}
                            onToggleBulk={onToggleBulk}
                        />
                    ))
                )}
            </div>

            {totalCount > pageLimit && (
                <div className="p-3 border-t border-gray-100 flex items-center justify-between">
                    <button
                        onClick={() => onPageChange(Math.max(0, currentPage - 1))}
                        disabled={currentPage === 0}
                        className="text-sm text-blue-600 hover:text-blue-800 disabled:text-gray-300"
                    >
                        ← Previous
                    </button>
                    <span className="text-xs text-gray-500">
                        Page {currentPage + 1} of {Math.ceil(totalCount / pageLimit)}
                    </span>
                    <button
                        onClick={() => onPageChange(currentPage + 1)}
                        disabled={(currentPage + 1) * pageLimit >= totalCount}
                        className="text-sm text-blue-600 hover:text-blue-800 disabled:text-gray-300"
                    >
                        Next →
                    </button>
                </div>
            )}
        </div>
    );
}
