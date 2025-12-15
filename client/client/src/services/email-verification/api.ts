// src/services/api.ts

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

const API_URL = `${API_BASE_URL}/api/v1`;

export interface VerificationResponse {
    success: boolean;
    message?: string;
}

export const verifyLeads = async (
    file: File,
    mode: 'individual' | 'bulk'
): Promise<void> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('verification_mode', mode);

    try {
        const response = await fetch(`${API_URL}/verify-leads/`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Verification failed');
        }

        // Handle File Download logic securely
        const blob = await response.blob();

        // Extract filename from headers if possible, else default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'verified_leads.xlsx';
        if (contentDisposition) {
            const match = contentDisposition.match(/filename="(.+?)"/);
            if (match && match[1]) filename = match[1];
        }

        // Trigger download
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
};