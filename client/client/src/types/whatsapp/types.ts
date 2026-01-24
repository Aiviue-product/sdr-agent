/**
 * WhatsApp Outreach Types
 * TypeScript interfaces for WhatsApp module.
 */

// ============================================
// LEAD TYPES
// ============================================

export interface WhatsAppLeadSummary {
    id: number;
    mobile_number: string;
    first_name: string;
    last_name?: string;
    full_name?: string;
    email?: string;
    company_name?: string;
    designation?: string;
    linkedin_url?: string;
    source?: string;
    is_wa_sent: boolean;
    last_delivery_status?: string;
    last_sent_at?: string;
    created_at?: string;
}

export interface WhatsAppLeadDetail extends WhatsAppLeadSummary {
    sector?: string;
    source_lead_id?: number;
    last_template_used?: string;
    last_failed_reason?: string;
    wati_contact_id?: string;
    wati_conversation_id?: string;
    updated_at?: string;
}

export interface WhatsAppLeadsResponse {
    leads: WhatsAppLeadSummary[];
    total_count: number;
    skip: number;
    limit: number;
}

// ============================================
// MESSAGE TYPES
// ============================================

export interface WhatsAppMessage {
    id: number;
    whatsapp_lead_id: number;
    direction: 'outbound' | 'inbound';
    template_name?: string;
    message_text: string;
    parameters?: Record<string, unknown>;
    status: string;
    failed_reason?: string;
    sent_at?: string;
    delivered_at?: string;
    read_at?: string;
    created_at: string;
}

export interface ConversationResponse {
    messages: WhatsAppMessage[];
    total_count: number;
    lead_id: number;
}

// ============================================
// TEMPLATE TYPES
// ============================================

export interface WhatsAppTemplate {
    id?: string;  // WATI uses MongoDB ObjectId (string)
    name: string;
    category?: string;
    body?: string;
    params: string[];
    has_header: boolean;
    has_buttons: boolean;
}

export interface TemplatesResponse {
    success: boolean;
    templates: WhatsAppTemplate[];
    total: number;
}

// ============================================
// SEND MESSAGE TYPES
// ============================================

export interface SendWhatsAppRequest {
    template_name: string;
    custom_params?: Record<string, string>;
    broadcast_name?: string;
}

export interface SendWhatsAppResponse {
    success: boolean;
    message: string;
    lead_id: number;
    phone_number?: string;
    template_name?: string;
    status?: string;
    error?: string;
}

export interface BulkSendWhatsAppRequest {
    lead_ids: number[];
    template_name: string;
    broadcast_name?: string;
}

export interface BulkSendWhatsAppResponse {
    success: boolean;
    broadcast_name: string;
    total: number;
    success_count: number;
    failed_count: number;
    results: Array<{
        lead_id: number;
        success: boolean;
        error?: string;
    }>;
}

export interface BulkEligibilityResponse {
    success: boolean;
    eligible: Array<{
        lead_id: number;
        phone_number: string;
        first_name: string;
    }>;
    eligible_count: number;
    ineligible: Array<{
        lead_id: number;
        reason: string;
    }>;
    ineligible_count: number;
    total_requested: number;
}

// ============================================
// ACTIVITY TYPES
// ============================================

export interface WhatsAppActivity {
    id: number;
    whatsapp_lead_id?: number;
    activity_type: string;
    title: string;
    description?: string;
    lead_name?: string;
    lead_mobile?: string;
    extra_data?: Record<string, unknown>;
    is_global: boolean;
    created_at: string;
}

export interface WhatsAppActivitiesResponse {
    activities: WhatsAppActivity[];
    total_count: number;
    page: number;
    limit: number;
    has_more: boolean;
}

// ============================================
// CONFIG & IMPORT TYPES
// ============================================

export interface WhatsAppConfigStatus {
    configured: boolean;
    endpoint?: string;
    channel?: string;
}

export interface ImportResponse {
    success: boolean;
    source: string;
    total_with_mobile: number;
    inserted: number;
    updated: number;
    skipped: number;
    errors: string[];
}

// ============================================
// CREATE/UPDATE LEAD TYPES
// ============================================

export interface CreateLeadRequest {
    mobile_number: string;
    first_name: string;
    last_name?: string;
    email?: string;
    company_name?: string;
    designation?: string;
    linkedin_url?: string;
    sector?: string;
}

export interface UpdateLeadRequest {
    first_name?: string;
    last_name?: string;
    email?: string;
    company_name?: string;
    designation?: string;
    linkedin_url?: string;
    sector?: string;
}
