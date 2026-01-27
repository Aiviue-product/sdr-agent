
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
    email_1_subject?: string;
    email_1_body?: string;
    email_2_subject?: string;
    email_2_body?: string;
    email_3_subject?: string;
    email_3_body?: string;

    // --- AI FIELDS ---
    hiring_signal?: boolean;
    enrichment_status?: 'pending' | 'completed' | 'failed';
    ai_variables?: {
        hiring_roles?: string;
        key_competencies?: string;
        pain_points?: string;
        summary_hook?: string;
    };

    // --- BULK PUSH FIELDS ---
    is_sent?: boolean;
    sent_at?: string;
}

export interface CampaignLeadsResponse {
    leads: Lead[];
    incomplete_leads_count: number;
}


export interface SequencePayload {
    email_1: string;
    email_2: string;
    email_3: string;
    email_1_subject?: string;
    email_2_subject?: string;
    email_3_subject?: string;
}

// --- BULK OPERATIONS TYPES ---
export interface BulkCheckResponse {
    total: number;
    ready: number;
    needs_enrichment: number;
    invalid_email: number;
    already_sent: number;
    details: {
        ready: number[];
        needs_enrichment: number[];
        invalid_email: number[];
        already_sent: number[];
    };
}

export interface BulkPushResponse {
    success: boolean;
    message: string;
    total_selected: number;
    total_pushed: number;
    leads_uploaded: number;
    duplicated_in_instantly: number;
    skipped_needs_enrichment: number[];
    skipped_no_email: number[];
    skipped_already_sent: number[];
}

// --- EMAIL CARD COMPONENT TYPES ---
export type EmailCardColor = 'blue' | 'purple' | 'orange';

export interface EmailCardProps {
    title: string;
    subject?: string;
    body?: string;
    color: EmailCardColor;
    onSend: () => void;
    onSubjectChange: (text: string) => void;
    onBodyChange: (text: string) => void;
    onRegenerate?: () => void;
}

// --- API ERROR TYPE ---
export interface ApiError {
    message: string;
    detail?: string;
}

