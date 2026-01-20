'use client';

import {
    ArrowLeft,
    Briefcase,
    CheckCircle2,
    LayoutDashboard,
    Loader2,
    Megaphone,
    Rocket,
    ShieldAlert,
    Sparkles
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { fetchEnrichmentLeads, fetchLeads } from '../services/campaign-service/api';
import { Lead } from '../types/email-outreach/types';

export default function MasterLeadsPage() {
    const [verifiedLeads, setVerifiedLeads] = useState<Lead[]>([]);
    const [enrichmentLeads, setEnrichmentLeads] = useState<Lead[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'verified' | 'enrichment'>('verified');

    useEffect(() => {
        loadAllData();
    }, []);

    const loadAllData = async () => {
        setLoading(true);
        try {
            // Parallel Fetch: Fastest way to get both without blocking
            const [verifiedData, enrichmentData] = await Promise.all([
                fetchLeads(),             // Your campaign leads
                fetchEnrichmentLeads()    // Your missing data leads
            ]);

            setVerifiedLeads(verifiedData.leads);
            setEnrichmentLeads(enrichmentData);
        } catch (error) {
            console.error("Failed to load master data", error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 font-sans">

            {/* --- TOP NAVIGATION BAR --- */}
            <div className="bg-purple-200 border-b border-slate-200 px-8 py-4 flex justify-between items-center sticky top-0 z-10">
                <div className="flex items-center gap-6">
                    <Link href="/" className="text-slate-500 hover:text-slate-800 transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                        <LayoutDashboard className="w-6 h-6 text-indigo-600" />
                        Master Lead Database
                    </h1>
                </div>

                <div className="flex gap-3">
                    <Link href="/campaign">
                        <button className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 rounded-lg text-slate-700 font-medium hover:bg-slate-50 text-sm transition-all">
                            <Megaphone className="w-4 h-4 text-indigo-600" />
                            Go to Campaign
                        </button>
                    </Link>
                    <Link href="/enrichment">
                        <button className="flex items-center gap-2 px-4 py-2 bg-amber-100 border border-slate-300 rounded-lg text-slate-700 font-medium hover:bg-slate-50 text-sm transition-all">
                            <Sparkles className="w-4 h-4 text-amber-500" />
                            Go to Enrichment
                        </button>
                    </Link>
                </div>
            </div>

            {/* --- MAIN CONTENT AREA --- */}
            <div className="max-w-7xl mx-auto p-8">

                {/* Statistics Cards */}
                <div className="grid grid-cols-2 gap-6 mb-8">
                    <div
                        onClick={() => setActiveTab('verified')}
                        className={`p-6 rounded-2xl border-2 cursor-pointer transition-all ${activeTab === 'verified' ? 'border-indigo-600 bg-indigo-50/50 shadow-md' : 'border-white bg-white hover:border-indigo-200'}`}
                    >
                        <div className="flex items-center justify-between mb-2">
                            <h3 className="font-bold text-slate-700">Campaign Ready</h3>
                            <CheckCircle2 className={`w-5 h-5 ${activeTab === 'verified' ? 'text-indigo-600' : 'text-slate-400'}`} />
                        </div>
                        <p className="text-3xl font-extrabold text-slate-900">{verifiedLeads.length}</p>
                        <p className="text-sm text-slate-500 mt-1">Leads with full data & signals</p>
                    </div>

                    <div
                        onClick={() => setActiveTab('enrichment')}
                        className={`p-6 rounded-2xl border-2 cursor-pointer transition-all ${activeTab === 'enrichment' ? 'border-amber-500 bg-amber-50/50 shadow-md' : 'border-white bg-white hover:border-amber-200'}`}
                    >
                        <div className="flex items-center justify-between mb-2">
                            <h3 className="font-bold text-slate-700">Needs Enrichment</h3>
                            <ShieldAlert className={`w-5 h-5 ${activeTab === 'enrichment' ? 'text-amber-500' : 'text-slate-400'}`} />
                        </div>
                        <p className="text-3xl font-extrabold text-slate-900">{enrichmentLeads.length}</p>
                        <p className="text-sm text-slate-500 mt-1">Missing Mobile or LinkedIn</p>
                    </div>
                </div>

                {/* THE LIST VIEW */}
                <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden min-h-[500px]">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center h-96">
                            <Loader2 className="w-10 h-10 text-indigo-600 animate-spin mb-4" />
                            <p className="text-slate-500">Fetching lead data...</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead className="bg-slate-50 border-b border-slate-200">
                                    <tr>
                                        <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Name</th>
                                        <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Role & Company</th>
                                        <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">
                                            {activeTab === 'verified' ? 'Hiring Signals' : 'Missing Data'}
                                        </th>
                                        <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Status</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    {(activeTab === 'verified' ? verifiedLeads : enrichmentLeads).map((lead) => (
                                        <tr key={lead.id} className="hover:bg-slate-50/80 transition-colors group">
                                            <td className="px-6 py-4">
                                                <div className="font-semibold text-slate-900">{lead.first_name} {lead.last_name}</div>
                                                <div className="text-xs text-slate-500">{lead.email}</div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-2">
                                                    <Briefcase className="w-3 h-3 text-slate-400" />
                                                    <span className="text-sm text-slate-700">{lead.designation}</span>
                                                </div>
                                                <div className="text-xs text-slate-500 ml-5">{lead.company_name}</div>
                                            </td>
                                            <td className="px-6 py-4">
                                                {activeTab === 'verified' ? (
                                                    // VERIFIED VIEW: Show Hiring Signal
                                                    lead.hiring_signal ? (
                                                        <div className="flex flex-col items-start gap-1">
                                                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 border border-green-200">
                                                                <Rocket className="w-3 h-3" /> Hiring Detected
                                                            </span>
                                                            <span className="text-xs text-slate-500 truncate max-w-[200px]" title={lead.ai_variables?.hiring_roles}>
                                                                {lead.ai_variables?.hiring_roles || "Generic roles"}
                                                            </span>
                                                        </div>
                                                    ) : (
                                                        <span className="text-xs text-slate-400 italic">No signal detected</span>
                                                    )
                                                ) : (
                                                    // ENRICHMENT VIEW: Show Missing Fields
                                                    <div className="flex gap-2">
                                                        {!lead.mobile_number && <span className="px-2 py-0.5 bg-red-50 text-red-600 text-xs rounded border border-red-100">No Mobile</span>}
                                                        {!lead.linkedin_url && <span className="px-2 py-0.5 bg-red-50 text-red-600 text-xs rounded border border-red-100">No LinkedIn</span>}
                                                        {!lead.company_name && <span className="px-2 py-0.5 bg-red-50 text-red-600 text-xs rounded border border-red-100">No Company</span>}
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                {activeTab === 'verified' ? (
                                                    <span className="px-3 py-1 bg-indigo-100 text-indigo-700 text-xs font-bold rounded-full">
                                                        Active
                                                    </span>
                                                ) : (
                                                    <Link href="/enrichment">
                                                        <button className="text-xs font-medium text-amber-600 hover:text-amber-800 hover:underline">
                                                            Fix Now →
                                                        </button>
                                                    </Link>
                                                )}
                                            </td>
                                        </tr>
                                    ))}

                                    {/* EMPTY STATE */}
                                    {(activeTab === 'verified' ? verifiedLeads : enrichmentLeads).length === 0 && (
                                        <tr>
                                            <td colSpan={4} className="px-6 py-12 text-center text-slate-400">
                                                No leads found in this category.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}