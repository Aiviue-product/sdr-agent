import { useEffect } from 'react';
import ActivityModal from '../components/linkedin/ActivityModal';
import LeadDetailPanel from '../components/linkedin/LeadDetailPanel';
import LeadsList from '../components/linkedin/LeadsList';
import LinkedInSearchHeader from '../components/linkedin/LinkedInSearchHeader';
import ErrorBoundary from '../components/shared/ErrorBoundary';

import {
    useActivityModal,
    useBulkActions,
    useLeadDetail,
    useLinkedInLeads,
    useLinkedInSearch,
    useRateLimits
} from '../hooks';


export default function LinkedInSignalsPage() {
    // --- HOOKS ---

    // 1. Rate Limits
    const { rateLimits, loadRateLimits } = useRateLimits();

    // 2. Lead List (depends on filter/page)
    const {
        leads,
        loading: loadingList,
        totalCount,
        currentPage,
        availableKeywords,
        selectedKeywordFilter,
        loadLeads,
        setCurrentPage,
        setSelectedKeywordFilter,
        refreshLeadsList,
        pageLimit
    } = useLinkedInLeads();

    // 3. Lead Detail & Actions
    const {
        selectedLeadId,
        selectedLeadDetail,
        loadingDetail,
        isRefreshing,
        isSendingDM,
        isSendingConnection,
        setSelectedLeadId,
        handleRefreshAnalysis,
        handleSendDM,
        handleSendConnection,
        copyDmToClipboard,
        openLinkedInProfile
    } = useLeadDetail({
        onActionCompleted: () => {
            refreshLeadsList();
            loadRateLimits();
        }
    });

    // 4. Bulk Actions
    const {
        selectedForBulk,
        isBulkRefreshing,
        isBulkSendingDM,
        isBulkSendingConnection,
        toggleBulkSelection,
        clearBulkSelection,
        handleBulkRefresh,
        handleBulkSendDM,
        handleBulkSendConnection
    } = useBulkActions({
        onComplete: () => {
            refreshLeadsList();
            clearBulkSelection();
            if (selectedLeadId) {
                // Refresh detail if selected lead was part of bulk
                // (Hook handleLeadDetail effect handles auto-reload when ID changes, 
                // but if ID didn't change we need manual reload)
                // Actually loadLeadDetail(id) is exposed if needed.
            }
            loadRateLimits();
        }
    });

    // 5. Search
    const {
        searchKeywords,
        dateFilter,
        postsPerKeyword,
        isSearching,
        setSearchKeywords,
        setDateFilter,
        setPostsPerKeyword,
        handleSearch
    } = useLinkedInSearch({
        onSearchSuccess: () => {
            // Reset to first page and show all keywords
            // Don't call loadLeads() here - the useEffect will handle it
            // when selectedKeywordFilter changes (avoids stale closure issue)
            setCurrentPage(0);
            setSelectedKeywordFilter('');
        }
    });

    // 6. Activity Modal
    const {
        showActivityModal,
        activeActivityLeadId,
        activeActivityLeadName,
        activities,
        loadingActivities,
        activityPage,
        hasMoreActivities,
        openActivityModal,
        closeActivityModal,
        loadMoreActivities
    } = useActivityModal();

    // --- EFFECTS ---

    // Load leads on mount and when filters change
    useEffect(() => {
        loadLeads();
    }, [loadLeads]);

    // Auto-select first lead if none selected
    useEffect(() => {
        if (leads.length > 0 && !selectedLeadId) {
            setSelectedLeadId(leads[0].id);
        }
    }, [leads, selectedLeadId, setSelectedLeadId]);

    // Coordination handlers
    const selectAllLeads = () => {
        if (selectedForBulk.size === leads.length && leads.length > 0) {
            clearBulkSelection();
        } else {
            leads.forEach(l => {
                if (!selectedForBulk.has(l.id)) {
                    toggleBulkSelection(l.id);
                }
            });
        }
    };

    return (
        <div className="flex flex-col h-screen bg-gray-50 font-sans relative">

            {/* --- SEARCH BAR HEADER --- */}
            <ErrorBoundary name="SearchHeader">
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
            </ErrorBoundary>

            <div className="flex flex-1 overflow-hidden">
                {/* --- LEFT SIDEBAR: LEADS LIST --- */}
                <ErrorBoundary name="LeadsList">
                    <LeadsList
                        leads={leads}
                        loading={loadingList}
                        selectedLeadId={selectedLeadId}
                        onSelectLead={setSelectedLeadId}
                        availableKeywords={availableKeywords}
                        selectedKeywordFilter={selectedKeywordFilter}
                        onKeywordFilterChange={setSelectedKeywordFilter}
                        totalCount={totalCount}
                        currentPage={currentPage}
                        onPageChange={setCurrentPage}
                        pageLimit={pageLimit}
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
                </ErrorBoundary>

                {/* --- RIGHT PANEL: LEAD DETAILS --- */}
                <ErrorBoundary name="LeadDetailPanel">
                    <LeadDetailPanel
                        leadDetail={selectedLeadDetail}
                        loading={loadingDetail}
                        onRefresh={handleRefreshAnalysis}
                        onSendConnection={() => handleSendConnection()}
                        onSendDM={() => handleSendDM()}
                        onOpenActivity={(id, name) => openActivityModal(id, name)}
                        onOpenProfile={openLinkedInProfile}
                        onCopyDm={copyDmToClipboard}
                        isRefreshing={isRefreshing}
                        isSendingConnection={isSendingConnection}
                        isSendingDM={isSendingDM}
                    />
                </ErrorBoundary>
            </div>

            {/* --- ACTIVITY MODAL --- */}
            <ErrorBoundary name="ActivityModal">
                <ActivityModal
                    isOpen={showActivityModal}
                    onClose={closeActivityModal}
                    activities={activities}
                    loading={loadingActivities}
                    hasMore={hasMoreActivities}
                    currentPage={activityPage}
                    onLoadMore={loadMoreActivities}
                    leadName={activeActivityLeadName}
                />
            </ErrorBoundary>
        </div>
    );
}

