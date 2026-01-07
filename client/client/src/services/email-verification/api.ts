// src/services/api.ts
import { API_BASE_URL } from "../../constants";

const API_URL = `${API_BASE_URL}/api/v1`;



// CHANGE 1: Return type is now Promise<Blob>, not void
export const verifyLeads = async (
    file: File,
    mode: 'individual' | 'bulk'
): Promise<Blob> => {
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

        return await response.blob();

    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
};