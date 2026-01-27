/**
 * useLinkedInLeads Hook
 * 
 * Manages the leads list state including:
 * - Fetching leads with pagination
 * - Filtering by keyword
 * - Available keywords for filter dropdown
 */
import { useCallback, useState } from 'react';
import toast from 'react-hot-toast';
import { fetchLinkedInLeads } from '../../services/linkedin-service/api';
import { LinkedInLead } from '../../types/linkedin';

const PAGE_LIMIT = 50;

interface UseLinkedInLeadsOptions {
    onFirstLeadLoaded?: (leadId: number) => void;
}

interface UseLinkedInLeadsReturn {
    // State
    leads: LinkedInLead[];
    loading: boolean;
    totalCount: number;
    currentPage: number;
    availableKeywords: string[];
    selectedKeywordFilter: string;

    // Actions
    loadLeads: () => Promise<void>;
    setCurrentPage: (page: number) => void;
    setSelectedKeywordFilter: (keyword: string) => void;
    refreshLeadsList: () => Promise<void>;

    // Constants
    pageLimit: number;
}

export function useLinkedInLeads(options?: UseLinkedInLeadsOptions): UseLinkedInLeadsReturn {
    const [leads, setLeads] = useState<LinkedInLead[]>([]);
    const [loading, setLoading] = useState(true);
    const [totalCount, setTotalCount] = useState(0);
    const [currentPage, setCurrentPage] = useState(0);
    const [availableKeywords, setAvailableKeywords] = useState<string[]>([]);
    const [selectedKeywordFilter, setSelectedKeywordFilter] = useState('');

    const loadLeads = useCallback(async () => {
        setLoading(true);
        try {
            const response = await fetchLinkedInLeads(
                selectedKeywordFilter || undefined,
                currentPage * PAGE_LIMIT,
                PAGE_LIMIT
            );

            setLeads(response.leads);
            setTotalCount(response.total_count);
            setAvailableKeywords(response.available_keywords);

            // Notify if first lead loaded (for auto-selection)
            if (response.leads.length > 0 && options?.onFirstLeadLoaded) {
                options.onFirstLeadLoaded(response.leads[0].id);
            }
        } catch (err) {
            console.error('Failed to load leads:', err);
            toast.error('Failed to load leads');
        } finally {
            setLoading(false);
        }
    }, [selectedKeywordFilter, currentPage, options?.onFirstLeadLoaded]);

    const refreshLeadsList = useCallback(async () => {
        // Reload leads without changing pagination
        await loadLeads();
    }, [loadLeads]);

    // Handle filter change - also reset pagination
    const handleSetKeywordFilter = useCallback((keyword: string) => {
        setSelectedKeywordFilter(keyword);
        setCurrentPage(0); // Reset to first page when filter changes
    }, []);

    return {
        leads,
        loading,
        totalCount,
        currentPage,
        availableKeywords,
        selectedKeywordFilter,
        loadLeads,
        setCurrentPage,
        setSelectedKeywordFilter: handleSetKeywordFilter,
        refreshLeadsList,
        pageLimit: PAGE_LIMIT,
    };
}
