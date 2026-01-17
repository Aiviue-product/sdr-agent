'use client';

import { Building2, Loader2, Mail, MessageCircle, Phone, Rocket, User } from 'lucide-react';
import { LinkedInLeadDetail } from '../../types/linkedin';
import DmPreviewCard from './DmPreviewCard';
import LeadActionButtons from './LeadActionButtons';

interface LeadDetailPanelProps {
    leadDetail: LinkedInLeadDetail | null;
    loading: boolean;
    onRefresh: () => void;
    onSendConnection: () => void;
    onSendDM: () => void;
    onOpenActivity: (leadId?: number, leadName?: string) => void;
    onOpenProfile: () => void;
    onCopyDm: () => void;
    isRefreshing: boolean;
    isSendingConnection: boolean;
    isSendingDM: boolean;
}

export default function LeadDetailPanel({
    leadDetail,
    loading,
    onRefresh,
    onSendConnection,
    onSendDM,
    onOpenActivity,
    onOpenProfile,
    onCopyDm,
    isRefreshing,
    isSendingConnection,
    isSendingDM
}: LeadDetailPanelProps) {
    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            </div>
        );
    }

    if (!leadDetail) {
        return (
            <div className="flex-1 flex items-center justify-center text-gray-400">
                <div className="text-center">
                    <MessageCircle className="w-12 h-12 mx-auto mb-4 opacity-30" />
                    <p>Select a lead to view details</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col overflow-hidden">
            {/* --- COMPACT HEADER --- */}
            <div className="bg-white border-b border-pink-200 shadow-sm flex-shrink-0">
                <div className="max-w-5xl mx-auto p-4 md:p-6 pb-4">
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                        <div className="flex items-center gap-4 min-w-0">
                            {leadDetail.profile_image_url ? (
                                <img
                                    src={leadDetail.profile_image_url}
                                    alt={leadDetail.full_name}
                                    className="w-14 h-14 rounded-full object-cover border-2 border-gray-100 shadow-sm"
                                />
                            ) : (
                                <div className={`w-14 h-14 rounded-full flex items-center justify-center
                                    ${leadDetail.is_company ? 'bg-purple-100' : 'bg-blue-100'}`}
                                >
                                    {leadDetail.is_company ? (
                                        <Building2 className="w-7 h-7 text-purple-600" />
                                    ) : (
                                        <User className="w-7 h-7 text-blue-600" />
                                    )}
                                </div>
                            )}

                            <div className="min-w-0">
                                <div className="flex items-center gap-3">
                                    <h2 className="text-xl font-bold text-gray-900 truncate">
                                        {leadDetail.full_name}
                                    </h2>
                                    {leadDetail.hiring_signal && (
                                        <span className="bg-green-100 text-green-700 text-[10px] px-2 py-0.5 rounded-full border border-green-200 flex items-center gap-1 font-bold whitespace-nowrap">
                                            <Rocket className="w-3 h-3" /> HIRING
                                        </span>
                                    )}
                                </div>
                                <p className="text-sm text-gray-500 font-medium truncate max-w-md">
                                    {leadDetail.headline}
                                </p>
                            </div>
                        </div>

                        <div className="flex-shrink-0">
                            <LeadActionButtons
                                lead={leadDetail}
                                onOpenProfile={onOpenProfile}
                                onRefresh={onRefresh}
                                onSendConnection={onSendConnection}
                                onSendDM={onSendDM}
                                onOpenActivity={() => leadDetail && onOpenActivity(leadDetail.id, leadDetail.full_name)}
                                isRefreshing={isRefreshing}
                                isSendingConnection={isSendingConnection}
                                isSendingDM={isSendingDM}
                            />
                        </div>
                    </div>

                    {/* Horizontal Meta Row */}
                    {(leadDetail.hiring_roles || (leadDetail.ai_variables as any)?.company_hiring) && (
                        <div className="mt-4 pt-3 border-t border-gray-50 flex flex-wrap items-center gap-4 text-sm">
                            {leadDetail.hiring_roles && (
                                <div className="flex items-center gap-2 bg-green-50/50 px-3 py-1 rounded-lg border border-green-100/50">
                                    <span className="text-green-600 font-bold text-[10px] uppercase tracking-tighter">Looking for:</span>
                                    <span className="text-green-800 font-semibold">{leadDetail.hiring_roles}</span>
                                </div>
                            )}

                            {(leadDetail.ai_variables as any)?.company_hiring && (
                                <div className="flex items-center gap-1.5 text-gray-600 text-xs">
                                    <Building2 className="w-3.5 h-3.5 text-blue-500" />
                                    <span className="text-gray-400 font-bold uppercase tracking-tighter">Company:</span>
                                    <span className="font-semibold text-gray-800">{(leadDetail.ai_variables as any).company_hiring}</span>
                                </div>
                            )}

                            <div className="flex items-center gap-3 ml-auto">
                                {(leadDetail.ai_variables as any)?.contact_email && (
                                    <div className="flex items-center gap-1.5 text-xs text-purple-600 hover:text-purple-700 transition-colors">
                                        <Mail className="w-3.5 h-3.5" />
                                        <span className="font-medium">{(leadDetail.ai_variables as any).contact_email}</span>
                                    </div>
                                )}
                                {(leadDetail.ai_variables as any)?.contact_phone && (
                                    <div className="flex items-center gap-1.5 text-xs text-amber-600">
                                        <Phone className="w-3.5 h-3.5" />
                                        <span className="font-medium">{(leadDetail.ai_variables as any).contact_phone}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* --- CONTENT AREA --- */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6 bg-gray-50/50">
                <div className="max-w-5xl mx-auto space-y-6">
                    {/* DM Preview takes prominence */}
                    <DmPreviewCard
                        dm={leadDetail.linkedin_dm}
                        onCopy={onCopyDm}
                    />

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Main Analysis Column */}
                        <div className="lg:col-span-2 space-y-6">
                            {leadDetail.pain_points && (
                                <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-5">
                                    <div className="flex items-center gap-2 mb-4">
                                        <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600">
                                            <Rocket className="w-4 h-4" />
                                        </div>
                                        <h4 className="font-bold text-gray-800 uppercase tracking-tight text-[11px]">Identified Pain Points</h4>
                                    </div>
                                    <p className="text-gray-700 text-sm leading-relaxed">{leadDetail.pain_points}</p>
                                </div>
                            )}

                            {leadDetail.post_data && leadDetail.post_data.length > 0 && (
                                <div className="bg-cyan-50 rounded-xl shadow-sm border border-gray-200/60 overflow-hidden">
                                    <div className="p-4 bg-gray-50/80 border-b border-gray-100 flex items-center justify-between">
                                        <h3 className="font-bold text-gray-800 text-[11px] uppercase tracking-tight">
                                            📄 Recent Posts ({leadDetail.post_data.length})
                                        </h3>
                                    </div>
                                    <div className="divide-y divide-gray-100 max-h-[500px] overflow-y-auto">
                                        {leadDetail.post_data.map((post, idx) => (
                                            <div key={post.activity_id || idx} className="p-5 hover:bg-gray-50/50 transition-colors">
                                                <div className="flex items-center justify-between mb-3">
                                                    <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                                                        {post.posted_at?.date || 'Unknown date'}
                                                    </span>
                                                    <span className="text-[10px] bg-blue-50 text-blue-600 px-2.5 py-1 rounded font-bold uppercase">
                                                        {post.search_keyword || 'N/A'}
                                                    </span>
                                                </div>
                                                <p className="text-gray-600 text-sm whitespace-pre-wrap leading-relaxed">
                                                    {post.text || 'No text available'}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Sidebar Column for Metadata */}
                        <div className="space-y-4">
                            <div className="bg-stone-200 rounded-xl shadow-sm border border-gray-200/60 p-5">
                                <h4 className="text-[10px] font-bold text-stone-500 uppercase tracking-widest mb-4">Search Context</h4>
                                <div className="space-y-4">
                                    <div className="flex items-start justify-between">
                                        <span className="text-xs text-stone-500 font-medium">Lead Type</span>
                                        <span className="text-xs font-bold text-gray-700">
                                            {leadDetail.is_company ? '🏢 Company' : '👤 Professional'}
                                        </span>
                                    </div>
                                    <div className="flex items-start justify-between">
                                        <span className="text-xs text-stone-500 font-medium">Source Keyword</span>
                                        <span className="text-xs font-bold text-gray-700">{leadDetail.search_keyword || 'N/A'}</span>
                                    </div>
                                    <div className="pt-3 border-t border-gray-50">
                                        <span className="text-[10px] text-stone-500 font-bold block mb-2 uppercase tracking-tighter">Profile URL</span>
                                        <a
                                            href={leadDetail.linkedin_url || '#'}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-xs text-blue-600 hover:underline font-medium break-all block"
                                        >
                                            {leadDetail.linkedin_url}
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
