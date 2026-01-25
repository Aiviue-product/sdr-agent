import { WhatsAppLeadDetail, WhatsAppMessage } from '../../types/whatsapp';
import WhatsAppChatHistory from './WhatsAppChatHistory';

interface WhatsAppDetailPanelProps {
    leadDetail: WhatsAppLeadDetail | null;
    messages: WhatsAppMessage[];
    loadingDetails: boolean;
    loadingMessages: boolean;
    selectedTemplate: string;
    onSendWhatsApp: () => void;
    onOpenActivity: (leadId: number, leadName: string) => void;
    onDeleteLead: (leadId: number) => void;
    onSyncStatus: (leadId: number) => void;
    onEditLead: (lead: WhatsAppLeadDetail) => void;
    isSending: boolean;
    isDeleting: boolean;
    isSyncing: boolean;
}

export default function WhatsAppDetailPanel({
    leadDetail,
    messages,
    loadingDetails,
    loadingMessages,
    selectedTemplate,
    onSendWhatsApp,
    onOpenActivity,
    onDeleteLead,
    onSyncStatus,
    onEditLead,
    isSending,
    isDeleting,
    isSyncing
}: WhatsAppDetailPanelProps) {
    if (loadingDetails) {
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
                return { icon: '📤', text: 'Message sent', color: 'text-green-600 bg-green-100' };
            case 'DELIVERED':
                return { icon: '✅', text: 'Delivered', color: 'text-green-600 bg-green-100' };
            case 'READ':
                return { icon: '👀', text: 'Read', color: 'text-cyan-600 bg-cyan-100' };
            case 'REPLIED':
                return { icon: '💬', text: 'Replied!', color: 'text-purple-600 bg-purple-100' };
            case 'FAILED':
                return { icon: '❌', text: 'Failed', color: 'text-red-600 bg-red-100' };
            default:
                return { icon: '⏳', text: 'Pending', color: 'text-yellow-600 bg-yellow-100' };
        }
    };

    const status = getStatusInfo();
    const canSend = !!selectedTemplate;

    return (
        <div className="flex-1 flex overflow-hidden bg-white">
            {/* Left Column: Lead Details (55%) */}
            <div className="w-[55%] border-r border-gray-200 overflow-y-auto bg-gray-50 flex flex-col">
                <div className="p-6 space-y-6">
                    {/* Header Card */}
                    <div className="bg-gradient-to-br from-stone-100 to-stone-300 rounded-xl shadow-sm p-5">
                        <div className="flex items-start justify-between">
                            <div>
                                <h2 className="text-xl font-bold text-cyan-400">
                                    {leadDetail.first_name} {leadDetail.last_name}
                                </h2>
                                <div className="flex items-center gap-2 mt-1.5 text-gray-500 text-sm">
                                    <span>📱</span>
                                    <span className="font-mono">{leadDetail.mobile_number}</span>
                                </div>
                            </div>

                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => onEditLead(leadDetail)}
                                    className="p-1.5 text-gray-700 text-sm hover:text-blue-700 hover:bg-blue-50 rounded transition-colors"
                                    title="Edit Lead"
                                >
                                    ✏️ Edit
                                </button>
                                <div className={`px-2.5 py-1 rounded text-xs flex items-center gap-1.5 ${status.color}`}>
                                    <span>{status.icon}</span>
                                    <span className="font-bold">{status.text}</span>
                                </div>
                            </div>
                        </div>

                        {/* Details Grid */}
                        <div className="grid grid-cols-2 gap-4 mt-6">
                            {leadDetail.email && (
                                <div className="space-y-0.5">
                                    <label className="text-[10px] font-bold text-slate-600 uppercase tracking-wider">Email</label>
                                    <p className="text-sm text-gray-900 font-medium truncate">{leadDetail.email}</p>
                                </div>
                            )}
                            {leadDetail.company_name && (
                                <div className="space-y-0.5">
                                    <label className="text-[10px] font-bold text-slate-600 uppercase tracking-wider">Company</label>
                                    <p className="text-sm text-gray-900 font-medium">{leadDetail.company_name}</p>
                                </div>
                            )}
                            {leadDetail.linkedin_url && (
                                <div className="col-span-2 space-y-0.5 mt-2">
                                    <label className="text-[10px] font-bold text-slate-600 uppercase tracking-wider">LinkedIn Profile</label>
                                    <a
                                        href={leadDetail.linkedin_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-xs text-blue-500 hover:text-blue-600 truncate block font-medium"
                                    >
                                        {leadDetail.linkedin_url}
                                    </a>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Last Message Info */}
                    {leadDetail.is_wa_sent && (
                        <div className="bg-gradient-to-br from-stone-100 to-stone-300 rounded-xl shadow-sm p-5">
                            <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-wider mb-4">📨 Last Message Details</h3>
                            <div className="space-y-3">
                                <div className="flex justify-between items-center text-sm pb-1 border-b border-gray-50">
                                    <span className="text-slate-600">Template</span>
                                    <span className="font-semibold text-gray-700">{leadDetail.last_template_used || '-'}</span>
                                </div>
                                <div className="flex justify-between items-center text-sm pb-1 border-b border-gray-50">
                                    <span className="text-slate-600">Sent at</span>
                                    <span className="text-gray-700 font-medium">{leadDetail.last_sent_at ? new Date(leadDetail.last_sent_at).toLocaleString() : '-'}</span>
                                </div>
                                <div className="flex justify-between items-center text-sm pb-1 border-b border-gray-50">
                                    <span className="text-slate-600">Source</span>
                                    <span className="font-semibold text-gray-600 capitalize">{leadDetail.source?.replace('_', ' ') || 'Manual'}</span>
                                </div>
                                {leadDetail.last_failed_reason && leadDetail.last_delivery_status === 'FAILED' && (
                                    <div className="p-2.5 bg-red-50 rounded-lg text-red-700 text-xs">
                                        <strong>Error:</strong> {leadDetail.last_failed_reason}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Action Buttons */}
                    <div className="bg-stone-200 rounded-xl shadow-sm p-5">
                        <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-wider mb-4">⚡ Actions</h3>

                        <div className="space-y-3">
                            <button
                                onClick={onSendWhatsApp}
                                disabled={!canSend || isSending}
                                className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-lg font-bold transition-colors shadow-sm ${canSend && !isSending
                                    ? 'bg-green-600 hover:bg-green-700 text-white'
                                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                    }`}
                            >
                                {isSending ? <span className="animate-spin">⏳</span> : <span>📤</span>}
                                {selectedTemplate ? (leadDetail.is_wa_sent ? `Send Again: ${selectedTemplate}` : `Send: ${selectedTemplate}`) : 'Select Template Above'}
                            </button>

                            <div className="flex gap-2">
                                <button
                                    onClick={() => onSyncStatus(leadDetail.id)}
                                    disabled={isSyncing}
                                    className="flex-1 flex items-center justify-center gap-2 py-2 px-3 border border-blue-200 text-blue-600 rounded-lg hover:bg-blue-50 transition-colors text-xs font-bold disabled:opacity-50"
                                >
                                    {isSyncing ? <span className="animate-spin">⏳</span> : <span>🔄</span>}
                                    Refresh Status
                                </button>

                                <button
                                    onClick={() => onOpenActivity(leadDetail.id, leadDetail.first_name)}
                                    className="px-4 py-2 border text-stone-500 border-stone-300 rounded-lg hover:bg-gray-50 transition-colors text-xs font-bold"
                                >
                                    📋 individual activity Log
                                </button>

                                <button
                                    onClick={() => {
                                        if (window.confirm(`Delete ${leadDetail.first_name}?`)) {
                                            onDeleteLead(leadDetail.id);
                                        }
                                    }}
                                    disabled={isDeleting}
                                    className="px-3 py-2 border border-red-200 text-red-600 rounded-lg hover:bg-red-50 transition-colors text-xs font-bold disabled:opacity-50"
                                >
                                    🗑️ delete lead
                                </button>
                            </div>
                        </div>

                        {/* Templates Sent History */}
                        {messages.some(m => m.direction === 'outbound' && m.template_name) && (
                            <div className="mt-4 pt-4 border-t border-stone-300">
                                <label className="text-[10px] font-bold text-slate-600 uppercase tracking-wider block mb-2">📜 Templates Sent to Lead</label>
                                <div className="flex flex-wrap gap-1.5">
                                    {Array.from(new Set(
                                        messages
                                            .filter(m => m.direction === 'outbound' && m.template_name)
                                            .map(m => m.template_name as string)
                                    )).map(tName => (
                                        <span key={tName} className="px-2 py-0.5 bg-stone-100 text-stone-600 rounded text-[10px] font-bold border border-stone-200">
                                            {tName}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Right Column: WhatsApp Chat History (45%) */}
            <div className="w-[45%] flex flex-col h-full bg-[#e5ddd5]">
                {/* Chat Header */}
                <div className="px-4 py-3 bg-gray-100 border-b border-gray-200 flex items-center gap-3">
                    <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                        {leadDetail.first_name[0]}{leadDetail.last_name?.[0] || ''}
                    </div>
                    <div>
                        <p className="text-sm font-bold text-gray-800 leading-none">{leadDetail.first_name} {leadDetail.last_name || ''}</p>
                        <p className="text-[10px] text-green-600 font-semibold mt-1">WhatsApp Conversation</p>
                    </div>
                </div>

                {/* Chat Content */}
                <WhatsAppChatHistory
                    messages={messages}
                    loading={loadingMessages}
                />
            </div>
        </div>
    );
}
