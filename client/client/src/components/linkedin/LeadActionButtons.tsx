'use client';

import { Activity, ExternalLink, RefreshCw, Send, UserPlus } from 'lucide-react';

interface LeadActionButtonsProps {
    onOpenProfile: () => void;
    onRefresh: () => void;
    onSendConnection: () => void;
    onSendDM: () => void;
    onOpenActivity: () => void;
    isRefreshing: boolean;
    isSendingConnection: boolean;
    isSendingDM: boolean;
}

export default function LeadActionButtons({
    onOpenProfile,
    onRefresh,
    onSendConnection,
    onSendDM,
    onOpenActivity,
    isRefreshing,
    isSendingConnection,
    isSendingDM
}: LeadActionButtonsProps) {
    return (
        <div className="flex gap-2 w-full sm:w-auto">
            <button
                onClick={onOpenProfile}
                className="flex items-center justify-center gap-1.5 px-4 py-2 text-sm bg-gradient-to-r from-pink-400/90 via-purple-400/90 to-indigo-400/90 text-white rounded-lg font-medium hover:from-pink-500 hover:via-purple-500 hover:to-indigo-500 transition-all shadow-sm hover:shadow-md whitespace-nowrap"
            >
                <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                Open LinkedIn
            </button>

            <button
                onClick={onRefresh}
                disabled={isRefreshing}
                className={`flex items-center justify-center gap-1.5 px-4 py-2 text-sm rounded-lg font-medium transition-all whitespace-nowrap
                    ${isRefreshing
                        ? 'bg-gray-100 text-gray-400 cursor-wait'
                        : 'bg-gradient-to-r from-amber-400 to-orange-400 text-white hover:from-amber-500 hover:to-orange-500 shadow-sm hover:shadow-md'
                    }`}
            >
                <RefreshCw className={`w-3.5 h-3.5 flex-shrink-0 ${isRefreshing ? 'animate-spin' : ''}`} />
                {isRefreshing ? 'Refreshing...' : 'Refresh'}
            </button>

            <button
                onClick={onSendConnection}
                disabled={isSendingConnection}
                className={`flex items-center justify-center gap-1.5 px-4 py-2 text-sm rounded-lg font-medium transition-all whitespace-nowrap
                    ${isSendingConnection
                        ? 'bg-gray-100 text-gray-400 cursor-wait'
                        : 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white hover:from-blue-600 hover:to-cyan-600 shadow-sm hover:shadow-md'
                    }`}
            >
                <UserPlus className={`w-3.5 h-3.5 flex-shrink-0 ${isSendingConnection ? 'animate-pulse' : ''}`} />
                {isSendingConnection ? 'Sending...' : 'Connect'}
            </button>

            <button
                onClick={onSendDM}
                disabled={isSendingDM}
                className={`flex items-center justify-center gap-1.5 px-4 py-2 text-sm rounded-lg font-medium transition-all whitespace-nowrap
                    ${isSendingDM
                        ? 'bg-gray-100 text-gray-400 cursor-wait'
                        : 'bg-gradient-to-r from-green-500 to-emerald-500 text-white hover:from-green-600 hover:to-emerald-600 shadow-sm hover:shadow-md'
                    }`}
            >
                <Send className={`w-3.5 h-3.5 flex-shrink-0 ${isSendingDM ? 'animate-pulse' : ''}`} />
                {isSendingDM ? 'Sending...' : 'Send DM'}
            </button>

            <button
                onClick={onOpenActivity}
                className="flex items-center justify-center gap-1.5 px-4 py-2 text-sm bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg font-medium hover:from-purple-600 hover:to-pink-600 shadow-sm hover:shadow-md transition-all whitespace-nowrap"
            >
                <Activity className="w-3.5 h-3.5 flex-shrink-0" />
                Activity
            </button>
        </div>
    );
}
