/**
 * LinkedIn Signal Outreach API Service
 * Handles all API calls for LinkedIn keyword search and lead management.
 */
import { API_BASE_URL } from "../../constants";
import {
    ActivitiesResponse,
    BulkRefreshResponse,
    BulkSendResponse,
    LinkedInLeadDetail,
    LinkedInLeadsResponse,
    LinkedInSearchRequest,
    LinkedInSearchResponse,
    RateLimitStatus,
    RefreshResponse,
    SendConnectionResponse,
    SendDMResponse
} from "../../types/linkedin";


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


// ============================================
// UNIPILE DM ENDPOINTS
// ============================================



/**
 * Get current rate limit status for LinkedIn operations.
 */
export const getRateLimits = async (): Promise<RateLimitStatus> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/linkedin/dm/rate-limits`);

    if (!res.ok) {
        throw new Error('Failed to get rate limits');
    }

    return res.json();
};

/**
 * Send DM to a single lead.
 * If not connected, will return error suggesting to send connection first.
 */
export const sendDM = async (leadId: number, message?: string): Promise<SendDMResponse> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/linkedin/dm/leads/${leadId}/send-dm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
    });

    if (!res.ok && res.status !== 422) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to send DM');
    }

    return res.json();
};

/**
 * Send connection request to a lead.
 */
export const sendConnectionRequest = async (leadId: number, message?: string): Promise<SendConnectionResponse> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/linkedin/dm/leads/${leadId}/send-connection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
    });

    if (!res.ok && res.status !== 422) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to send connection');
    }

    return res.json();
};

/**
 * Bulk send DMs or connection requests to multiple leads.
 */
export const bulkSend = async (
    leadIds: number[],
    sendType: 'dm' | 'connection',
    message?: string
): Promise<BulkSendResponse> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/linkedin/dm/bulk-send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            lead_ids: leadIds,
            send_type: sendType,
            message
        })
    });

    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Bulk send failed');
    }

    return res.json();
};

/**
 * Get activity timeline with pagination.
 */
export const getActivities = async (
    page: number = 1,
    limit: number = 20,
    activityType?: string,
    leadId?: number
): Promise<ActivitiesResponse> => {
    let url = `${API_BASE_URL}/api/v1/linkedin/dm/activities?page=${page}&limit=${limit}`;

    if (activityType) {
        url += `&activity_type=${encodeURIComponent(activityType)}`;
    }
    if (leadId) {
        url += `&lead_id=${leadId}`;
    }

    const res = await fetch(url);

    if (!res.ok) {
        throw new Error('Failed to fetch activities');
    }

    return res.json();
};
