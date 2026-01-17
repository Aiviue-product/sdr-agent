'use client';


import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import ActivityModal from '../components/linkedin/ActivityModal';
import LeadDetailPanel from '../components/linkedin/LeadDetailPanel';
import LeadsList from '../components/linkedin/LeadsList';
import LinkedInSearchHeader from '../components/linkedin/LinkedInSearchHeader';

import {
    bulkRefreshLeads,
    bulkSend,
    fetchLinkedInLeadDetail,
    fetchLinkedInLeads,
    getActivities,
    getRateLimits,
    refreshLeadAnalysis,
    searchLinkedInPosts,
    sendConnectionRequest,
    sendDM
} from '../services/linkedin-service/api';
import { ActivityItem, LinkedInLead, LinkedInLeadDetail, LinkedInSearchRequest, RateLimitStatus } from '../types/linkedin';
import { ApiError } from '../types/types';


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
    const [isBulkSendingDM, setIsBulkSendingDM] = useState(false);
    const [isBulkSendingConnection, setIsBulkSendingConnection] = useState(false);

    // DM/Connection state
    const [isSendingDM, setIsSendingDM] = useState(false);
    const [isSendingConnection, setIsSendingConnection] = useState(false);
    const [rateLimits, setRateLimits] = useState<RateLimitStatus | null>(null);
    const [showActivityModal, setShowActivityModal] = useState(false);
    const [activeActivityLeadId, setActiveActivityLeadId] = useState<number | null>(null);
    const [activeActivityLeadName, setActiveActivityLeadName] = useState<string | undefined>(undefined);
    const [activities, setActivities] = useState<ActivityItem[]>([]);
    const [loadingActivities, setLoadingActivities] = useState(false);
    const [activityPage, setActivityPage] = useState(1);
    const [hasMoreActivities, setHasMoreActivities] = useState(false);

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
            setSelectedForBulk(new Set());
        } else {
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
            toast.loading(`Refreshing ${leadIds.length} leads...`, { id: 'bulk-refresh' });
            const result = await bulkRefreshLeads(leadIds);

            if (result.success) {
                toast.success(result.message, { id: 'bulk-refresh' });
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

    const handleBulkSendDM = async () => {
        const leadIds = Array.from(selectedForBulk);
        if (leadIds.length === 0) return;

        setIsBulkSendingDM(true);
        try {
            toast.loading(`Sending DMs to ${leadIds.length} leads...`, { id: 'bulk-dm' });
            const result = await bulkSend(leadIds, 'dm');

            if (result.success) {
                toast.success(`Sent ${result.successful} DMs (${result.failed} failed)`, { id: 'bulk-dm' });
                setSelectedForBulk(new Set());
                await loadLeads();
                await loadRateLimits();
            } else {
                toast.error(`Bulk DM failed: ${result.failed} failures`, { id: 'bulk-dm' });
            }
        } catch (error) {
            const apiError = error as ApiError;
            toast.error(apiError.message || 'Bulk DM failed', { id: 'bulk-dm' });
        } finally {
            setIsBulkSendingDM(false);
        }
    };

    const handleBulkSendConnection = async () => {
        const leadIds = Array.from(selectedForBulk);
        if (leadIds.length === 0) return;

        setIsBulkSendingConnection(true);
        try {
            toast.loading(`Sending connections to ${leadIds.length} leads...`, { id: 'bulk-connection' });
            const result = await bulkSend(leadIds, 'connection');

            if (result.success) {
                toast.success(`Sent ${result.successful} connections (${result.failed} failed)`, { id: 'bulk-connection' });
                setSelectedForBulk(new Set());
                await loadLeads();
                await loadRateLimits();
            } else {
                toast.error(`Bulk connection failed: ${result.failed} failures`, { id: 'bulk-connection' });
            }
        } catch (error) {
            const apiError = error as ApiError;
            toast.error(apiError.message || 'Bulk connection failed', { id: 'bulk-connection' });
        } finally {
            setIsBulkSendingConnection(false);
        }
    };

    const loadRateLimits = async () => {
        try {
            const limits = await getRateLimits();
            setRateLimits(limits);
        } catch (err) {
            console.error('Failed to load rate limits:', err);
        }
    };

    const loadActivities = async (page: number = 1, leadId?: number | null) => {
        setLoadingActivities(true);
        try {
            const response = await getActivities(page, 20, undefined, leadId || undefined);
            if (page === 1) {
                setActivities(response.activities);
            } else {
                setActivities(prev => [...prev, ...response.activities]);
            }
            setHasMoreActivities(response.has_more);
            setActivityPage(page);
        } catch (err) {
            console.error('Failed to load activities:', err);
            toast.error('Failed to load activities');
        } finally {
            setLoadingActivities(false);
        }
    };

    const handleSendDM = async () => {
        if (!selectedLeadId || !selectedLeadDetail) return;

        setIsSendingDM(true);
        try {
            toast.loading('Sending DM...', { id: 'send-dm' });
            const result = await sendDM(selectedLeadId);

            if (result.success) {
                toast.success(result.message, { id: 'send-dm' });
                await loadLeadDetail(selectedLeadId);
                await loadLeads();
                await loadRateLimits();
            } else {
                toast.error(result.error || result.message, { id: 'send-dm' });
            }
        } catch (error) {
            const apiError = error as ApiError;
            toast.error(apiError.message || 'Failed to send DM', { id: 'send-dm' });
        } finally {
            setIsSendingDM(false);
        }
    };

    const handleSendConnection = async () => {
        if (!selectedLeadId || !selectedLeadDetail) return;

        setIsSendingConnection(true);
        try {
            toast.loading('Sending connection request...', { id: 'send-connection' });
            const result = await sendConnectionRequest(selectedLeadId);

            if (result.success) {
                toast.success(result.message, { id: 'send-connection' });
                await loadLeadDetail(selectedLeadId);
                await loadLeads();
                await loadRateLimits();
            } else {
                toast.error(result.error || result.message, { id: 'send-connection' });
            }
        } catch (error) {
            const apiError = error as ApiError;
            toast.error(apiError.message || 'Failed to send connection', { id: 'send-connection' });
        } finally {
            setIsSendingConnection(false);
        }
    };

    const openActivityModal = async (leadId?: number, leadName?: string) => {
        // Clear stale data immediately so user sees loading state, not old data
        setActivities([]);
        setActivityPage(1);
        setHasMoreActivities(false);
        setActiveActivityLeadId(leadId || null);
        setActiveActivityLeadName(leadName);
        setShowActivityModal(true);
        await loadActivities(1, leadId);
    };

    useEffect(() => {
        loadRateLimits();
    }, []);

    return (
        <div className="flex flex-col h-screen bg-gray-50 font-sans relative">

            {/* --- SEARCH BAR HEADER --- */}
            <LinkedInSearchHeader
                searchKeywords={searchKeywords}
                onKeywordsChange={setSearchKeywords}
                dateFilter={dateFilter}
                onDateFilterChange={setDateFilter}
                postsPerKeyword={postsPerKeyword}
                onPostsPerKeywordChange={setPostsPerKeyword}
                onSearch={handleSearch}
                onOpenActivity={() => openActivityModal()}
                isSearching={isSearching}
            />

            <div className="flex flex-1 overflow-hidden">
                {/* --- LEFT SIDEBAR: LEADS LIST --- */}
                <LeadsList
                    leads={leads}
                    loading={loadingList}
                    selectedLeadId={selectedLeadId}
                    onSelectLead={setSelectedLeadId}
                    availableKeywords={availableKeywords}
                    selectedKeywordFilter={selectedKeywordFilter}
                    onKeywordFilterChange={(val) => {
                        setSelectedKeywordFilter(val);
                        setCurrentPage(0);
                    }}
                    totalCount={totalCount}
                    currentPage={currentPage}
                    onPageChange={setCurrentPage}
                    pageLimit={PAGE_LIMIT}
                    selectedForBulk={selectedForBulk}
                    onToggleBulk={toggleBulkSelection}
                    onSelectAll={selectAllLeads}
                    onBulkRefresh={handleBulkRefresh}
                    onBulkSendConnection={handleBulkSendConnection}
                    onBulkSendDM={handleBulkSendDM}
                    isBulkRefreshing={isBulkRefreshing}
                    isBulkSendingConnection={isBulkSendingConnection}
                    isBulkSendingDM={isBulkSendingDM}
                />

                {/* --- RIGHT PANEL: LEAD DETAILS --- */}
                <LeadDetailPanel
                    leadDetail={selectedLeadDetail}
                    loading={loadingDetail}
                    onRefresh={handleRefreshAnalysis}
                    onSendConnection={handleSendConnection}
                    onSendDM={handleSendDM}
                    onOpenActivity={openActivityModal}
                    onOpenProfile={openLinkedInProfile}
                    onCopyDm={copyDmToClipboard}
                    isRefreshing={isRefreshing}
                    isSendingConnection={isSendingConnection}
                    isSendingDM={isSendingDM}
                />
            </div>

            {/* --- ACTIVITY MODAL --- */}
            <ActivityModal
                isOpen={showActivityModal}
                onClose={() => {
                    setShowActivityModal(false);
                    setActiveActivityLeadId(null);
                    setActiveActivityLeadName(undefined);
                }}
                activities={activities}
                loading={loadingActivities}
                hasMore={hasMoreActivities}
                currentPage={activityPage}
                onLoadMore={() => loadActivities(activityPage + 1, activeActivityLeadId)}
                leadName={activeActivityLeadName}
            />
        </div>
    );
}