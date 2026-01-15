/**
 * LinkedIn Signal Outreach API Service
 * Handles all API calls for LinkedIn keyword search and lead management.
 */
import { API_BASE_URL } from "../../constants";
import {
    LinkedInLeadDetail,
    LinkedInLeadsResponse,
    LinkedInSearchRequest,
    LinkedInSearchResponse
} from "../../types/types";


// ============================================
// SEARCH ENDPOINT
// ============================================

/**
 * Search LinkedIn posts by keywords.
 * Calls Apify, analyzes posts with AI, saves leads to DB.
 */
export const searchLinkedInPosts = async (
    request: LinkedInSearchRequest
): Promise<LinkedInSearchResponse> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/linkedin/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
    });

    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'LinkedIn search failed');
    }

    return res.json();
};


// ============================================
// LEADS ENDPOINTS
// ============================================

/**
 * Fetch all LinkedIn leads with optional keyword filter and pagination.
 */
export const fetchLinkedInLeads = async (
    keyword?: string,
    skip: number = 0,
    limit: number = 50
): Promise<LinkedInLeadsResponse> => {
    let url = `${API_BASE_URL}/api/v1/linkedin/leads?skip=${skip}&limit=${limit}`;

    if (keyword) {
        url += `&keyword=${encodeURIComponent(keyword)}`;
    }

    const res = await fetch(url);

    if (!res.ok) {
        throw new Error('Failed to fetch LinkedIn leads');
    }

    return res.json();
};

/**
 * Fetch single LinkedIn lead details (includes DM and full post data).
 */
export const fetchLinkedInLeadDetail = async (
    leadId: number
): Promise<LinkedInLeadDetail> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/linkedin/leads/${leadId}`);

    if (!res.ok) {
        throw new Error('Failed to fetch lead details');
    }

    return res.json();
};


// ============================================
// UTILITY ENDPOINTS
// ============================================

/**
 * Get list of unique search keywords for filter dropdown.
 */
export const fetchAvailableKeywords = async (): Promise<string[]> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/linkedin/keywords`);

    if (!res.ok) {
        return [];
    }

    const data = await res.json();
    return data.keywords || [];
};


// ============================================
// REFRESH ANALYSIS ENDPOINTS
// ============================================

interface RefreshResponse {
    success: boolean;
    message: string;
    lead_id?: number;
    hiring_signal?: boolean;
    hiring_roles?: string;
    linkedin_dm?: string;
}

interface BulkRefreshResponse {
    success: boolean;
    message: string;
    success_count: number;
    failed_count: number;
    errors: Array<{ lead_id: number; error: string }>;
}

/**
 * Refresh AI analysis for a single lead using existing post_data.
 * No re-scraping - uses cached post content.
 */
export const refreshLeadAnalysis = async (leadId: number): Promise<RefreshResponse> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/linkedin/leads/${leadId}/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });

    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Refresh failed');
    }

    return res.json();
};

/**
 * Bulk refresh AI analysis for multiple leads.
 * NOTE: On FREE tier, this will be slow (~13s per lead).
 */
export const bulkRefreshLeads = async (leadIds: number[]): Promise<BulkRefreshResponse> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/linkedin/leads/bulk-refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_ids: leadIds })
    });

    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Bulk refresh failed');
    }

    return res.json();
};

