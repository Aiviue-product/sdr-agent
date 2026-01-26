/**
 * WhatsApp Bulk Job Modal
 * Shows progress for bulk send jobs with pause/cancel controls.
 */
import { useEffect, useState } from 'react';
import { BulkJobDetail, BulkJobItem, BulkJobStatus } from '../../types/whatsapp';
import {
    cancelBulkJob,
    createBulkJob,
    getBulkJob,
    getBulkJobItems,
    pauseBulkJob,
    startBulkJob
} from '../../services/whatsapp-service/api';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    leadIds: number[];
    templateName: string;
    onComplete: () => void;
}

export default function WhatsAppBulkJobModal({
    isOpen,
    onClose,
    leadIds,
    templateName,
    onComplete
}: Props) {
    const [job, setJob] = useState<BulkJobDetail | null>(null);
    const [failedItems, setFailedItems] = useState<BulkJobItem[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [isCreating, setIsCreating] = useState(false);
    const [isPausing, setIsPausing] = useState(false);
    const [isCancelling, setIsCancelling] = useState(false);
    const [isResuming, setIsResuming] = useState(false);

    // Poll interval ref
    const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null);

    // Fetch failed items when job completes with failures
    useEffect(() => {
        if (job && job.failed_count > 0 && 
            (job.status === BulkJobStatus.COMPLETED || job.status === BulkJobStatus.FAILED)) {
            loadFailedItems();
        }
    }, [job?.id, job?.status, job?.failed_count]);

    const loadFailedItems = async () => {
        if (!job) return;
        try {
            const response = await getBulkJobItems(job.id, 'failed', 0, 10);
            setFailedItems(response.items || []);
        } catch (err) {
            console.error('Failed to load failed items:', err);
        }
    };

    // Create and start job when modal opens
    useEffect(() => {
        if (isOpen && leadIds.length > 0 && !job) {
            createAndStartJob();
        }

        return () => {
            if (pollInterval) {
                clearInterval(pollInterval);
            }
        };
    }, [isOpen, leadIds]);

    // Poll for job status when running
    useEffect(() => {
        if (job && job.status === BulkJobStatus.RUNNING) {
            const interval = setInterval(async () => {
                try {
                    const response = await getBulkJob(job.id);
                    if (response.job) {
                        setJob(response.job);

                        // Stop polling if job is no longer running
                        if (response.job.status !== BulkJobStatus.RUNNING) {
                            clearInterval(interval);
                            setPollInterval(null);
                        }
                    }
                } catch (err) {
                    console.error('Failed to poll job status:', err);
                }
            }, 2000); // Poll every 2 seconds

            setPollInterval(interval);

            return () => clearInterval(interval);
        }
    }, [job?.id, job?.status]);

    const createAndStartJob = async () => {
        setIsCreating(true);
        setError(null);

        try {
            const response = await createBulkJob({
                lead_ids: leadIds,
                template_name: templateName,
                broadcast_name: `bulk_${Date.now()}`,
                start_immediately: true // Start right away
            });

            if (response.success && response.job) {
                setJob(response.job);
            } else {
                setError(response.error || 'Failed to create job');
            }
        } catch (err) {
            const e = err as Error;
            setError(e.message || 'Failed to create bulk job');
        } finally {
            setIsCreating(false);
        }
    };

    const handlePause = async () => {
        if (!job) return;

        setIsPausing(true);
        try {
            const response = await pauseBulkJob(job.id);
            if (response.job) {
                setJob(response.job);
            }
        } catch (err) {
            const e = err as Error;
            setError(e.message);
        } finally {
            setIsPausing(false);
        }
    };

    const handleResume = async () => {
        if (!job) return;

        setIsResuming(true);
        try {
            const response = await startBulkJob(job.id);
            if (response.job) {
                setJob(response.job);
            }
        } catch (err) {
            const e = err as Error;
            setError(e.message);
        } finally {
            setIsResuming(false);
        }
    };

    const handleCancel = async () => {
        if (!job) return;

        if (!confirm('Are you sure you want to cancel? This cannot be undone.')) {
            return;
        }

        setIsCancelling(true);
        try {
            const response = await cancelBulkJob(job.id);
            if (response.job) {
                setJob(response.job);
            }
        } catch (err) {
            const e = err as Error;
            setError(e.message);
        } finally {
            setIsCancelling(false);
        }
    };

    const handleClose = () => {
        if (pollInterval) {
            clearInterval(pollInterval);
        }
        
        // If job completed or was cancelled, notify parent
        if (job && (job.status === BulkJobStatus.COMPLETED || 
                    job.status === BulkJobStatus.CANCELLED ||
                    job.status === BulkJobStatus.FAILED)) {
            onComplete();
        }
        
        setJob(null);
        setFailedItems([]);
        setError(null);
        onClose();
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case BulkJobStatus.RUNNING:
                return 'text-blue-600';
            case BulkJobStatus.COMPLETED:
                return 'text-green-600';
            case BulkJobStatus.PAUSED:
                return 'text-yellow-600';
            case BulkJobStatus.FAILED:
            case BulkJobStatus.CANCELLED:
                return 'text-red-600';
            default:
                return 'text-gray-600';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case BulkJobStatus.RUNNING:
                return '🔄';
            case BulkJobStatus.COMPLETED:
                return '✅';
            case BulkJobStatus.PAUSED:
                return '⏸️';
            case BulkJobStatus.FAILED:
                return '❌';
            case BulkJobStatus.CANCELLED:
                return '🚫';
            default:
                return '⏳';
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-2xl w-full max-w-md mx-4 border border-gray-200">
                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-900">
                        Bulk WhatsApp Send
                    </h2>
                </div>

                {/* Content */}
                <div className="px-6 py-4">
                    {isCreating ? (
                        <div className="text-center py-8">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 mx-auto mb-4"></div>
                            <p className="text-gray-600">Creating job...</p>
                        </div>
                    ) : error ? (
                        <div className="text-center py-8">
                            <div className="text-red-500 text-4xl mb-4">❌</div>
                            <p className="text-red-600">{error}</p>
                            <button
                                onClick={createAndStartJob}
                                className="mt-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                            >
                                Retry
                            </button>
                        </div>
                    ) : job ? (
                        <div className="space-y-4">
                            {/* Status */}
                            <div className="flex items-center justify-between">
                                <span className="text-gray-600">Status:</span>
                                <span className={`font-semibold ${getStatusColor(job.status)}`}>
                                    {getStatusIcon(job.status)} {job.status.toUpperCase()}
                                </span>
                            </div>

                            {/* Progress Bar */}
                            <div>
                                <div className="flex justify-between text-sm text-gray-600 mb-1">
                                    <span>Progress</span>
                                    <span>{job.progress_percent}%</span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-4">
                                    <div
                                        className={`h-4 rounded-full transition-all duration-300 ${
                                            job.status === BulkJobStatus.COMPLETED
                                                ? 'bg-green-500'
                                                : job.status === BulkJobStatus.FAILED
                                                ? 'bg-red-500'
                                                : 'bg-blue-500'
                                        }`}
                                        style={{ width: `${job.progress_percent}%` }}
                                    ></div>
                                </div>
                            </div>

                            {/* Stats */}
                            <div className="grid grid-cols-3 gap-4 text-center">
                                <div className="bg-green-50 rounded-lg p-3">
                                    <div className="text-2xl font-bold text-green-600">
                                        {job.sent_count}
                                    </div>
                                    <div className="text-xs text-green-700">Sent</div>
                                </div>
                                <div className="bg-red-50 rounded-lg p-3">
                                    <div className="text-2xl font-bold text-red-600">
                                        {job.failed_count}
                                    </div>
                                    <div className="text-xs text-red-700">Failed</div>
                                </div>
                                <div className="bg-gray-50 rounded-lg p-3">
                                    <div className="text-2xl font-bold text-gray-600">
                                        {job.pending_count}
                                    </div>
                                    <div className="text-xs text-gray-700">Pending</div>
                                </div>
                            </div>

                            {/* Template Info */}
                            <div className="text-sm text-gray-500">
                                Template: <span className="font-medium">{job.template_name}</span>
                            </div>

                            {/* Job Error Message */}
                            {job.error_message && (
                                <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                                    <strong>Job Error:</strong> {job.error_message}
                                </div>
                            )}

                            {/* Show failed items with actual errors */}
                            {failedItems.length > 0 && (
                                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                    <div className="text-sm font-medium text-red-800 mb-2">
                                        Failed Items ({job.failed_count}):
                                    </div>
                                    <div className="max-h-32 overflow-y-auto space-y-1">
                                        {failedItems.map((item) => (
                                            <div key={item.id} className="text-xs text-red-700 bg-red-100 rounded px-2 py-1">
                                                <span className="font-medium">Lead #{item.lead_id}:</span>{' '}
                                                {item.error_message || 'Unknown error'}
                                            </div>
                                        ))}
                                        {job.failed_count > failedItems.length && (
                                            <div className="text-xs text-red-600 italic">
                                                ... and {job.failed_count - failedItems.length} more
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Action Buttons */}
                            <div className="flex gap-2 pt-2">
                                {job.status === BulkJobStatus.RUNNING && (
                                    <button
                                        onClick={handlePause}
                                        disabled={isPausing}
                                        className="flex-1 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50"
                                    >
                                        {isPausing ? 'Pausing...' : '⏸️ Pause'}
                                    </button>
                                )}

                                {(job.status === BulkJobStatus.PAUSED || 
                                  job.status === BulkJobStatus.FAILED) && (
                                    <button
                                        onClick={handleResume}
                                        disabled={isResuming}
                                        className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                                    >
                                        {isResuming ? 'Resuming...' : '▶️ Resume'}
                                    </button>
                                )}

                                {job.status !== BulkJobStatus.COMPLETED && 
                                 job.status !== BulkJobStatus.CANCELLED && (
                                    <button
                                        onClick={handleCancel}
                                        disabled={isCancelling}
                                        className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50"
                                    >
                                        {isCancelling ? '...' : '🚫 Cancel'}
                                    </button>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-8">
                            <p className="text-gray-600">Initializing...</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-gray-200 flex justify-end">
                    <button
                        onClick={handleClose}
                        className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                    >
                        {job?.status === BulkJobStatus.RUNNING ? 'Close (runs in background)' : 'Close'}
                    </button>
                </div>
            </div>
        </div>
    );
}
