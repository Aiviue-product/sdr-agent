/**
 * useBulkActions Hook
 * 
 * Manages multi-selection and bulk operations for leads:
 * - Selecting/Deselecting leads
 * - Bulk refresh analysis
 * - Bulk send DMs and Connections
 */
import { useCallback, useState } from 'react';
import toast from 'react-hot-toast';
import { bulkRefreshLeads, bulkSend } from '../../services/linkedin-service/api';
import { ApiError } from '../../types/types';

interface UseBulkActionsOptions {
    onComplete?: () => void;
}

interface UseBulkActionsReturn {
    // State
    selectedForBulk: Set<number>;
    isBulkRefreshing: boolean;
    isBulkSendingDM: boolean;
    isBulkSendingConnection: boolean;

    // Actions
    toggleBulkSelection: (leadId: number) => void;
    clearBulkSelection: () => void;
    handleBulkRefresh: () => Promise<void>;
    handleBulkSendDM: () => Promise<void>;
    handleBulkSendConnection: () => Promise<void>;
}

export function useBulkActions(options?: UseBulkActionsOptions): UseBulkActionsReturn {
    const [selectedForBulk, setSelectedForBulk] = useState<Set<number>>(new Set());
    const [isBulkRefreshing, setIsBulkRefreshing] = useState(false);
    const [isBulkSendingDM, setIsBulkSendingDM] = useState(false);
    const [isBulkSendingConnection, setIsBulkSendingConnection] = useState(false);

    const toggleBulkSelection = useCallback((leadId: number) => {
        setSelectedForBulk(prev => {
            const newSet = new Set(prev);
            if (newSet.has(leadId)) {
                newSet.delete(leadId);
            } else {
                newSet.add(leadId);
            }
            return newSet;
        });
    }, []);

    const clearBulkSelection = useCallback(() => {
        setSelectedForBulk(new Set());
    }, []);

    const handleBulkRefresh = useCallback(async () => {
        if (selectedForBulk.size === 0) return;

        setIsBulkRefreshing(true);
        try {
            toast.loading(`Refreshing ${selectedForBulk.size} leads...`, { id: 'bulk-refresh' });
            const leadIds = Array.from(selectedForBulk);
            const result = await bulkRefreshLeads(leadIds);

            toast.success(`Refreshed leads: ${result.success_count} success, ${result.failed_count} failed`, { id: 'bulk-refresh' });

            if (result.success_count > 0) {
                options?.onComplete?.();
            }
        } catch (error) {
            const apiError = error as ApiError;
            toast.error(apiError.message || 'Bulk refresh failed', { id: 'bulk-refresh' });
        } finally {
            setIsBulkRefreshing(false);
        }
    }, [selectedForBulk, options]);

    const handleBulkSendDM = useCallback(async () => {
        if (selectedForBulk.size === 0) return;

        setIsBulkSendingDM(true);
        try {
            toast.loading(`Sending ${selectedForBulk.size} DMs...`, { id: 'bulk-dm' });
            const leadIds = Array.from(selectedForBulk);
            const result = await bulkSend(leadIds, 'dm');

            toast.success(`DMs processed: ${result.successful} success, ${result.failed} failed`, { id: 'bulk-dm' });

            if (result.successful > 0) {
                options?.onComplete?.();
            }
        } catch (error) {
            const apiError = error as ApiError;
            toast.error(apiError.message || 'Bulk DM failed', { id: 'bulk-dm' });
        } finally {
            setIsBulkSendingDM(false);
        }
    }, [selectedForBulk, options]);

    const handleBulkSendConnection = useCallback(async () => {
        if (selectedForBulk.size === 0) return;

        setIsBulkSendingConnection(true);
        try {
            toast.loading(`Sending ${selectedForBulk.size} connections...`, { id: 'bulk-connection' });
            const leadIds = Array.from(selectedForBulk);
            const result = await bulkSend(leadIds, 'connection');

            toast.success(`Connections processed: ${result.successful} success, ${result.failed} failed`, { id: 'bulk-connection' });

            if (result.successful > 0) {
                options?.onComplete?.();
            }
        } catch (error) {
            const apiError = error as ApiError;
            toast.error(apiError.message || 'Bulk connection failed', { id: 'bulk-connection' });
        } finally {
            setIsBulkSendingConnection(false);
        }
    }, [selectedForBulk, options]);

    return {
        selectedForBulk,
        isBulkRefreshing,
        isBulkSendingDM,
        isBulkSendingConnection,
        toggleBulkSelection,
        clearBulkSelection,
        handleBulkRefresh,
        handleBulkSendDM,
        handleBulkSendConnection
    };
}
