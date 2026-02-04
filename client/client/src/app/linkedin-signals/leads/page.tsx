"use client";

import { ArrowLeft, Building2, ChevronLeft, ChevronRight, Filter, Loader2, Rocket, Search, User } from 'lucide-react';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { fetchLinkedInLeads } from '../../../services/linkedin-service/api';
import { LinkedInLead } from '../../../types/linkedin';

const PAGE_LIMIT = 20;

export default function AllLeadsPage() {
    const [leads, setLeads] = useState<LinkedInLead[]>([]);
    const [loading, setLoading] = useState(true);
    const [totalCount, setTotalCount] = useState(0);
    const [currentPage, setCurrentPage] = useState(0);
    const [availableKeywords, setAvailableKeywords] = useState<string[]>([]);
    const [selectedKeyword, setSelectedKeyword] = useState('');

    const loadLeads = useCallback(async () => {
        setLoading(true);
        try {
            const response = await fetchLinkedInLeads(
                selectedKeyword || undefined,
                currentPage * PAGE_LIMIT,
                PAGE_LIMIT
            );
            setLeads(response.leads);
            setTotalCount(response.total_count);
            setAvailableKeywords(response.available_keywords);
        } catch (err) {
            console.error('Failed to load leads:', err);
            toast.error('Failed to load leads');
        } finally {
            setLoading(false);
        }
    }, [selectedKeyword, currentPage]);

    useEffect(() => {
        loadLeads();
    }, [loadLeads]);

    const totalPages = Math.ceil(totalCount / PAGE_LIMIT);

    const handleKeywordChange = (keyword: string) => {
        setSelectedKeyword(keyword);
        setCurrentPage(0); // Reset to first page
    };

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <div className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
                <div className="max-w-6xl mx-auto px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <Link
                                href="/linkedin-signals"
                                className="text-gray-500 hover:text-gray-800 flex items-center gap-1 text-sm font-medium transition-colors"
                            >
                                <ArrowLeft className="w-4 h-4" /> Back to Search
                            </Link>
                            <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
                                <User className="w-6 h-6 text-teal-600" />
                                All My Leads
                            </h1>
                            <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                                {totalCount} total
                            </span>
                        </div>

                        {/* Keyword Filter */}
                        <div className="flex items-center gap-2">
                            <Filter className="w-4 h-4 text-gray-400" />
                            <select
                                value={selectedKeyword}
                                onChange={(e) => handleKeywordChange(e.target.value)}
                                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none bg-white text-gray-700 text-sm"
                            >
                                <option value="">All Keywords</option>
                                {availableKeywords.map((kw) => (
                                    <option key={kw} value={kw}>{kw}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="max-w-6xl mx-auto px-6 py-6">
                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
                        <span className="ml-3 text-gray-600">Loading leads...</span>
                    </div>
                ) : leads.length === 0 ? (
                    <div className="text-center py-20">
                        <Search className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                        <h3 className="text-xl font-semibold text-gray-600 mb-2">No leads found</h3>
                        <p className="text-gray-500">
                            {selectedKeyword
                                ? `No leads found for "${selectedKeyword}". Try a different filter.`
                                : 'Start by searching for keywords to find leads.'}
                        </p>
                        <Link
                            href="/linkedin-signals"
                            className="inline-flex items-center gap-2 mt-4 px-6 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors"
                        >
                            <Search className="w-4 h-4" /> Search Leads
                        </Link>
                    </div>
                ) : (
                    <>
                        {/* Leads Grid */}
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                            {leads.map((lead) => (
                                <LeadGridCard key={lead.id} lead={lead} />
                            ))}
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="flex items-center justify-between mt-8 bg-white rounded-lg shadow-sm p-4 border border-gray-100">
                                <div className="text-sm text-gray-600">
                                    Showing {currentPage * PAGE_LIMIT + 1} - {Math.min((currentPage + 1) * PAGE_LIMIT, totalCount)} of {totalCount}
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                                        disabled={currentPage === 0}
                                        className="flex items-center gap-1 px-3 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        <ChevronLeft className="w-4 h-4" /> Previous
                                    </button>
                                    <span className="px-4 py-2 text-sm text-gray-600">
                                        Page {currentPage + 1} of {totalPages}
                                    </span>
                                    <button
                                        onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
                                        disabled={currentPage >= totalPages - 1}
                                        className="flex items-center gap-1 px-3 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        Next <ChevronRight className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}

// Grid card component for individual lead
function LeadGridCard({ lead }: { lead: LinkedInLead }) {
    const [imageError, setImageError] = useState(false);

    return (
        <Link
            href={`/linkedin-signals/leads/${lead.id}`}
            className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md hover:border-teal-200 transition-all group"
        >
            <div className="flex items-start gap-3">
                {/* Avatar */}
                <div className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden
                    ${lead.is_company ? 'bg-purple-100' : 'bg-blue-100'}`}
                >
                    {lead.profile_image_url && !imageError ? (
                        <img
                            src={lead.profile_image_url}
                            alt={lead.full_name}
                            className="w-full h-full object-cover"
                            referrerPolicy="no-referrer"
                            onError={() => setImageError(true)}
                        />
                    ) : lead.is_company ? (
                        <Building2 className="w-6 h-6 text-purple-600" />
                    ) : (
                        <User className="w-6 h-6 text-blue-600" />
                    )}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 group-hover:text-teal-700 transition-colors flex items-center gap-2">
                        <span className="truncate">{lead.full_name}</span>
                        {lead.hiring_signal && (
                            <Rocket className="w-4 h-4 text-green-600 fill-green-100 flex-shrink-0" />
                        )}
                    </h3>
                    <p className="text-sm text-gray-500 truncate mt-0.5">
                        {lead.headline || lead.company_name || 'No headline'}
                    </p>
                </div>
            </div>

            {/* Tags */}
            <div className="mt-3 flex flex-wrap gap-2">
                {lead.search_keyword && (
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                        {lead.search_keyword}
                    </span>
                )}
                {lead.connection_status === 'connected' && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded font-medium">
                        Connected
                    </span>
                )}
                {lead.connection_status === 'pending' && (
                    <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded font-medium">
                        Pending
                    </span>
                )}
                {lead.is_dm_sent && (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded font-medium">
                        DM Sent ✓
                    </span>
                )}
            </div>

            {/* Hiring Signal */}
            {lead.hiring_signal && lead.hiring_roles && (
                <p className="text-xs text-green-700 font-medium mt-2 bg-green-50 px-2 py-1.5 rounded border border-green-100 truncate">
                    🏢 {lead.hiring_roles}
                </p>
            )}
        </Link>
    );
}
