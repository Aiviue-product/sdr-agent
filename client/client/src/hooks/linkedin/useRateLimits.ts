/**
 * useRateLimits Hook
 * 
 * Fetches and manages LinkedIn outreach rate limits.
 */
import { useCallback, useEffect, useState } from 'react';
import { getRateLimits } from '../../services/linkedin-service/api';
import { RateLimitStatus } from '../../types/linkedin';

export function useRateLimits() {
    const [rateLimits, setRateLimits] = useState<RateLimitStatus | null>(null);
    const [loadingLimits, setLoadingLimits] = useState(false);

    const loadRateLimits = useCallback(async () => {
        setLoadingLimits(true);
        try {
            const limits = await getRateLimits();
            setRateLimits(limits);
        } catch (err) {
            console.error('Failed to load rate limits:', err);
        } finally {
            setLoadingLimits(false);
        }
    }, []);

    useEffect(() => {
        loadRateLimits();
    }, [loadRateLimits]);

    return {
        rateLimits,
        loadingLimits,
        loadRateLimits
    };
}
