'use client';

import {
    ArrowLeft,
    Building2,
    ChevronRight,
    Copy,
    ExternalLink,
    Filter,
    Loader2,
    Mail,
    MessageCircle,
    Phone,
    RefreshCw,
    Rocket,
    Search,
    Send,
    User
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';

import {
    bulkRefreshLeads,
    fetchLinkedInLeadDetail,
    fetchLinkedInLeads,
    refreshLeadAnalysis,
    searchLinkedInPosts
} from '../services/linkedin-service/api';
import { ApiError, LinkedInLead, LinkedInLeadDetail, LinkedInSearchRequest } from '../types/types';


export default function LinkedInSignalsPage() {
    // --- STATE ---
    const [leads, setLeads] = useState<LinkedInLead[]>([]);
    const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
    const [selectedLeadDetail, setSelectedLeadDetail] = useState<LinkedInLeadDetail | null>(null);
    const [loadingList, setLoadingList] = useState(true);
    const [loadingDetail, setLoadingDetail] = useState(false);

    // Search form state
    const [searchKeywords, setSearchKeywords] = useState('');
    const [dateFilter, setDateFilter] = useState<'past-24h' | 'past-week' | 'past-month'>('past-week');
    const [postsPerKeyword, setPostsPerKeyword] = useState(10);
    const [isSearching, setIsSearching] = useState(false);

    // Filter state
    const [availableKeywords, setAvailableKeywords] = useState<string[]>([]);
    const [selectedKeywordFilter, setSelectedKeywordFilter] = useState<string>('');

    // Pagination
    const [totalCount, setTotalCount] = useState(0);
    const [currentPage, setCurrentPage] = useState(0);
    const PAGE_LIMIT = 50;

    // Bulk selection state
    const [selectedForBulk, setSelectedForBulk] = useState<Set<number>>(new Set());
    const [isBulkRefreshing, setIsBulkRefreshing] = useState(false);

    // --- LOAD DATA ON MOUNT ---
    useEffect(() => {
        loadLeads();
    }, [selectedKeywordFilter, currentPage]);

    // --- LOAD LEAD DETAILS ---
    useEffect(() => {
        if (selectedLeadId) {
            loadLeadDetail(selectedLeadId);
        }
    }, [selectedLeadId]);

    // --- API CALLS ---
    const loadLeads = async () => {
        setLoadingList(true);
        try {
            const response = await fetchLinkedInLeads(
                selectedKeywordFilter || undefined,
                currentPage * PAGE_LIMIT,
                PAGE_LIMIT
            );
            setLeads(response.leads);
            setTotalCount(response.total_count);
            setAvailableKeywords(response.available_keywords);

            // Auto-select first lead if none selected
            if (response.leads.length > 0 && !selectedLeadId) {
                setSelectedLeadId(response.leads[0].id);
            }
        } catch (err) {
            console.error(err);
            toast.error('Failed to load leads');
        } finally {
            setLoadingList(false);
        }
    };

    const loadLeadDetail = async (id: number) => {
        setLoadingDetail(true);
        try {
            const data = await fetchLinkedInLeadDetail(id);
            setSelectedLeadDetail(data);
        } catch (err) {
            console.error(err);
            toast.error('Failed to load lead details');
        } finally {
            setLoadingDetail(false);
        }
    };

    const handleSearch = async () => {
        if (!searchKeywords.trim()) {
            toast.error('Please enter at least one keyword');
            return;
        }

        setIsSearching(true);
        const keywords = searchKeywords.split(',').map(k => k.trim()).filter(k => k);

        const request: LinkedInSearchRequest = {
            keywords,
            date_filter: dateFilter,
            posts_per_keyword: postsPerKeyword
        };

        try {
            toast.loading('Searching LinkedIn...', { id: 'search' });
            const result = await searchLinkedInPosts(request);

            if (result.success) {
                toast.success(result.message, { id: 'search' });
                // Refresh leads list
                setCurrentPage(0);
                setSelectedKeywordFilter('');
                await loadLeads();
            } else {
                toast.error('Search failed', { id: 'search' });
            }
        } catch (error) {
            const apiError = error as ApiError;
            toast.error(apiError.message || 'Search failed', { id: 'search' });
        } finally {
            setIsSearching(false);
        }
    };

    const copyDmToClipboard = () => {
        if (selectedLeadDetail?.linkedin_dm) {
            navigator.clipboard.writeText(selectedLeadDetail.linkedin_dm);
            toast.success('DM copied to clipboard!');
        }
    };

    const openLinkedInProfile = () => {
        if (selectedLeadDetail?.linkedin_url) {
            window.open(selectedLeadDetail.linkedin_url, '_blank');
        }
    };

    const [isRefreshing, setIsRefreshing] = useState(false);

    const handleRefreshAnalysis = async () => {
        if (!selectedLeadId) return;

        setIsRefreshing(true);
        try {
            toast.loading('Refreshing AI analysis...', { id: 'refresh' });
            const result = await refreshLeadAnalysis(selectedLeadId);

            if (result.success) {
                toast.success(result.message, { id: 'refresh' });
                // Reload lead details and list
                await loadLeadDetail(selectedLeadId);
                await loadLeads();
            } else {
                toast.error('Refresh failed', { id: 'refresh' });
            }
        } catch (error) {
            const apiError = error as ApiError;
            toast.error(apiError.message || 'Refresh failed', { id: 'refresh' });
        } finally {
            setIsRefreshing(false);
        }
    };

    // --- BULK SELECTION FUNCTIONS ---
    const toggleBulkSelection = (leadId: number) => {
        setSelectedForBulk(prev => {
            const newSet = new Set(prev);
            if (newSet.has(leadId)) {
                newSet.delete(leadId);
            } else {
                newSet.add(leadId);
            }
            return newSet;
        });
    };

    const selectAllLeads = () => {
        if (selectedForBulk.size === leads.length) {
            // Deselect all
            setSelectedForBulk(new Set());
        } else {
            // Select all
            setSelectedForBulk(new Set(leads.map(l => l.id)));
        }
    };

    const handleBulkRefresh = async () => {
        if (selectedForBulk.size === 0) {
            toast.error('No leads selected');
            return;
        }

        const leadIds = Array.from(selectedForBulk);
        setIsBulkRefreshing(true);

        try {
            toast.loading(`Refreshing ${leadIds.length} leads... (this may take a while on free tier)`, { id: 'bulk-refresh' });
            const result = await bulkRefreshLeads(leadIds);

            if (result.success) {
                toast.success(result.message, { id: 'bulk-refresh' });
                // Clear selection and reload
                setSelectedForBulk(new Set());
                await loadLeads();
                if (selectedLeadId) {
                    await loadLeadDetail(selectedLeadId);
                }
            } else {
                toast.error('Bulk refresh failed', { id: 'bulk-refresh' });
            }
        } catch (error) {
            const apiError = error as ApiError;
            toast.error(apiError.message || 'Bulk refresh failed', { id: 'bulk-refresh' });
        } finally {
            setIsBulkRefreshing(false);
        }
    };

    // --- RENDER ---
    return (
        <div className="flex flex-col h-screen bg-gray-50 font-sans">

            {/* --- SEARCH BAR HEADER --- */}
            <div className="bg-white border-b border-pink-300 p-4 shadow-sm">
                <div className="max-w-6xl mx-auto">
                    <div className="flex items-center gap-4 mb-4">
                        <Link href="/" className="text-gray-500 hover:text-gray-800 flex items-center gap-1 text-xs font-bold transition-colors">
                            <ArrowLeft className="w-3 h-3" /> Back to Home
                        </Link>
                        <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                            <Search className="w-5 h-5 text-blue-600" />
                            LinkedIn Signal Search
                        </h1>
                    </div>

                    {/* Search Form */}
                    <div className="flex items-end gap-4 flex-wrap">
                        <div className="flex-1 min-w-[300px]">
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                                Keywords (comma-separated)
                            </label>
                            <input
                                type="text"
                                value={searchKeywords}
                                onChange={(e) => setSearchKeywords(e.target.value)}
                                placeholder="hiring software engineer, looking for developers"
                                className="w-full px-4 py-2 border border-pink-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-gray-900 placeholder:text-gray-400 bg-white"
                            />
                        </div>

                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                                Date Range
                            </label>
                            <select
                                value={dateFilter}
                                onChange={(e) => setDateFilter(e.target.value as typeof dateFilter)}
                                className="px-4 py-2 border border-pink-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white text-gray-900"
                            >
                                <option value="past-24h">Past 24 Hours</option>
                                <option value="past-week">Past Week</option>
                                <option value="past-month">Past Month</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                                Posts/Keyword
                            </label>
                            <input
                                type="number"
                                value={postsPerKeyword}
                                onChange={(e) => setPostsPerKeyword(parseInt(e.target.value) || 10)}
                                min={1}
                                max={50}
                                className="w-20 px-3 py-2 border border-pink-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-gray-900 bg-white"
                            />
                        </div>

                        <button
                            onClick={handleSearch}
                            disabled={isSearching}
                            className={`flex items-center gap-2 px-6 py-2 rounded-lg font-bold transition-all
                                ${isSearching
                                    ? 'bg-gray-200 text-gray-400 cursor-wait'
                                    : 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-200'
                                }`}
                        >
                            {isSearching ? (
                                <><Loader2 className="w-4 h-4 animate-spin" /> Searching...</>
                            ) : (
                                <><Search className="w-4 h-4" /> Search</>
                            )}
                        </button>
                    </div>
                </div>
            </div>

            <div className="flex flex-1 overflow-hidden">
                {/* --- LEFT SIDEBAR: LEADS LIST --- */}
                <div className="w-1/3 border-r border-pink-200 bg-white flex flex-col">
                    {/* Filter Bar */}
                    <div className="p-4 border-b border-pink-100">
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <Filter className="w-4 h-4 text-pink-600" />
                                <select
                                    value={selectedKeywordFilter}
                                    onChange={(e) => {
                                        setSelectedKeywordFilter(e.target.value);
                                        setCurrentPage(0);
                                    }}
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

                        {/* Bulk Selection Controls */}
                        <div className="flex items-center justify-between pt-2 border-t border-pink-50">
                            <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-600 hover:text-gray-800">
                                <input
                                    type="checkbox"
                                    checked={leads.length > 0 && selectedForBulk.size === leads.length}
                                    onChange={selectAllLeads}
                                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                Select All ({selectedForBulk.size}/{leads.length})
                            </label>

                            {selectedForBulk.size > 0 && (
                                <button
                                    onClick={handleBulkRefresh}
                                    disabled={isBulkRefreshing}
                                    className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg font-medium transition-colors
                                        ${isBulkRefreshing
                                            ? 'bg-pink-100 text-pink-400 cursor-wait'
                                            : 'bg-amber-500 text-white hover:bg-amber-600'
                                        }`}
                                >
                                    <RefreshCw className={`w-3.5 h-3.5 ${isBulkRefreshing ? 'animate-spin' : ''}`} />
                                    {isBulkRefreshing ? 'Refreshing...' : `Refresh ${selectedForBulk.size}`}
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Leads List */}
                    <div className="flex-1 overflow-y-auto">
                        {loadingList ? (
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
                                <div
                                    key={lead.id}
                                    onClick={() => setSelectedLeadId(lead.id)}
                                    className={`
                                        p-4 border-b border-gray-50 cursor-pointer transition-colors hover:bg-gray-50
                                        ${selectedLeadId === lead.id ? 'bg-blue-50 border-l-4 border-l-blue-600' : 'border-l-4 border-l-transparent'}
                                    `}
                                >
                                    <div className="flex items-start gap-3">
                                        {/* Checkbox for bulk selection */}
                                        <input
                                            type="checkbox"
                                            checked={selectedForBulk.has(lead.id)}
                                            onChange={(e) => {
                                                e.stopPropagation();
                                                toggleBulkSelection(lead.id);
                                            }}
                                            onClick={(e) => e.stopPropagation()}
                                            className="w-4 h-4 mt-3 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                                        />

                                        {/* Avatar/Icon */}
                                        <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0
                                            ${lead.is_company ? 'bg-purple-100' : 'bg-blue-100'}`}
                                        >
                                            {lead.is_company ? (
                                                <Building2 className="w-5 h-5 text-purple-600" />
                                            ) : (
                                                <User className="w-5 h-5 text-blue-600" />
                                            )}
                                        </div>

                                        <div className="flex-1 min-w-0">
                                            <h3 className={`font-semibold flex items-center gap-2 ${selectedLeadId === lead.id ? 'text-blue-900' : 'text-gray-900'}`}>
                                                <span className="truncate">{lead.full_name}</span>

                                                {/* Hiring Badge */}
                                                {lead.hiring_signal && (
                                                    <Rocket className="w-4 h-4 text-green-600 fill-green-100 flex-shrink-0" />
                                                )}

                                                {/* DM Sent Badge */}
                                                {lead.is_dm_sent && (
                                                    <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-medium flex-shrink-0">
                                                        Sent ✓
                                                    </span>
                                                )}
                                            </h3>

                                            <p className="text-sm text-gray-500 truncate mt-0.5">
                                                {lead.headline || lead.company_name || 'No headline'}
                                            </p>

                                            {/* Hiring Roles */}
                                            {lead.hiring_signal && lead.hiring_roles && (
                                                <p className="text-xs text-green-700 font-medium mt-1.5 bg-green-50 px-2 py-1 rounded w-fit max-w-full truncate border border-green-100">
                                                    🏢 {lead.hiring_roles}
                                                </p>
                                            )}
                                        </div>

                                        <ChevronRight className={`w-4 h-4 mt-3 flex-shrink-0 ${selectedLeadId === lead.id ? 'text-blue-500' : 'text-gray-300'}`} />
                                    </div>
                                </div>
                            ))
                        )}
                    </div>

                    {/* Pagination */}
                    {totalCount > PAGE_LIMIT && (
                        <div className="p-3 border-t border-gray-100 flex items-center justify-between">
                            <button
                                onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                                disabled={currentPage === 0}
                                className="text-sm text-blue-600 hover:text-blue-800 disabled:text-gray-300"
                            >
                                ← Previous
                            </button>
                            <span className="text-xs text-gray-500">
                                Page {currentPage + 1} of {Math.ceil(totalCount / PAGE_LIMIT)}
                            </span>
                            <button
                                onClick={() => setCurrentPage(p => p + 1)}
                                disabled={(currentPage + 1) * PAGE_LIMIT >= totalCount}
                                className="text-sm text-blue-600 hover:text-blue-800 disabled:text-gray-300"
                            >
                                Next →
                            </button>
                        </div>
                    )}
                </div>

                {/* --- RIGHT PANEL: LEAD DETAILS --- */}
                <div className="flex-1 flex flex-col overflow-hidden">
                    {loadingDetail ? (
                        <div className="flex-1 flex items-center justify-center">
                            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                        </div>
                    ) : !selectedLeadDetail ? (
                        <div className="flex-1 flex items-center justify-center text-gray-400">
                            <div className="text-center">
                                <MessageCircle className="w-12 h-12 mx-auto mb-4 opacity-30" />
                                <p>Select a lead to view details</p>
                            </div>
                        </div>
                    ) : (
                        <>
                            {/* Header */}
                            <div className="bg-white p-6 border-b border-pink-200 shadow-sm">
                                <div className="flex justify-between items-start">
                                    <div className="flex items-start gap-4">
                                        {/* Profile Image */}
                                        {selectedLeadDetail.profile_image_url ? (
                                            <img
                                                src={selectedLeadDetail.profile_image_url}
                                                alt={selectedLeadDetail.full_name}
                                                className="w-16 h-16 rounded-full object-cover border-2 border-gray-200"
                                            />
                                        ) : (
                                            <div className={`w-16 h-16 rounded-full flex items-center justify-center
                                                ${selectedLeadDetail.is_company ? 'bg-purple-100' : 'bg-blue-100'}`}
                                            >
                                                {selectedLeadDetail.is_company ? (
                                                    <Building2 className="w-8 h-8 text-purple-600" />
                                                ) : (
                                                    <User className="w-8 h-8 text-blue-600" />
                                                )}
                                            </div>
                                        )}

                                        <div>
                                            <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                                                {selectedLeadDetail.full_name}
                                                {selectedLeadDetail.hiring_signal && (
                                                    <span className="bg-green-100 text-green-900 text-xs px-2.5 py-0.5 rounded-full border border-green-200 flex items-center gap-1 font-medium">
                                                        <Rocket className="w-3 h-3" /> Hiring
                                                    </span>
                                                )}
                                            </h2>
                                            <p className="text-gray-600 mt-1">{selectedLeadDetail.headline}</p>
                                            {selectedLeadDetail.hiring_roles && (
                                                <p className="text-green-700 font-medium mt-2">
                                                    Looking for: {selectedLeadDetail.hiring_roles}
                                                </p>
                                            )}

                                            {/* Contact Information Bar */}
                                            {((selectedLeadDetail.ai_variables as any)?.contact_email ||
                                                (selectedLeadDetail.ai_variables as any)?.contact_phone ||
                                                (selectedLeadDetail.ai_variables as any)?.company_hiring) && (
                                                    <div className="flex flex-wrap gap-3 mt-4 pt-4 border-t border-gray-100/50">
                                                        {(selectedLeadDetail.ai_variables as any).company_hiring && (
                                                            <div className="flex items-center gap-1.5 text-sm text-gray-700 bg-blue-50/50 px-2.5 py-1 rounded-md border border-blue-100/30">
                                                                <Building2 className="w-3.5 h-3.5 text-blue-500" />
                                                                <span className="text-gray-500 text-[10px] uppercase font-bold tracking-tight">Company:</span>
                                                                <span className="font-semibold text-gray-800">{(selectedLeadDetail.ai_variables as any).company_hiring}</span>
                                                            </div>
                                                        )}
                                                        {(selectedLeadDetail.ai_variables as any).contact_email && (
                                                            <div className="flex items-center gap-1.5 text-sm text-gray-700 bg-purple-50/50 px-2.5 py-1 rounded-md border border-purple-100/30">
                                                                <Mail className="w-3.5 h-3.5 text-purple-500" />
                                                                <span className="text-gray-500 text-[10px] uppercase font-bold tracking-tight">Email:</span>
                                                                <span className="font-semibold text-gray-800">{(selectedLeadDetail.ai_variables as any).contact_email}</span>
                                                            </div>
                                                        )}
                                                        {(selectedLeadDetail.ai_variables as any).contact_phone && (
                                                            <div className="flex items-center gap-1.5 text-sm text-gray-700 bg-amber-50/50 px-2.5 py-1 rounded-md border border-amber-100/30">
                                                                <Phone className="w-3.5 h-3.5 text-amber-500" />
                                                                <span className="text-gray-500 text-[10px] uppercase font-bold tracking-tight">Phone:</span>
                                                                <span className="font-semibold text-gray-800">{(selectedLeadDetail.ai_variables as any).contact_phone}</span>
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                        </div>
                                    </div>

                                    {/* Action Buttons */}
                                    <div className="flex gap-2">
                                        <button
                                            onClick={openLinkedInProfile}
                                            className="flex items-center justify-center gap-1.5 px-4 py-2 text-sm bg-gradient-to-r from-pink-400/90 via-purple-400/90 to-indigo-400/90 text-white rounded-lg font-medium hover:from-pink-500 hover:via-purple-500 hover:to-indigo-500 transition-all shadow-sm hover:shadow-md whitespace-nowrap"
                                        >
                                            <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                                            Open LinkedIn
                                        </button>
                                        <button
                                            onClick={handleRefreshAnalysis}
                                            disabled={isRefreshing}
                                            className={`flex items-center justify-center gap-1.5 px-4 py-2 text-sm rounded-lg font-medium transition-all whitespace-nowrap
                                                ${isRefreshing
                                                    ? 'bg-gray-100 text-gray-400 cursor-wait'
                                                    : 'bg-gradient-to-r from-amber-400 to-orange-400 text-white hover:from-amber-500 hover:to-orange-500 shadow-sm hover:shadow-md'
                                                }`}
                                            title="Re-run AI analysis using existing post data"
                                        >
                                            <RefreshCw className={`w-3.5 h-3.5 flex-shrink-0 ${isRefreshing ? 'animate-spin' : ''}`} />
                                            {isRefreshing ? 'Refreshing...' : 'Refresh'}
                                        </button>
                                        <button
                                            disabled
                                            className="flex items-center justify-center gap-1.5 px-4 py-2 text-sm bg-gradient-to-r from-gray-50 to-gray-100 text-gray-400 rounded-lg font-medium cursor-not-allowed border border-gray-200 whitespace-nowrap"
                                            title="Coming soon"
                                        >
                                            <Send className="w-3.5 h-3.5 flex-shrink-0" />
                                            Send DM
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Scrollable Content */}
                            <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
                                <div className="max-w-3xl mx-auto space-y-6">

                                    {/* AI-Generated DM Card */}
                                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                                        <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-100 flex justify-between items-center">
                                            <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                                                <MessageCircle className="w-4 h-4 text-blue-600" />
                                                AI-Generated LinkedIn DM
                                            </h3>
                                            <button
                                                onClick={copyDmToClipboard}
                                                className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 font-medium"
                                            >
                                                <Copy className="w-4 h-4" />
                                                Copy
                                            </button>
                                        </div>
                                        <div className="p-6">
                                            <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                                                {selectedLeadDetail.linkedin_dm || 'No DM generated yet. Run a new search to generate DMs.'}
                                            </p>
                                            <p className="text-xs text-gray-400 mt-4">
                                                {selectedLeadDetail.linkedin_dm?.length || 0} / 400 characters
                                            </p>
                                        </div>
                                    </div>

                                    {/* Pain Points Card */}
                                    {selectedLeadDetail.pain_points && (
                                        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                                            <h4 className="font-medium text-gray-700 mb-2">💡 Identified Pain Points</h4>
                                            <p className="text-gray-600">{selectedLeadDetail.pain_points}</p>
                                        </div>
                                    )}

                                    {/* Post Data */}
                                    {selectedLeadDetail.post_data && selectedLeadDetail.post_data.length > 0 && (
                                        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                                            <div className="p-4 bg-gray-50 border-b border-gray-100">
                                                <h3 className="font-semibold text-gray-800">
                                                    📄 LinkedIn Posts ({selectedLeadDetail.post_data.length})
                                                </h3>
                                            </div>
                                            <div className="divide-y divide-gray-100">
                                                {selectedLeadDetail.post_data.map((post, idx) => (
                                                    <div key={post.activity_id || idx} className="p-4">
                                                        <p className="text-xs text-gray-400 mb-2">
                                                            {post.posted_at?.date || 'Unknown date'} • Keyword: {post.search_keyword || 'N/A'}
                                                        </p>
                                                        <p className="text-gray-600 text-sm whitespace-pre-wrap line-clamp-6">
                                                            {post.text || 'No text available'}
                                                        </p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Info Cards */}
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                                            <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Search Keyword</h4>
                                            <p className="font-medium text-gray-800">{selectedLeadDetail.search_keyword || 'N/A'}</p>
                                        </div>
                                        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                                            <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Lead Type</h4>
                                            <p className="font-medium text-gray-800">
                                                {selectedLeadDetail.is_company ? 'Company Page' : 'Individual'}
                                            </p>
                                        </div>
                                    </div>

                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
