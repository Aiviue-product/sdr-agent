'use client';

import { RefreshCw, Send, UserPlus } from 'lucide-react';

interface BulkActionBarProps {
    selectedCount: number;
    totalCount: number;
    onSelectAll: () => void;
    isAllSelected: boolean;
    onBulkRefresh: () => void;
    onBulkSendConnection: () => void;
    onBulkSendDM: () => void;
    isBulkRefreshing: boolean;
    isBulkSendingConnection: boolean;
    isBulkSendingDM: boolean;
}

export default function BulkActionBar({
    selectedCount,
    totalCount,
    onSelectAll,
    isAllSelected,
    onBulkRefresh,
    onBulkSendConnection,
    onBulkSendDM,
    isBulkRefreshing,
    isBulkSendingConnection,
    isBulkSendingDM
}: BulkActionBarProps) {
    return (
        <div className="flex items-center justify-between pt-2 border-t border-pink-50">
            <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-600 hover:text-gray-800">
                <input
                    type="checkbox"
                    checked={isAllSelected}
                    onChange={onSelectAll}
                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                Select All ({selectedCount}/{totalCount})
            </label>

            {selectedCount > 0 && (
                <div className="flex items-center gap-2">
                    <button
                        onClick={onBulkRefresh}
                        disabled={isBulkRefreshing}
                        className={`flex items-center gap-1 px-2 py-1 text-xs rounded font-medium transition-colors
                            ${isBulkRefreshing
                                ? 'bg-pink-100 text-pink-400 cursor-wait'
                                : 'bg-amber-500 text-white hover:bg-amber-600'
                            }`}
                    >
                        <RefreshCw className={`w-3 h-3 ${isBulkRefreshing ? 'animate-spin' : ''}`} />
                        {isBulkRefreshing ? '...' : 'Refresh'}
                    </button>
                    <button
                        onClick={onBulkSendConnection}
                        disabled={isBulkSendingConnection}
                        className={`flex items-center gap-1 px-2 py-1 text-xs rounded font-medium transition-colors
                            ${isBulkSendingConnection
                                ? 'bg-blue-100 text-blue-400 cursor-wait'
                                : 'bg-blue-500 text-white hover:bg-blue-600'
                            }`}
                    >
                        <UserPlus className={`w-3 h-3 ${isBulkSendingConnection ? 'animate-pulse' : ''}`} />
                        {isBulkSendingConnection ? '...' : 'Connect'}
                    </button>
                    <button
                        onClick={onBulkSendDM}
                        disabled={isBulkSendingDM}
                        className={`flex items-center gap-1 px-2 py-1 text-xs rounded font-medium transition-colors
                            ${isBulkSendingDM
                                ? 'bg-green-100 text-green-400 cursor-wait'
                                : 'bg-green-500 text-white hover:bg-green-600'
                            }`}
                    >
                        <Send className={`w-3 h-3 ${isBulkSendingDM ? 'animate-pulse' : ''}`} />
                        {isBulkSendingDM ? '...' : 'DM'}
                    </button>
                </div>
            )}
        </div>
    );
}
