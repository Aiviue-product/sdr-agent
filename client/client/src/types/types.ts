
export interface VerificationResponse {
    success: boolean;
    message?: string;
}


export interface Lead {
    id: number;
    first_name: string;
    last_name?: string;
    company_name: string;
    designation: string;
    mobile_number?: string;
    linkedin_url?: string;
    sector: string;
    email: string;
    verification_status: string;

    // Generated Emails
    email_1_subject?: string; // New
    email_1_body?: string;
    email_2_subject?: string; // New
    email_2_body?: string;
    email_3_subject?: string; // New
    email_3_body?: string;

    // --- NEW AI FIELDS ---
    hiring_signal?: boolean;      // True/False
    enrichment_status?: 'pending' | 'completed' | 'failed';
    ai_variables?: {              // The JSON object from Gemini
        hiring_roles?: string;
        key_competencies?: string;
        pain_points?: string;
        summary_hook?: string;
    };
}

export interface SequencePayload {
    email_1: string;
    email_2: string;
    email_3: string;
    email_1_subject?: string;
    email_2_subject?: string;
    email_3_subject?: string;
}