'use client';

import {
    AlertTriangle,
    ArrowLeft,
    Loader2,
    Mail,
    Sparkles
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { fetchEnrichmentLeads } from '../services/campaign-service/api';
import { Lead } from '../types/email-outreach/types';

// Type for enrichment issues
interface EnrichmentIssue {
    field: string;
    type: 'profile' | 'email';
    severity: 'error' | 'warning';
}

export default function EnrichmentPage() {
    const [leads, setLeads] = useState<Lead[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadEnrichmentLeads();
    }, []);

    const loadEnrichmentLeads = async () => {
        try {
            const data = await fetchEnrichmentLeads();
            setLeads(data);
        } catch (err) {
            console.error("Failed to load enrichment leads", err);
        } finally {
            setLoading(false);
        }
    };

    // Helper to get all enrichment issues for a lead
    const getEnrichmentIssues = (lead: Lead): EnrichmentIssue[] => {
        const issues: EnrichmentIssue[] = [];
        
        // Check for email enrichment needs (invalid/catch-all emails)
        if (lead.lead_stage === 'email_enrichment') {
            if (lead.verification_status === 'catch-all') {
                issues.push({ field: 'Risky Email', type: 'email', severity: 'warning' });
            } else {
                // invalid, api_error, etc.
                issues.push({ field: 'Invalid Email', type: 'email', severity: 'error' });
            }
        }
        
        // Check for profile enrichment needs (missing fields)
        if (!lead.mobile_number) issues.push({ field: 'Mobile', type: 'profile', severity: 'error' });
        if (!lead.linkedin_url) issues.push({ field: 'LinkedIn', type: 'profile', severity: 'error' });
        if (!lead.company_name) issues.push({ field: 'Company', type: 'profile', severity: 'error' });
        
        return issues;
    };

    // Count leads by enrichment type
    const emailEnrichmentCount = leads.filter(l => l.lead_stage === 'email_enrichment').length;
    const profileEnrichmentCount = leads.length - emailEnrichmentCount;

    return (
        <div className="min-h-screen bg-gray-50 font-sans p-8">

            {/* Header */}
            <div className="max-w-6xl mx-auto mb-8 flex justify-between items-center">
                <div>
                    {/* --- CHANGED HREF FROM "/" TO "/campaign" --- */}
                    <Link href="/" className="text-gray-500 hover:text-gray-800 flex items-center gap-1 mb-2 text-sm font-medium transition-colors">
                        <ArrowLeft className="w-4 h-4" /> Back to Home
                    </Link>

                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                        <Sparkles className="w-6 h-6 text-yellow-500" />
                        Enrichment Pool
                    </h1>
                    <p className="text-gray-500 mt-1">
                        {leads.length} leads need enrichment before outreach.
                    </p>
                    
                    {/* Stats badges */}
                    {leads.length > 0 && (
                        <div className="flex gap-3 mt-2">
                            {emailEnrichmentCount > 0 && (
                                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-700 border border-orange-200">
                                    <Mail className="w-3 h-3 mr-1" />
                                    {emailEnrichmentCount} need email fix
                                </span>
                            )}
                            {profileEnrichmentCount > 0 && (
                                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700 border border-red-200">
                                    <AlertTriangle className="w-3 h-3 mr-1" />
                                    {profileEnrichmentCount} missing profile data
                                </span>
                            )}
                        </div>
                    )}
                </div>

                <button
                    onClick={() => toast('Enrichment coming soon! This will auto-find Mobile & LinkedIn.', { icon: '🚧' })}
                    className="flex items-center gap-2 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-white px-6 py-3 rounded-xl font-bold shadow-lg shadow-yellow-200 transition-all transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={leads.length === 0}
                >
                    <Sparkles className="w-5 h-5" />
                    Perform Enrichment
                </button>
            </div>

            {/* Content Table */}
            <div className="max-w-6xl mx-auto bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                {loading ? (
                    <div className="flex flex-col items-center justify-center p-20 text-gray-400">
                        <Loader2 className="w-10 h-10 animate-spin mb-4 text-indigo-600" />
                        <p>Scanning leads needing enrichment...</p>
                    </div>
                ) : leads.length === 0 ? (
                    <div className="text-center p-20 bg-gray-50">
                        <div className="bg-green-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Sparkles className="w-8 h-8 text-green-600" />
                        </div>
                        <h3 className="text-lg font-bold text-gray-900">All Clean!</h3>
                        <p className="text-gray-500">No leads require enrichment right now.</p>
                    </div>
                ) : (
                    <table className="min-w-full divide-y divide-gray-100">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Lead Details</th>
                                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Enrichment Needed</th>
                                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Type</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 bg-white">
                            {leads.map((lead) => {
                                const issues = getEnrichmentIssues(lead);
                                const isEmailIssue = lead.lead_stage === 'email_enrichment';
                                
                                return (
                                    <tr key={lead.id} className={`hover:bg-yellow-50/30 transition-colors ${isEmailIssue ? 'bg-orange-50/20' : ''}`}>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center">
                                                <div className={`flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center font-bold ${
                                                    isEmailIssue 
                                                        ? 'bg-orange-100 text-orange-700' 
                                                        : 'bg-indigo-100 text-indigo-700'
                                                }`}>
                                                    {lead.first_name?.[0]}{lead.last_name?.[0]}
                                                </div>
                                                <div className="ml-4">
                                                    <div className="text-sm font-medium text-gray-900">{lead.first_name} {lead.last_name}</div>
                                                    <div className={`text-sm ${isEmailIssue ? 'text-orange-600 line-through' : 'text-gray-500'}`}>
                                                        {lead.email}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex flex-wrap gap-2">
                                                {issues.map((issue, idx) => (
                                                    <span 
                                                        key={idx} 
                                                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                                                            issue.type === 'email'
                                                                ? issue.severity === 'warning'
                                                                    ? 'bg-yellow-100 text-yellow-800 border-yellow-200'
                                                                    : 'bg-orange-100 text-orange-800 border-orange-200'
                                                                : 'bg-red-100 text-red-800 border-red-200'
                                                        }`}
                                                    >
                                                        {issue.type === 'email' 
                                                            ? <Mail className="w-3 h-3 mr-1" />
                                                            : <AlertTriangle className="w-3 h-3 mr-1" />
                                                        }
                                                        {issue.type === 'email' ? issue.field : `Missing ${issue.field}`}
                                                    </span>
                                                ))}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-sm font-medium ${
                                                isEmailIssue 
                                                    ? 'text-orange-600 bg-orange-50' 
                                                    : 'text-yellow-600 bg-yellow-50'
                                            }`}>
                                                {isEmailIssue ? 'Email Issue' : 'Profile Incomplete'}
                                            </span>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}