
export interface LinkedInLead {
    id: number;
    full_name: string;
    first_name?: string;
    last_name?: string;
    company_name?: string;
    is_company: boolean;
    linkedin_url: string;
    headline?: string;
    profile_image_url?: string;
    search_keyword?: string;
    hiring_signal: boolean;
    hiring_roles?: string;
    pain_points?: string;
    is_dm_sent: boolean;
    connection_status?: 'none' | 'pending' | 'connected' | 'rejected';
    dm_status?: 'not_sent' | 'sent' | 'replied';
    created_at?: string;
}

// DM Generation Status type
export type DmGenerationStatus = 'pending' | 'generated' | 'failed';

export interface LinkedInLeadDetail extends LinkedInLead {
    post_data?: Array<{
        activity_id: string;
        text: string;
        search_keyword?: string;
        posted_at?: { date?: string };
    }>;
    ai_variables?: Record<string, unknown>;
    linkedin_dm?: string;
    dm_sent_at?: string;
    updated_at?: string;
    // DM Generation (background processing)
    dm_generation_status?: DmGenerationStatus;
    dm_generation_started_at?: string;
}

export interface LinkedInSearchRequest {
    keywords: string[];
    date_filter: 'past-24h' | 'past-week' | 'past-month';
    posts_per_keyword: number;
}

export interface LinkedInSearchResponse {
    success: boolean;
    message: string;
    stats: {
        total_posts: number;
        unique_leads: number;
        keywords_searched: number;
        inserted_count: number;
        updated_count: number;
        skipped_count: number;
    };
}

export interface LinkedInLeadsResponse {
    leads: LinkedInLead[];
    total_count: number;
    skip: number;
    limit: number;
    available_keywords: string[];
}

export interface RefreshResponse {
    success: boolean;
    message: string;
    lead_id?: number;
    hiring_signal?: boolean;
    hiring_roles?: string;
    linkedin_dm?: string;
}

export interface BulkRefreshResponse {
    success: boolean;
    message: string;
    success_count: number;
    failed_count: number;
    errors: Array<{ lead_id: number; error: string }>;
}

export interface RateLimitStatus {
    connections_sent_today: number;
    connections_remaining: number;
    connections_limit: number;
    dms_sent_today: number;
    dms_remaining: number;
    dms_limit: number;
}

export interface SendDMResponse {
    success: boolean;
    message: string;
    lead_id: number;
    dm_status?: string;
    sent_at?: string;
    error?: string;
}

export interface SendConnectionResponse {
    success: boolean;
    message: string;
    lead_id: number;
    connection_status?: string;
    invitation_id?: string;
    sent_at?: string;
    error?: string;
}

export interface BulkSendResponse {
    success: boolean;
    total: number;
    successful: number;
    failed: number;
    results: Array<{
        lead_id: number;
        success: boolean;
        message: string;
        error?: string;
    }>;
}

export interface ActivityItem {
    id: number;
    lead_id: number;
    activity_type: string;
    message?: string;
    lead_name?: string;
    lead_linkedin_url?: string;
    created_at: string;
}

export interface ActivitiesResponse {
    activities: ActivityItem[];
    total_count: number;
    page: number;
    limit: number;
    has_more: boolean;
}
