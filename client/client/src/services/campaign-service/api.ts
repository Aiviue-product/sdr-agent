import { Lead, SequencePayload } from "../../types/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

// 1. Fetch Campaign Leads (Ready for Outreach)
export const fetchLeads = async (): Promise<Lead[]> => {
    // Calls the default "/" endpoint which now filters by lead_stage='campaign'
    const res = await fetch(`${API_BASE_URL}/api/v1/leads/`);
    if (!res.ok) throw new Error('Failed to fetch leads');
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