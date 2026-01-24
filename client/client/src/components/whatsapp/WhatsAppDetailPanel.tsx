/**
 * WhatsApp Detail Panel Component
 * Right panel showing selected lead details and send action.
 */
import { WhatsAppLeadDetail } from '../../types/whatsapp';

interface WhatsAppDetailPanelProps {
    leadDetail: WhatsAppLeadDetail | null;
    loading: boolean;
    selectedTemplate: string;
    onSendWhatsApp: () => void;
    onOpenActivity: (leadId: number, leadName: string) => void;
    isSending: boolean;
}

export default function WhatsAppDetailPanel({
    leadDetail,
    loading,
    selectedTemplate,
    onSendWhatsApp,
    onOpenActivity,
    isSending
}: WhatsAppDetailPanelProps) {
    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <div className="animate-spin text-4xl mb-3">⏳</div>
                    <span className="text-gray-500">Loading lead details...</span>
                </div>
            </div>
        );
    }

    if (!leadDetail) {
        return (
            <div className="flex-1 flex items-center justify-center bg-gray-50">
                <div className="text-center text-gray-500">
                    <div className="text-5xl mb-3">📱</div>
                    <p>Select a lead to view details</p>
                </div>
            </div>
        );
    }

    const getStatusInfo = () => {
        if (!leadDetail.is_wa_sent) {
            return {
                icon: '⏳',
                text: 'Not sent yet',
                color: 'text-gray-600 bg-gray-100'
            };
        }

        switch (leadDetail.last_delivery_status) {
            case 'SENT':
                return { icon: '📤', text: 'Message sent', color: 'text-blue-600 bg-blue-100' };
            case 'DELIVERED':
                return { icon: '✅', text: 'Delivered', color: 'text-green-600 bg-green-100' };
            case 'READ':
                return { icon: '👀', text: 'Read', color: 'text-green-700 bg-green-200' };
            case 'FAILED':
                return { icon: '❌', text: 'Failed', color: 'text-red-600 bg-red-100' };
            default:
                return { icon: '⏳', text: 'Pending', color: 'text-yellow-600 bg-yellow-100' };
        }
    };

    const status = getStatusInfo();
    const canSend = !leadDetail.is_wa_sent && selectedTemplate;

    return (
        <div className="flex-1 bg-gray-50 overflow-y-auto">
            <div className="max-w-2xl mx-auto p-6">
                {/* Header Card */}
                <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
                    <div className="flex items-start justify-between">
                        <div>
                            <h2 className="text-2xl font-bold text-gray-800">
                                {leadDetail.first_name} {leadDetail.last_name}
                            </h2>
                            <div className="flex items-center gap-2 mt-2 text-gray-600">
                                <span className="text-lg">📱</span>
                                <span className="font-mono">{leadDetail.mobile_number}</span>
                            </div>
                        </div>

                        {/* Status Badge */}
                        <div className={`px-3 py-1.5 rounded-lg flex items-center gap-2 ${status.color}`}>
                            <span>{status.icon}</span>
                            <span className="font-medium">{status.text}</span>
                        </div>
                    </div>

                    {/* Details Grid */}
                    <div className="grid grid-cols-2 gap-4 mt-6">
                        {leadDetail.email && (
                            <div>
                                <label className="text-xs text-gray-500 uppercase">Email</label>
                                <p className="text-gray-800">{leadDetail.email}</p>
                            </div>
                        )}
                        {leadDetail.company_name && (
                            <div>
                                <label className="text-xs text-gray-500 uppercase">Company</label>
                                <p className="text-gray-800">{leadDetail.company_name}</p>
                            </div>
                        )}
                        {leadDetail.designation && (
                            <div>
                                <label className="text-xs text-gray-500 uppercase">Designation</label>
                                <p className="text-gray-800">{leadDetail.designation}</p>
                            </div>
                        )}
                        {leadDetail.source && (
                            <div>
                                <label className="text-xs text-gray-500 uppercase">Source</label>
                                <p className="text-gray-800 capitalize">{leadDetail.source.replace('_', ' ')}</p>
                            </div>
                        )}
                        {leadDetail.linkedin_url && (
                            <div className="col-span-2">
                                <label className="text-xs text-gray-500 uppercase">LinkedIn</label>
                                <a
                                    href={leadDetail.linkedin_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-blue-600 hover:underline truncate block"
                                >
                                    {leadDetail.linkedin_url}
                                </a>
                            </div>
                        )}
                    </div>
                </div>

                {/* Last Message Info */}
                {leadDetail.is_wa_sent && (
                    <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
                        <h3 className="text-lg font-semibold text-gray-800 mb-4">📨 Last Message</h3>

                        <div className="space-y-3">
                            <div className="flex justify-between">
                                <span className="text-gray-500">Template:</span>
                                <span className="font-medium">{leadDetail.last_template_used || '-'}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">Sent at:</span>
                                <span>{leadDetail.last_sent_at ? new Date(leadDetail.last_sent_at).toLocaleString() : '-'}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">Status:</span>
                                <span className={status.color.split(' ')[0]}>{leadDetail.last_delivery_status}</span>
                            </div>
                            {leadDetail.last_failed_reason && (
                                <div className="p-3 bg-red-50 rounded-lg text-red-700 text-sm">
                                    <strong>Error:</strong> {leadDetail.last_failed_reason}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Action Buttons */}
                <div className="bg-white rounded-xl shadow-sm p-6">
                    <h3 className="text-lg font-semibold text-gray-800 mb-4">⚡ Actions</h3>

                    <div className="flex gap-3">
                        <button
                            onClick={onSendWhatsApp}
                            disabled={!canSend || isSending}
                            className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg font-medium transition-colors ${canSend && !isSending
                                    ? 'bg-green-600 hover:bg-green-700 text-white'
                                    : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                                }`}
                        >
                            {isSending ? (
                                <>
                                    <span className="animate-spin">⏳</span>
                                    Sending...
                                </>
                            ) : (
                                <>
                                    <span>📤</span>
                                    {leadDetail.is_wa_sent ? 'Already Sent' : 'Send WhatsApp'}
                                </>
                            )}
                        </button>

                        <button
                            onClick={() => onOpenActivity(leadDetail.id, leadDetail.first_name)}
                            className="px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                        >
                            📋 Activity
                        </button>
                    </div>

                    {!selectedTemplate && !leadDetail.is_wa_sent && (
                        <p className="mt-3 text-sm text-amber-600">
                            ⚠️ Select a template from the header to send
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}
