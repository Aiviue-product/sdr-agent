'use client';

import {
    Activity,
    Link2,
    Loader2,
    MessageCircle,
    Send,
    UserPlus,
    X
} from 'lucide-react';
import { ActivityItem } from '../../types/linkedin';

interface ActivityModalProps {
    isOpen: boolean;
    onClose: () => void;
    activities: ActivityItem[];
    loading: boolean;
    hasMore: boolean;
    currentPage: number;
    onLoadMore: () => void;
}

export default function ActivityModal({
    isOpen,
    onClose,
    activities,
    loading,
    hasMore,
    currentPage,
    onLoadMore
}: ActivityModalProps) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100] p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden">
                {/* Modal Header */}
                <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-pink-50 flex items-center justify-between">
                    <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                        <Activity className="w-5 h-5 text-purple-600" />
                        Activity Timeline
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                {/* Modal Body */}
                <div className="flex-1 overflow-y-auto p-6">
                    {loading && activities.length === 0 ? (
                        <div className="flex justify-center py-10">
                            <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
                        </div>
                    ) : activities.length === 0 ? (
                        <div className="text-center text-gray-400 py-10">
                            <Activity className="w-12 h-12 mx-auto mb-4 opacity-30" />
                            <p>No activities yet.</p>
                            <p className="text-sm mt-2">Activities will appear when you send DMs or connection requests.</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {activities.map((activity) => (
                                <div
                                    key={activity.id}
                                    className="flex items-start gap-4 p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
                                >
                                    {/* Activity Icon */}
                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0
                                        ${activity.activity_type === 'dm_sent' ? 'bg-green-100' : ''}
                                        ${activity.activity_type === 'dm_replied' ? 'bg-blue-100' : ''}
                                        ${activity.activity_type === 'connection_sent' ? 'bg-amber-100' : ''}
                                        ${activity.activity_type === 'connection_accepted' ? 'bg-emerald-100' : ''}
                                        ${!['dm_sent', 'dm_replied', 'connection_sent', 'connection_accepted'].includes(activity.activity_type) ? 'bg-gray-100' : ''}
                                    `}>
                                        {activity.activity_type === 'dm_sent' && <Send className="w-5 h-5 text-green-600" />}
                                        {activity.activity_type === 'dm_replied' && <MessageCircle className="w-5 h-5 text-blue-600" />}
                                        {activity.activity_type === 'connection_sent' && <UserPlus className="w-5 h-5 text-amber-600" />}
                                        {activity.activity_type === 'connection_accepted' && <Link2 className="w-5 h-5 text-emerald-600" />}
                                    </div>

                                    {/* Activity Content */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between">
                                            <h4 className="font-semibold text-gray-800">
                                                {activity.activity_type === 'dm_sent' && '📨 DM Sent'}
                                                {activity.activity_type === 'dm_replied' && '💬 Reply Received'}
                                                {activity.activity_type === 'connection_sent' && '🔗 Connection Sent'}
                                                {activity.activity_type === 'connection_accepted' && '✅ Connection Accepted'}
                                                {activity.activity_type === 'follow_up_sent' && '🔄 Follow-up Sent'}
                                            </h4>
                                            <span className="text-xs text-gray-400">
                                                {new Date(activity.created_at).toLocaleDateString('en-US', {
                                                    month: 'short',
                                                    day: 'numeric',
                                                    hour: '2-digit',
                                                    minute: '2-digit'
                                                })}
                                            </span>
                                        </div>
                                        {activity.lead_name && (
                                            <p className="text-sm text-gray-600 mt-1">
                                                {activity.lead_name}
                                            </p>
                                        )}
                                        {activity.message && (
                                            <p className="text-sm text-gray-500 mt-2 bg-white p-2 rounded-lg border border-gray-100 line-clamp-2">
                                                {activity.message}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            ))}

                            {/* Load More Button */}
                            {hasMore && (
                                <button
                                    onClick={onLoadMore}
                                    disabled={loading}
                                    className="w-full py-3 text-center text-purple-600 hover:text-purple-800 font-medium disabled:text-gray-400"
                                >
                                    {loading ? (
                                        <Loader2 className="w-4 h-4 animate-spin mx-auto" />
                                    ) : (
                                        'Load More'
                                    )}
                                </button>
                            )}
                        </div>
                    )}
                </div>

                {/* Modal Footer */}
                <div className="p-4 border-t border-gray-200 bg-gray-50 text-center text-sm text-gray-500">
                    Showing {activities.length} activities
                </div>
            </div>
        </div>
    );
}
