/**
 * useLinkedInSearch Hook
 * 
 * Manages the search header state and operations:
 * - Search keywords, date filter, posts per keyword
 * - Triggering the search API
 */
import { useCallback, useState } from 'react';
import toast from 'react-hot-toast';
import { searchLinkedInPosts } from '../../services/linkedin-service/api';
import { ApiError } from '../../types/email-outreach/types';
import { LinkedInSearchRequest } from '../../types/linkedin';

interface UseLinkedInSearchOptions {
    onSearchSuccess?: (searchedKeywords: string) => void;
}

interface UseLinkedInSearchReturn {
    // State
    searchKeywords: string;
    dateFilter: 'past-24h' | 'past-week' | 'past-month';
    postsPerKeyword: number;
    isSearching: boolean;

    // Setters
    setSearchKeywords: (val: string) => void;
    setDateFilter: (val: 'past-24h' | 'past-week' | 'past-month') => void;
    setPostsPerKeyword: (val: number) => void;

    // Actions
    handleSearch: () => Promise<void>;
}

export function useLinkedInSearch(options?: UseLinkedInSearchOptions): UseLinkedInSearchReturn {
    const [searchKeywords, setSearchKeywords] = useState('');
    const [dateFilter, setDateFilter] = useState<'past-24h' | 'past-week' | 'past-month'>('past-week');
    const [postsPerKeyword, setPostsPerKeyword] = useState(10);
    const [isSearching, setIsSearching] = useState(false);

    const handleSearch = useCallback(async () => {
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
                if (options?.onSearchSuccess) {
                    // Pass the searched keywords so the list can filter by them
                    options.onSearchSuccess(searchKeywords);
                }
            } else {
                toast.error('Search failed', { id: 'search' });
            }
        } catch (error) {
            const apiError = error as ApiError;
            toast.error(apiError.message || 'Search failed', { id: 'search' });
        } finally {
            setIsSearching(false);
        }
    }, [searchKeywords, dateFilter, postsPerKeyword, options]);

    return {
        searchKeywords,
        dateFilter,
        postsPerKeyword,
        isSearching,
        setSearchKeywords,
        setDateFilter,
        setPostsPerKeyword,
        handleSearch
    };
}
