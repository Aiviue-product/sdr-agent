'use client';

import {
    AlertTriangle,
    ArrowLeft,
    Loader2,
    Sparkles
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { fetchEnrichmentLeads } from '../services/campaign-service/api';
import { Lead } from '../types/email-outreach/types';

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

    // Helper to visually show what is missing
    const getMissingFields = (lead: Lead) => {
        let missing = [];
        if (!lead.mobile_number) missing.push('Mobile');
        if (!lead.linkedin_url) missing.push('LinkedIn');
        if (!lead.company_name) missing.push('Company');
        return missing;
    };

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
                        These {leads.length} leads are valid but need more data before outreach.
                    </p>
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
                                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Missing Data Points</th>
                                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 bg-white">
                            {leads.map((lead) => (
                                <tr key={lead.id} className="hover:bg-yellow-50/30 transition-colors">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center">
                                            <div className="flex-shrink-0 h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold">
                                                {lead.first_name?.[0]}{lead.last_name?.[0]}
                                            </div>
                                            <div className="ml-4">
                                                <div className="text-sm font-medium text-gray-900">{lead.first_name} {lead.last_name}</div>
                                                <div className="text-sm text-gray-500">{lead.email}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex gap-2">
                                            {getMissingFields(lead).map(field => (
                                                <span key={field} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 border border-red-200">
                                                    <AlertTriangle className="w-3 h-3 mr-1" />
                                                    Missing {field}
                                                </span>
                                            ))}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right">
                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-sm font-medium text-yellow-600 bg-yellow-50">
                                            Needs Review
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}