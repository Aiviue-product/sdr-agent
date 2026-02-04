"use client";

import {
    ArrowLeft,
    Building2,
    Clock,
    Copy,
    ExternalLink,
    Loader2,
    MessageSquare,
    RefreshCw,
    Rocket,
    Send,
    User,
    UserPlus
} from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import {
    fetchLinkedInLeadDetail,
    refreshLeadAnalysis,
    sendConnectionRequest,
    sendDM
} from '../../../../services/linkedin-service/api';
import { LinkedInLeadDetail } from '../../../../types/linkedin';

export default function LeadDetailPage() {
    const params = useParams();
    const leadId = params?.id ? parseInt(params.id as string, 10) : NaN;

    const [lead, setLead] = useState<LinkedInLeadDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [isSendingDM, setIsSendingDM] = useState(false);
    const [isSendingConnection, setIsSendingConnection] = useState(false);
    const [imageError, setImageError] = useState(false);

    const loadLead = useCallback(async () => {
        if (!leadId || isNaN(leadId)) return;
        setLoading(true);
        try {
            const data = await fetchLinkedInLeadDetail(leadId);
            setLead(data);
        } catch (err) {
            console.error('Failed to load lead:', err);
            toast.error('Failed to load lead details');
        } finally {
            setLoading(false);
        }
    }, [leadId]);

    useEffect(() => {
        loadLead();
    }, [loadLead]);

    // Polling for DM generation status
    useEffect(() => {
        if (!lead || lead.dm_generation_status !== 'pending') return;

        const interval = setInterval(async () => {
            try {
                const updated = await fetchLinkedInLeadDetail(leadId);
                setLead(updated);
                if (updated.dm_generation_status !== 'pending') {
                    clearInterval(interval);
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        }, 3000);

        return () => clearInterval(interval);
    }, [lead?.dm_generation_status, leadId]);

    const handleRefresh = async () => {
        setIsRefreshing(true);
        try {
            await refreshLeadAnalysis(leadId);
            toast.success('Analysis refreshed');
            await loadLead();
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Refresh failed');
        } finally {
            setIsRefreshing(false);
        }
    };

    const handleSendDM = async () => {
        setIsSendingDM(true);
        try {
            const result = await sendDM(leadId);
            if (result.success) {
                toast.success('DM sent successfully');
                await loadLead();
            } else {
                toast.error(result.error || 'Failed to send DM');
            }
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Failed to send DM');
        } finally {
            setIsSendingDM(false);
        }
    };

    const handleSendConnection = async () => {
        setIsSendingConnection(true);
        try {
            const result = await sendConnectionRequest(leadId);
            if (result.success) {
                toast.success('Connection request sent');
                await loadLead();
            } else {
                toast.error(result.error || 'Failed to send connection');
            }
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Failed to send connection');
        } finally {
            setIsSendingConnection(false);
        }
    };

    const copyDmToClipboard = () => {
        if (lead?.linkedin_dm) {
            navigator.clipboard.writeText(lead.linkedin_dm);
            toast.success('DM copied to clipboard');
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
                <span className="ml-3 text-gray-600">Loading lead details...</span>
            </div>
        );
    }

    if (!lead) {
        return (
            <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center">
                <User className="w-16 h-16 text-gray-300 mb-4" />
                <h2 className="text-xl font-semibold text-gray-600 mb-2">Lead not found</h2>
                <Link
                    href="/linkedin-signals/leads"
                    className="text-teal-600 hover:text-teal-700 flex items-center gap-1"
                >
                    <ArrowLeft className="w-4 h-4" /> Back to All Leads
                </Link>
            </div>
        );
    }

    const dmStatus = lead.dm_generation_status;
    const isGenerating = dmStatus === 'pending';
    const hasFailed = dmStatus === 'failed';
    const hasGeneratedDM = lead.linkedin_dm && dmStatus === 'generated';

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <div className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
                <div className="max-w-4xl mx-auto px-6 py-4">
                    <div className="flex items-center justify-between">
                        <Link
                            href="/linkedin-signals/leads"
                            className="text-gray-500 hover:text-gray-800 flex items-center gap-1 text-sm font-medium transition-colors"
                        >
                            <ArrowLeft className="w-4 h-4" /> Back to All Leads
                        </Link>

                        <div className="flex items-center gap-2">
                            <button
                                onClick={handleRefresh}
                                disabled={isRefreshing}
                                className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
                            >
                                <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                                Refresh
                            </button>
                            <a
                                href={lead.linkedin_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                            >
                                <ExternalLink className="w-4 h-4" /> LinkedIn Profile
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="max-w-4xl mx-auto px-6 py-8">
                {/* Profile Card */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
                    <div className="flex items-start gap-4">
                        {/* Avatar */}
                        <div className={`w-20 h-20 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden
                            ${lead.is_company ? 'bg-purple-100' : 'bg-blue-100'}`}
                        >
                            {lead.profile_image_url && !imageError ? (
                                <img
                                    src={lead.profile_image_url}
                                    alt={lead.full_name}
                                    className="w-full h-full object-cover"
                                    referrerPolicy="no-referrer"
                                    onError={() => setImageError(true)}
                                />
                            ) : lead.is_company ? (
                                <Building2 className="w-10 h-10 text-purple-600" />
                            ) : (
                                <User className="w-10 h-10 text-blue-600" />
                            )}
                        </div>

                        {/* Info */}
                        <div className="flex-1">
                            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                                {lead.full_name}
                                {lead.hiring_signal && (
                                    <span className="flex items-center gap-1 text-sm bg-green-100 text-green-700 px-3 py-1 rounded-full font-medium">
                                        <Rocket className="w-4 h-4" /> Hiring
                                    </span>
                                )}
                            </h1>
                            <p className="text-gray-600 mt-1">{lead.headline || 'No headline'}</p>
                            {lead.company_name && (
                                <p className="text-gray-500 text-sm mt-1">at {lead.company_name}</p>
                            )}

                            {/* Status Tags */}
                            <div className="flex flex-wrap gap-2 mt-3">
                                {lead.search_keyword && (
                                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                                        Keyword: {lead.search_keyword}
                                    </span>
                                )}
                                {lead.connection_status === 'connected' && (
                                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded font-medium">
                                        Connected
                                    </span>
                                )}
                                {lead.connection_status === 'pending' && (
                                    <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded font-medium">
                                        Connection Pending
                                    </span>
                                )}
                                {lead.is_dm_sent && (
                                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded font-medium">
                                        DM Sent ✓
                                    </span>
                                )}
                            </div>

                            {/* Hiring Roles */}
                            {lead.hiring_signal && lead.hiring_roles && (
                                <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                                    <h4 className="text-sm font-semibold text-green-800 mb-1">🏢 Hiring For:</h4>
                                    <p className="text-sm text-green-700">{lead.hiring_roles}</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Actions */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
                    <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                        <Send className="w-5 h-5 text-teal-600" /> Actions
                    </h2>
                    <div className="flex flex-wrap gap-3">
                        <button
                            onClick={handleSendConnection}
                            disabled={isSendingConnection || lead.connection_status === 'connected'}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {isSendingConnection ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <UserPlus className="w-4 h-4" />
                            )}
                            {lead.connection_status === 'connected' ? 'Already Connected' : 'Send Connection'}
                        </button>

                        <button
                            onClick={handleSendDM}
                            disabled={isSendingDM || !lead.linkedin_dm || lead.is_dm_sent}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {isSendingDM ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <MessageSquare className="w-4 h-4" />
                            )}
                            {lead.is_dm_sent ? 'DM Already Sent' : 'Send DM'}
                        </button>
                    </div>
                </div>

                {/* Generated DM */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
                    <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                        <MessageSquare className="w-5 h-5 text-teal-600" /> Generated DM
                    </h2>

                    {isGenerating && (
                        <div className="flex items-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                            <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                            <div>
                                <p className="text-blue-800 font-medium">Generating DM...</p>
                                <p className="text-blue-600 text-sm">This may take a few seconds.</p>
                            </div>
                        </div>
                    )}

                    {hasFailed && (
                        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                            <p className="text-red-800 font-medium">DM generation failed</p>
                            <p className="text-red-600 text-sm mt-1">
                                Rate limiting may have occurred. Please click the Refresh button to try again.
                            </p>
                        </div>
                    )}

                    {hasGeneratedDM && (
                        <div className="relative">
                            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg whitespace-pre-wrap text-gray-800">
                                {lead.linkedin_dm}
                            </div>
                            <button
                                onClick={copyDmToClipboard}
                                className="absolute top-2 right-2 p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                                title="Copy to clipboard"
                            >
                                <Copy className="w-4 h-4 text-gray-600" />
                            </button>
                        </div>
                    )}

                    {!isGenerating && !hasFailed && !hasGeneratedDM && (
                        <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-gray-500 italic">
                            No DM generated yet. Click Refresh to generate one.
                        </div>
                    )}
                </div>

                {/* Post Data */}
                {lead.post_data && lead.post_data.length > 0 && (
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                        <h2 className="text-lg font-semibold text-gray-800 mb-4">📝 LinkedIn Posts</h2>
                        <div className="space-y-4">
                            {lead.post_data.map((post, idx) => (
                                <div key={idx} className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
                                    {post.posted_at?.date && (
                                        <p className="text-xs text-gray-400 mb-2 flex items-center gap-1">
                                            <Clock className="w-3 h-3" />
                                            {new Date(post.posted_at.date).toLocaleDateString()}
                                        </p>
                                    )}
                                    <p className="text-gray-800 text-sm whitespace-pre-wrap">
                                        {post.text.length > 500 ? post.text.slice(0, 500) + '...' : post.text}
                                    </p>
                                    {post.search_keyword && (
                                        <span className="inline-block mt-2 text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">
                                            {post.search_keyword}
                                        </span>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
