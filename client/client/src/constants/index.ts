/**
 * Centralized Constants for the SDR Frontend Application.
 */

// ============================================
// API CONFIGURATION
// ============================================
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ============================================
// UI CONFIGURATION
// ============================================
export const TOAST_DURATION = 4000; // ms

// ============================================
// PAGINATION & LIMITS
// ============================================
export const DEFAULT_PAGE_LIMIT = 50;
export const MAX_BULK_SELECT_LIMIT = 100;

// ============================================
// EMAIL CONTEXT / THEMES (Colors)
// ============================================
export const EMAIL_CARD_COLORS = {
    blue: "border-l-blue-500",
    purple: "border-l-purple-500",
    orange: "border-l-orange-500"
} as const;

export type EmailCardColor = keyof typeof EMAIL_CARD_COLORS;
