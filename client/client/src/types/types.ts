
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
    email_1_body?: string;
    email_2_body?: string;
    email_3_body?: string;
}

// Add this interface
export interface SequencePayload {
    email_1: string;
    email_2: string;
    email_3: string;
}

