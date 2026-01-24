/**
 * WhatsApp Activity Modal Component
 * Shows activity timeline for a lead or global activities.
 */
import { WhatsAppActivity } from '../../types/whatsapp';

interface WhatsAppActivityModalProps {
    isOpen: boolean;
    onClose: () => void;
    activities: WhatsAppActivity[];
    loading: boolean;
    leadName?: string;
}

export default function WhatsAppActivityModal({
    isOpen,
    onClose,
    activities,
    loading,
    leadName
}: WhatsAppActivityModalProps) {
    if (!isOpen) return null;

    const getActivityIcon = (type: string) => {
        switch (type) {
            case 'message_sent': return '📤';
            case 'message_delivered': return '✅';
            case 'message_read': return '👀';
            case 'message_failed': return '❌';
            case 'reply_received': return '💬';
            case 'lead_created': return '👤';
            case 'leads_imported': return '📥';
            case 'bulk_send_started': return '🚀';
            case 'bulk_send_completed': return '✨';
            default: return '📋';
        }
    };

    const getActivityColor = (type: string) => {
        switch (type) {
            case 'message_sent': return 'bg-blue-100 text-blue-700';
            case 'message_delivered': return 'bg-green-100 text-green-700';
            case 'message_read': return 'bg-green-200 text-green-800';
            case 'message_failed': return 'bg-red-100 text-red-700';
            case 'reply_received': return 'bg-purple-100 text-purple-700';
            default: return 'bg-gray-100 text-gray-700';
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/50"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[80vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-800">
                        {leadName ? `Activity: ${leadName}` : 'Global Activity Log'}
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        ✕
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4">
                    {loading ? (
                        <div className="flex items-center justify-center h-32">
                            <div className="animate-spin text-2xl">⏳</div>
                        </div>
                    ) : activities.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                            <span className="text-3xl mb-2">📋</span>
                            <span>No activities yet</span>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {activities.map((activity) => (
                                <div
                                    key={activity.id}
                                    className="flex gap-3 p-3 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors"
                                >
                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${getActivityColor(activity.activity_type)}`}>
                                        {getActivityIcon(activity.activity_type)}
                                    </div>

                                    <div className="flex-1 min-w-0">
                                        <div className="font-medium text-gray-800">
                                            {activity.title}
                                        </div>
                                        {activity.description && (
                                            <div className="text-sm text-gray-500 truncate">
                                                {activity.description}
                                            </div>
                                        )}
                                        <div className="text-xs text-gray-400 mt-1">
                                            {new Date(activity.created_at).toLocaleString()}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-gray-200">
                    <button
                        onClick={onClose}
                        className="w-full py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}
