'use client';

import { AlertCircle, Copy, Loader2, MessageCircle, RefreshCw } from 'lucide-react';
import { DmGenerationStatus } from '../../types/linkedin';

interface DmPreviewCardProps {
    dm: string | null | undefined;
    dmGenerationStatus?: DmGenerationStatus;
    dmGenerationStartedAt?: string;
    onCopy: () => void;
    onRefresh?: () => void;
    isRefreshing?: boolean;
}

// Check if DM generation is stuck (pending for more than 10 minutes)
function isGenerationStuck(startedAt: string | undefined): boolean {
    if (!startedAt) return false;
    const started = new Date(startedAt).getTime();
    const now = Date.now();
    const tenMinutes = 10 * 60 * 1000; // 10 minutes in ms
    return (now - started) > tenMinutes;
}

export default function DmPreviewCard({ 
    dm, 
    dmGenerationStatus = 'generated',
    dmGenerationStartedAt,
    onCopy,
    onRefresh,
    isRefreshing = false
}: DmPreviewCardProps) {
    const isStuck = dmGenerationStatus === 'pending' && isGenerationStuck(dmGenerationStartedAt);
    const isPending = dmGenerationStatus === 'pending' && !isStuck;
    const isFailed = dmGenerationStatus === 'failed';
    const isGenerated = dmGenerationStatus === 'generated' || (dm && dmGenerationStatus !== 'pending' && dmGenerationStatus !== 'failed');

    // Render content based on status
    const renderContent = () => {
        // Pending state - show spinner
        if (isPending) {
            return (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                    <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-3" />
                    <p className="text-gray-600 font-medium">Generating your personalized DM...</p>
                    <p className="text-gray-400 text-sm mt-1">This may take a few moments</p>
                </div>
            );
        }

        // Stuck state - pending for too long
        if (isStuck) {
            return (
                <div className="flex flex-col items-center justify-center py-6 text-center">
                    <AlertCircle className="w-8 h-8 text-amber-500 mb-3" />
                    <p className="text-gray-700 font-medium">DM generation seems stuck</p>
                    <p className="text-gray-500 text-sm mt-1 mb-4">
                        Please click the Refresh button to try again
                    </p>
                    {onRefresh && (
                        <button
                            onClick={onRefresh}
                            disabled={isRefreshing}
                            className="flex items-center gap-2 px-4 py-2 bg-amber-100 text-amber-700 rounded-lg hover:bg-amber-200 transition-colors disabled:opacity-50"
                        >
                            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                            {isRefreshing ? 'Refreshing...' : 'Refresh Analysis'}
                        </button>
                    )}
                </div>
            );
        }

        // Failed state
        if (isFailed) {
            return (
                <div className="flex flex-col items-center justify-center py-6 text-center">
                    <AlertCircle className="w-8 h-8 text-red-500 mb-3" />
                    <p className="text-gray-700 font-medium">DM generation failed</p>
                    <p className="text-gray-500 text-sm mt-1 mb-4">
                        Please click the Refresh button to try again
                    </p>
                    {onRefresh && (
                        <button
                            onClick={onRefresh}
                            disabled={isRefreshing}
                            className="flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors disabled:opacity-50"
                        >
                            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                            {isRefreshing ? 'Refreshing...' : 'Retry Generation'}
                        </button>
                    )}
                </div>
            );
        }

        // Generated state - show DM
        return (
            <>
                <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                    {dm || 'No DM generated yet. Run a new search to generate DMs.'}
                </p>
                <p className="text-xs text-gray-400 mt-4">
                    {dm?.length || 0} / 400 characters
                </p>
            </>
        );
    };

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-100 flex justify-between items-center">
                <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                    <MessageCircle className="w-4 h-4 text-blue-600" />
                    AI-Generated LinkedIn DM
                    {isPending && (
                        <span className="ml-2 px-2 py-0.5 text-xs bg-blue-100 text-blue-600 rounded-full">
                            Generating...
                        </span>
                    )}
                </h3>
                {isGenerated && dm && (
                    <button
                        onClick={onCopy}
                        className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 font-medium"
                    >
                        <Copy className="w-4 h-4" />
                        Copy
                    </button>
                )}
            </div>
            <div className="p-6">
                {renderContent()}
            </div>
        </div>
    );
}
