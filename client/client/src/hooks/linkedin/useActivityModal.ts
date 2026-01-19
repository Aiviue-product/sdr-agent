/**
 * useActivityModal Hook
 * 
 * Manages the LinkedIn activity timeline modal:
 * - Modal visibility
 * - Fetching activities with pagination
 * - Loading more activities (infinite scroll style)
 */
import { useCallback, useState } from 'react';
import toast from 'react-hot-toast';
import { getActivities } from '../../services/linkedin-service/api';
import { ActivityItem } from '../../types/linkedin';

interface UseActivityModalReturn {
    // State
    showActivityModal: boolean;
    activeActivityLeadId: number | null;
    activeActivityLeadName: string | undefined;
    activities: ActivityItem[];
    loadingActivities: boolean;
    activityPage: number;
    hasMoreActivities: boolean;

    // Actions
    openActivityModal: (leadId?: number, leadName?: string) => void;
    closeActivityModal: () => void;
    loadMoreActivities: () => Promise<void>;
}

export function useActivityModal(): UseActivityModalReturn {
    const [showActivityModal, setShowActivityModal] = useState(false);
    const [activeActivityLeadId, setActiveActivityLeadId] = useState<number | null>(null);
    const [activeActivityLeadName, setActiveActivityLeadName] = useState<string | undefined>(undefined);
    const [activities, setActivities] = useState<ActivityItem[]>([]);
    const [loadingActivities, setLoadingActivities] = useState(false);
    const [activityPage, setActivityPage] = useState(1);
    const [hasMoreActivities, setHasMoreActivities] = useState(false);

    const fetchActivities = useCallback(async (page: number, leadId?: number) => {
        if (page === 1) {
            setActivities([]);
        }
        setLoadingActivities(true);
        try {
            const response = await getActivities({ page, leadId });
            if (page === 1) {
                setActivities(response.activities);
            } else {
                setActivities(prev => [...prev, ...response.activities]);
            }
            setHasMoreActivities(response.has_more);
        } catch (error) {
            console.error('Failed to load activities:', error);
            toast.error('Failed to load activities');
        } finally {
            setLoadingActivities(false);
        }
    }, []);

    const openActivityModal = useCallback((leadId?: number, leadName?: string) => {
        setActiveActivityLeadId(leadId || null);
        setActiveActivityLeadName(leadName);
        setShowActivityModal(true);
        setActivityPage(1);
        fetchActivities(1, leadId);
    }, [fetchActivities]);

    const closeActivityModal = useCallback(() => {
        setShowActivityModal(false);
    }, []);

    const loadMoreActivities = useCallback(async () => {
        if (loadingActivities || !hasMoreActivities) return;

        const nextPage = activityPage + 1;
        setActivityPage(nextPage);
        await fetchActivities(nextPage, activeActivityLeadId || undefined);
    }, [loadingActivities, hasMoreActivities, activityPage, activeActivityLeadId, fetchActivities]);

    return {
        showActivityModal,
        activeActivityLeadId,
        activeActivityLeadName,
        activities,
        loadingActivities,
        activityPage,
        hasMoreActivities,
        openActivityModal,
        closeActivityModal,
        loadMoreActivities
    };
}
