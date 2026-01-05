const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export interface Lead {
    id: number;
    first_name: string;
    last_name?: string;
    company_name: string;
    designation: string;
    sector: string;
    email: string;
    verification_status: string;
    // Generated Emails
    email_1_body?: string;
    email_2_body?: string;
    email_3_body?: string;
}

export const fetchLeads = async (): Promise<Lead[]> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/leads/?status=valid`);
    if (!res.ok) throw new Error('Failed to fetch leads');
    return res.json();
};

export const fetchLeadDetails = async (id: number): Promise<Lead> => {
    const res = await fetch(`${API_BASE_URL}/api/v1/leads/${id}`);
    if (!res.ok) throw new Error('Failed to fetch lead details');
    return res.json();
};

// --- UPDATED SEND FUNCTION ---
export const sendEmailMock = async (id: number, templateId: number, bodyContent: string) => {
    const res = await fetch(`${API_BASE_URL}/api/v1/leads/${id}/send`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            template_id: templateId,
            email_body: bodyContent
        })
    });
    return res.json();
};





// Add this interface
interface SequencePayload {
    email_1: string;
    email_2: string;
    email_3: string;
}

// Add this function
export const sendSequenceToInstantly = async (id: number, payload: SequencePayload) => {
    const res = await fetch(`${API_BASE_URL}/api/v1/leads/${id}/push-sequence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    return res.json();
};