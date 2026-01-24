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
                <div className="flex items-center justify-between p-4 border-b border-stone-100 bg-stone-50/50">
                    <h2 className="text-lg font-bold text-stone-800">
                        {leadName ? `Activity: ${leadName}` : 'Global Activity Log'}
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-stone-100 rounded-lg transition-colors text-stone-400"
                    >
                        ✕
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4">
                    {loading ? (
                        <div className="flex items-center justify-center h-48">
                            <div className="animate-spin text-3xl text-green-600">⏳</div>
                        </div>
                    ) : activities.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-48 text-stone-400">
                            <span className="text-4xl mb-3 opacity-50">📋</span>
                            <span className="font-medium">No activities yet</span>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {activities.map((activity) => (
                                <div
                                    key={activity.id}
                                    className="flex gap-4 p-4 rounded-xl border border-stone-50 bg-stone-50/30 hover:bg-stone-50 transition-all group"
                                >
                                    <div className={`w-12 h-12 rounded-2xl shadow-sm flex items-center justify-center shrink-0 ${getActivityColor(activity.activity_type)}`}>
                                        <span className="text-xl">{getActivityIcon(activity.activity_type)}</span>
                                    </div>

                                    <div className="flex-1 min-w-0 flex flex-col justify-center">
                                        <div className="font-bold text-stone-800 leading-tight">
                                            {activity.title}
                                        </div>
                                        {activity.description && (
                                            <div className="text-sm text-stone-500 font-medium truncate mt-0.5">
                                                {activity.description}
                                            </div>
                                        )}
                                        <div className="text-[11px] text-stone-400 font-bold uppercase tracking-tight mt-1.5 flex items-center gap-1.5">
                                            <span className="opacity-70">🕒</span>
                                            {new Date(activity.created_at).toLocaleString()}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-stone-100">
                    <button
                        onClick={onClose}
                        className="w-full py-2.5 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded-xl font-bold transition-all"
                    >
                        Close Window
                    </button>
                </div>
            </div>
        </div>
    );
}
