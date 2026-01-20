/**
 * useLeadDetail Hook
 * 
 * Manages the detailed view of a selected lead:
 * - Fetching full lead details
 * - Refreshing AI analysis
 * - Sending DMs and Connection requests
 * - Common Lead actions (copy DM, open profile)
 */
import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import {
    fetchLinkedInLeadDetail,
    refreshLeadAnalysis,
    sendConnectionRequest,
    sendDM
} from '../../services/linkedin-service/api';
import { ApiError } from '../../types/email-outreach/types';
import { LinkedInLeadDetail } from '../../types/linkedin';

interface UseLeadDetailOptions {
    onActionCompleted?: () => void;
}

interface UseLeadDetailReturn {
    // State
    selectedLeadId: number | null;
    selectedLeadDetail: LinkedInLeadDetail | null;
    loadingDetail: boolean;
    isRefreshing: boolean;
    isSendingDM: boolean;
    isSendingConnection: boolean;

    // Actions
    setSelectedLeadId: (id: number | null) => void;
    loadLeadDetail: (id: number) => Promise<void>;
    handleRefreshAnalysis: () => Promise<void>;
    handleSendDM: (message?: string) => Promise<void>;
    handleSendConnection: (message?: string) => Promise<void>;
    copyDmToClipboard: () => void;
    openLinkedInProfile: () => void;
}

export function useLeadDetail(options?: UseLeadDetailOptions): UseLeadDetailReturn {
    const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
    const [selectedLeadDetail, setSelectedLeadDetail] = useState<LinkedInLeadDetail | null>(null);
    const [loadingDetail, setLoadingDetail] = useState(false);

    // Action states
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [isSendingDM, setIsSendingDM] = useState(false);
    const [isSendingConnection, setIsSendingConnection] = useState(false);

    const loadLeadDetail = useCallback(async (id: number) => {
        setLoadingDetail(true);
        try {
            const data = await fetchLinkedInLeadDetail(id);
            setSelectedLeadDetail(data);
        } catch (err) {
            console.error('Failed to load lead details:', err);
            toast.error('Failed to load lead details');
        } finally {
            setLoadingDetail(false);
        }
    }, []);

    // Effect to auto-load detail when ID changes
    useEffect(() => {
        if (selectedLeadId) {
            loadLeadDetail(selectedLeadId);
        } else {
            setSelectedLeadDetail(null);
        }
    }, [selectedLeadId, loadLeadDetail]);

    const handleRefreshAnalysis = useCallback(async () => {
        if (!selectedLeadId) return;

        setIsRefreshing(true);
        try {
            toast.loading('Refreshing AI analysis...', { id: 'refresh' });
            const result = await refreshLeadAnalysis(selectedLeadId);

            if (result.success) {
                toast.success(result.message, { id: 'refresh' });
                await loadLeadDetail(selectedLeadId);
                options?.onActionCompleted?.();
            } else {
                toast.error(result.message || 'Refresh failed', { id: 'refresh' });
            }
        } catch (error) {
            const apiError = error as ApiError;
            toast.error(apiError.message || 'Refresh failed', { id: 'refresh' });
        } finally {
            setIsRefreshing(false);
        }
    }, [selectedLeadId, loadLeadDetail, options]);

    const handleSendDM = useCallback(async (customMessage?: string) => {
        if (!selectedLeadId) return;

        setIsSendingDM(true);
        try {
            toast.loading('Sending DM...', { id: 'dm' });
            const result = await sendDM(selectedLeadId, customMessage);

            if (result.success) {
                toast.success('DM sent successfully!', { id: 'dm' });
                await loadLeadDetail(selectedLeadId);
                options?.onActionCompleted?.();
            } else {
                toast.error(result.error || 'Failed to send DM', { id: 'dm' });
            }
        } catch (error) {
            const apiError = error as ApiError;
            toast.error(apiError.message || 'Failed to send DM', { id: 'dm' });
        } finally {
            setIsSendingDM(false);
        }
    }, [selectedLeadId, loadLeadDetail, options]);

    const handleSendConnection = useCallback(async (customMessage?: string) => {
        if (!selectedLeadId) return;

        setIsSendingConnection(true);
        try {
            toast.loading('Sending connection...', { id: 'connection' });
            const result = await sendConnectionRequest(selectedLeadId, customMessage);

            if (result.success) {
                toast.success('Connection request sent!', { id: 'connection' });
                await loadLeadDetail(selectedLeadId);
                options?.onActionCompleted?.();
            } else {
                toast.error(result.error || 'Failed to send connection', { id: 'connection' });
            }
        } catch (error) {
            const apiError = error as ApiError;
            toast.error(apiError.message || 'Failed to send connection', { id: 'connection' });
        } finally {
            setIsSendingConnection(false);
        }
    }, [selectedLeadId, loadLeadDetail, options]);

    const copyDmToClipboard = useCallback(() => {
        if (selectedLeadDetail?.linkedin_dm) {
            navigator.clipboard.writeText(selectedLeadDetail.linkedin_dm);
            toast.success('DM copied to clipboard!');
        }
    }, [selectedLeadDetail]);

    const openLinkedInProfile = useCallback(() => {
        if (selectedLeadDetail?.linkedin_url) {
            window.open(selectedLeadDetail.linkedin_url, '_blank');
        }
    }, [selectedLeadDetail]);

    return {
        selectedLeadId,
        selectedLeadDetail,
        loadingDetail,
        isRefreshing,
        isSendingDM,
        isSendingConnection,
        setSelectedLeadId,
        loadLeadDetail,
        handleRefreshAnalysis,
        handleSendDM,
        handleSendConnection,
        copyDmToClipboard,
        openLinkedInProfile
    };
}
