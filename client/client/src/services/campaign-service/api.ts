import { API_BASE_URL } from "../../constants";
import { CampaignLeadsResponse, Lead, SequencePayload } from "../../types/types";

// 1. Fetch Campaign Leads (All Verified Leads)
export const fetchLeads = async (): Promise<CampaignLeadsResponse> => {
    // Calls the default "/" endpoint which returns all verified leads + incomplete count
    const res = await fetch(`${API_BASE_URL}/api/v1/leads/`);
    if (!res.ok) throw new Error('Failed to fetch leads');
    return res.json();
};

export const enrichLead = async (id: number) => {
    // Calls the endpoint: POST /api/v1/enrichment/{id}/enrich
    const res = await fetch(`${API_BASE_URL}/api/v1/enrichment/${id}/enrich`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });

    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Enrichment failed');
    }

    return res.json();
};

// 2. NEW: Fetch Enrichment Leads (Missing Data)
export const fetchEnrichmentLeads = async (): Promise<Lead[]> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/leads/enrichment`);
    if (!res.ok) throw new Error('Failed to fetch enrichment leads');
    return res.json();
};

export const fetchLeadDetails = async (id: number): Promise<Lead> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/leads/${id}`);
    if (!res.ok) throw new Error('Failed to fetch lead details');
    return res.json();
};

export const sendEmailMock = async (id: number, templateId: number, bodyContent: string) => {
    const res = await fetch(`${API_BASE_URL}/api/v1/leads/${id}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            template_id: templateId,
            email_body: bodyContent
        })
    });
    return res.json();
};

export const sendSequenceToInstantly = async (id: number, payload: SequencePayload) => {
    const res = await fetch(`${API_BASE_URL}/api/v1/leads/${id}/push-sequence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    return res.json();
};


// ============================================
// BULK OPERATIONS (NEW)
// ============================================

import { BulkCheckResponse, BulkPushResponse } from "../../types/types";

/**
 * Pre-flight check before bulk push.
 * Returns categorized lead IDs: ready, needs_enrichment, invalid_email, already_sent
 */
export const bulkCheckEligibility = async (leadIds: number[]): Promise<BulkCheckResponse> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/leads/bulk-check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_ids: leadIds })
    });

    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Bulk check failed');
    }

    return res.json();
};

/**
 * Push multiple leads to Instantly in a single API call.
 * Returns success metrics and lists of skipped leads.
 */
export const bulkPushToInstantly = async (leadIds: number[]): Promise<BulkPushResponse> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/leads/bulk-push`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_ids: leadIds })
    });

    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Bulk push failed');
    }

    return res.json();
};