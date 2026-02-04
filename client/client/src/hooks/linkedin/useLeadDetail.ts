/**
 * useLeadDetail Hook
 * 
 * Manages the detailed view of a selected lead:
 * - Fetching full lead details
 * - Refreshing AI analysis
 * - Sending DMs and Connection requests
 * - Common Lead actions (copy DM, open profile)
 * - Polling for DM generation status updates
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import {
    fetchLinkedInLeadDetail,
    refreshLeadAnalysis,
    sendConnectionRequest,
    sendDM
} from '../../services/linkedin-service/api';
import { ApiError } from '../../types/email-outreach/types';
import { LinkedInLeadDetail } from '../../types/linkedin';

// Polling interval for checking DM generation status (5 seconds)
const DM_GENERATION_POLL_INTERVAL = 5000;

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
    isPollingDmStatus: boolean;

    // Actions
    setSelectedLeadId: (id: number | null) => void;
    loadLeadDetail: (id: number, silent?: boolean) => Promise<LinkedInLeadDetail | null>;
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
    const [isPollingDmStatus, setIsPollingDmStatus] = useState(false);

    // Action states
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [isSendingDM, setIsSendingDM] = useState(false);
    const [isSendingConnection, setIsSendingConnection] = useState(false);

    // Ref for polling interval
    const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

    const loadLeadDetail = useCallback(async (id: number, silent = false) => {
        if (!silent) {
            setLoadingDetail(true);
        }
        try {
            const data = await fetchLinkedInLeadDetail(id);
            setSelectedLeadDetail(data);
            return data;
        } catch (err) {
            console.error('Failed to load lead details:', err);
            if (!silent) {
                toast.error('Failed to load lead details');
            }
            return null;
        } finally {
            if (!silent) {
                setLoadingDetail(false);
            }
        }
    }, []);

    // Stop polling
    const stopPolling = useCallback(() => {
        if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
        }
        setIsPollingDmStatus(false);
    }, []);

    // Start polling for DM generation status
    const startPolling = useCallback((leadId: number) => {
        // Don't start if already polling
        if (pollingIntervalRef.current) return;

        setIsPollingDmStatus(true);
        console.log(`🔄 Starting DM status polling for lead ${leadId}`);

        pollingIntervalRef.current = setInterval(async () => {
            const data = await loadLeadDetail(leadId, true); // Silent refresh
            
            if (data) {
                // Stop polling if status is no longer pending
                if (data.dm_generation_status !== 'pending') {
                    console.log(`✅ DM generation complete for lead ${leadId}: ${data.dm_generation_status}`);
                    stopPolling();
                    
                    // Show toast if DM was generated
                    if (data.dm_generation_status === 'generated' && data.linkedin_dm) {
                        toast.success('DM generated successfully!');
                    }
                    
                    // IMPORTANT: Refresh the leads list to update hiring signals
                    // This syncs the left panel (leads list) with the updated data
                    options?.onActionCompleted?.();
                }
            }
        }, DM_GENERATION_POLL_INTERVAL);
    }, [loadLeadDetail, stopPolling, options]);

    // Effect to auto-load detail when ID changes
    useEffect(() => {
        if (selectedLeadId) {
            loadLeadDetail(selectedLeadId);
        } else {
            setSelectedLeadDetail(null);
            stopPolling();
        }
    }, [selectedLeadId, loadLeadDetail, stopPolling]);

    // Effect to start/stop polling based on dm_generation_status
    // We intentionally only depend on dm_generation_status, not the whole selectedLeadDetail object
    // to avoid unnecessary polling restarts on other detail changes
    useEffect(() => {
        if (selectedLeadDetail && selectedLeadId) {
            if (selectedLeadDetail.dm_generation_status === 'pending') {
                startPolling(selectedLeadId);
            } else {
                stopPolling();
            }
        }

        // Cleanup on unmount
        return () => {
            stopPolling();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedLeadDetail?.dm_generation_status, selectedLeadId, startPolling, stopPolling]);

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
        isPollingDmStatus,
        setSelectedLeadId,
        loadLeadDetail,
        handleRefreshAnalysis,
        handleSendDM,
        handleSendConnection,
        copyDmToClipboard,
        openLinkedInProfile
    };
}
