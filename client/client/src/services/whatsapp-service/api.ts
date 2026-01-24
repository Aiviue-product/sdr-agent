/**
 * WhatsApp Outreach API Service
 * Handles all API calls for WhatsApp messaging via WATI.
 */
import { API_BASE_URL } from "../../constants";
import {
    BulkEligibilityResponse,
    BulkSendWhatsAppRequest,
    BulkSendWhatsAppResponse,
    ConversationResponse,
    CreateLeadRequest,
    ImportResponse,
    SendWhatsAppRequest,
    SendWhatsAppResponse,
    TemplatesResponse,
    UpdateLeadRequest,
    WhatsAppActivitiesResponse,
    WhatsAppConfigStatus,
    WhatsAppLeadDetail,
    WhatsAppLeadsResponse
} from "../../types/whatsapp";

const WHATSAPP_API = `${API_BASE_URL}/api/v1/whatsapp`;

// ============================================
// CONFIGURATION
// ============================================

/**
 * Check if WATI is properly configured.
 */
export const getWhatsAppConfig = async (): Promise<WhatsAppConfigStatus> => {
    const res = await fetch(`${WHATSAPP_API}/config`);

    if (!res.ok) {
        throw new Error('Failed to get WhatsApp config');
    }

    return res.json();
};

// ============================================
// TEMPLATES
// ============================================

/**
 * Get all approved WhatsApp templates.
 */
export const getTemplates = async (): Promise<TemplatesResponse> => {
    const res = await fetch(`${WHATSAPP_API}/templates`);

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to fetch templates');
    }

    return res.json();
};

// ============================================
// LEADS
// ============================================

/**
 * Fetch all WhatsApp leads with pagination and filters.
 */
export const fetchWhatsAppLeads = async (
    skip: number = 0,
    limit: number = 50,
    source?: string,
    isSent?: boolean
): Promise<WhatsAppLeadsResponse> => {
    let url = `${WHATSAPP_API}/leads?skip=${skip}&limit=${limit}`;

    if (source) {
        url += `&source=${encodeURIComponent(source)}`;
    }
    if (isSent !== undefined) {
        url += `&is_sent=${isSent}`;
    }

    const res = await fetch(url);

    if (!res.ok) {
        throw new Error('Failed to fetch WhatsApp leads');
    }

    return res.json();
};

/**
 * Fetch single lead details.
 */
export const fetchWhatsAppLeadDetail = async (leadId: number): Promise<WhatsAppLeadDetail> => {
    const res = await fetch(`${WHATSAPP_API}/leads/${leadId}`);

    if (!res.ok) {
        throw new Error('Failed to fetch lead details');
    }

    return res.json();
};

/**
 * Create a new WhatsApp lead.
 */
export const createWhatsAppLead = async (data: CreateLeadRequest): Promise<WhatsAppLeadDetail> => {
    const res = await fetch(`${WHATSAPP_API}/leads`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to create lead');
    }

    return res.json();
};

/**
 * Update a WhatsApp lead.
 */
export const updateWhatsAppLead = async (leadId: number, data: UpdateLeadRequest): Promise<WhatsAppLeadDetail> => {
    const res = await fetch(`${WHATSAPP_API}/leads/${leadId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to update lead');
    }

    return res.json();
};

/**
 * Delete a WhatsApp lead.
 */
export const deleteWhatsAppLead = async (leadId: number): Promise<{ success: boolean }> => {
    const res = await fetch(`${WHATSAPP_API}/leads/${leadId}`, {
        method: 'DELETE'
    });

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to delete lead');
    }

    return res.json();
};

// ============================================
// MESSAGING
// ============================================

/**
 * Send WhatsApp message to a single lead.
 */
export const sendWhatsApp = async (
    leadId: number,
    request: SendWhatsAppRequest
): Promise<SendWhatsAppResponse> => {
    const res = await fetch(`${WHATSAPP_API}/leads/${leadId}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
    });

    // Return response even if not success (contains error info)
    return res.json();
};

/**
 * Get message history for a lead.
 */
export const getConversation = async (
    leadId: number,
    skip: number = 0,
    limit: number = 50
): Promise<ConversationResponse> => {
    const res = await fetch(
        `${WHATSAPP_API}/leads/${leadId}/messages?skip=${skip}&limit=${limit}`
    );

    if (!res.ok) {
        throw new Error('Failed to fetch messages');
    }

    return res.json();
};

/**
 * Sync message status from WATI.
 */
export const syncMessageStatus = async (leadId: number): Promise<{ success: boolean; status?: string }> => {
    const res = await fetch(`${WHATSAPP_API}/leads/${leadId}/sync-status`, {
        method: 'POST'
    });

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to sync status');
    }

    return res.json();
};

// ============================================
// BULK OPERATIONS
// ============================================

/**
 * Check which leads are eligible for bulk send.
 */
export const checkBulkEligibility = async (
    request: BulkSendWhatsAppRequest
): Promise<BulkEligibilityResponse> => {
    const res = await fetch(`${WHATSAPP_API}/bulk/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
    });

    if (!res.ok) {
        throw new Error('Failed to check eligibility');
    }

    return res.json();
};

/**
 * Bulk send WhatsApp messages.
 */
export const bulkSendWhatsApp = async (
    request: BulkSendWhatsAppRequest
): Promise<BulkSendWhatsAppResponse> => {
    const res = await fetch(`${WHATSAPP_API}/bulk/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
    });

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Bulk send failed');
    }

    return res.json();
};

// ============================================
// IMPORT
// ============================================

/**
 * Import leads from email outreach module.
 */
export const importFromEmailLeads = async (): Promise<ImportResponse> => {
    const res = await fetch(`${WHATSAPP_API}/import/email-leads`, {
        method: 'POST'
    });

    if (!res.ok) {
        throw new Error('Failed to import leads');
    }

    return res.json();
};

/**
 * Import leads from LinkedIn outreach module.
 */
export const importFromLinkedInLeads = async (): Promise<ImportResponse> => {
    const res = await fetch(`${WHATSAPP_API}/import/linkedin-leads`, {
        method: 'POST'
    });

    if (!res.ok) {
        throw new Error('Failed to import leads');
    }

    return res.json();
};

// ============================================
// ACTIVITIES
// ============================================

/**
 * Get WhatsApp activity timeline.
 */
export const getWhatsAppActivities = async (params: {
    page?: number;
    limit?: number;
    activityType?: string;
    leadId?: number;
    globalOnly?: boolean;
} = {}): Promise<WhatsAppActivitiesResponse> => {
    const { page = 1, limit = 20, activityType, leadId, globalOnly } = params;
    let url = `${WHATSAPP_API}/activities?page=${page}&limit=${limit}`;

    if (activityType) {
        url += `&activity_type=${encodeURIComponent(activityType)}`;
    }
    if (leadId) {
        url += `&lead_id=${leadId}`;
    }
    if (globalOnly !== undefined) {
        url += `&global_only=${globalOnly}`;
    }

    const res = await fetch(url);

    if (!res.ok) {
        throw new Error('Failed to fetch activities');
    }

    return res.json();
};
