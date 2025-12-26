/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import {
    BrainCircuit,
    Briefcase,
    CheckCircle2,
    ChevronRight,
    Clock,
    Loader2,
    Mail,
    Rocket,
    Send,
    Sparkles,
    User
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import {
    enrichLead,
    fetchLeadDetails,
    fetchLeads,
    sendEmailMock,
    sendSequenceToInstantly
} from '../services/campaign-service/api';

import { Lead } from "../types/types";

export default function CampaignPage() {
    const [leads, setLeads] = useState<Lead[]>([]);
    const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
    const [selectedLeadDetail, setSelectedLeadDetail] = useState<Lead | null>(null);
    const [loadingList, setLoadingList] = useState(true);
    const [loadingDetail, setLoadingDetail] = useState(false);

    // Loading state for the Personalize Button
    const [isEnriching, setIsEnriching] = useState(false);

    // 1. Load the List on Mount
    useEffect(() => {
        loadLeads();
    }, []);

    // 2. Load Details when a lead is clicked
    useEffect(() => {
        if (selectedLeadId) {
            loadSingleLead(selectedLeadId);
        }
    }, [selectedLeadId]);

    const loadLeads = async () => {
        try {
            const data = await fetchLeads();
            setLeads(data);
            if (data.length > 0 && !selectedLeadId) setSelectedLeadId(data[0].id); // Auto-select first
        } catch (err) {
            console.error(err);
        } finally {
            setLoadingList(false);
        }
    };

    const loadSingleLead = async (id: number) => {
        setLoadingDetail(true);
        try {
            const data = await fetchLeadDetails(id);
            setSelectedLeadDetail(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoadingDetail(false);
        }
    };

    // --- HANDLE AI PERSONALIZATION ---
    // This function now uses the "Smart Backend". 
    // If data exists, it won't re-scrape, it will just re-run AI (Fast Rewrite).
    const handleEnrichment = async () => {
        if (!selectedLeadId) return;
        setIsEnriching(true);

        try {
            // 1. Call Backend (Scrape + AI Analysis)
            await enrichLead(selectedLeadId);

            // 2. Refresh Lead Details (To pull the new Email Body with the Hook)
            await loadSingleLead(selectedLeadId);

            // 3. Refresh Lead List (To show the 'Hiring' badge in sidebar)
            loadLeads();

            alert("✨ Personalization Complete! Email updated.");

        } catch (error: any) {
            console.error("Enrichment failed", error);
            alert(`❌ Failed: ${error.message}`);
        } finally {
            setIsEnriching(false);
        }
    };

    const updateLocalEmailBody = (templateKey: 'email_1_body' | 'email_2_body' | 'email_3_body', newText: string) => {
        if (!selectedLeadDetail) return;
        setSelectedLeadDetail({
            ...selectedLeadDetail,
            [templateKey]: newText
        });
    };

    const handlePushSequence = async () => {
        if (!selectedLeadDetail || !selectedLeadId) return;
        try {
            alert("🚀 Pushing full sequence to Instantly...");
            await sendSequenceToInstantly(selectedLeadId, {
                email_1: selectedLeadDetail.email_1_body || "",
                email_2: selectedLeadDetail.email_2_body || "",
                email_3: selectedLeadDetail.email_3_body || ""
            });
            alert("✅ Lead & Sequence added successfully!");
        } catch (error) {
            console.error(error);
            alert("❌ Failed to push sequence.");
        }
    };

    const handleSend = async (templateId: number) => {
        if (!selectedLeadDetail || !selectedLeadId) return;
        let finalBody = "";
        if (templateId === 1) finalBody = selectedLeadDetail.email_1_body || "";
        if (templateId === 2) finalBody = selectedLeadDetail.email_2_body || "";
        if (templateId === 3) finalBody = selectedLeadDetail.email_3_body || "";

        try {
            alert(` Sending to Instantly.ai...`);
            await sendEmailMock(selectedLeadId, templateId, finalBody);
            alert("✅ Sent successfully!");
        } catch (error) {
            console.error("Failed to send", error);
            alert("❌ Failed to send email.");
        }
    };

    return (
        <div className="flex h-screen bg-gray-50 font-sans">

            {/* --- LEFT SIDEBAR: LEAD LIST --- */}
            <div className="w-1/3 border-r border-gray-200 bg-white flex flex-col">
                <div className="p-5 border-b border-gray-100">
                    <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                        <User className="w-5 h-5 text-indigo-600" />
                        Verified Leads
                    </h1>
                    <p className="text-sm text-gray-500 mt-1">{leads.length} potential candidates ready</p>
                </div>

                <div className="flex-1 overflow-y-auto">
                    {loadingList ? (
                        <div className="flex justify-center p-10"><Loader2 className="animate-spin text-indigo-600" /></div>
                    ) : (
                        leads.map((lead) => (
                            <div
                                key={lead.id}
                                onClick={() => setSelectedLeadId(lead.id)}
                                className={`
                  p-4 border-b border-gray-50 cursor-pointer transition-colors hover:bg-gray-50
                  ${selectedLeadId === lead.id ? 'bg-indigo-50 border-l-4 border-l-indigo-600' : 'border-l-4 border-l-transparent'}
                `}
                            >
                                <div className="flex justify-between items-start">
                                    <div className="w-full">
                                        <h3 className={`font-semibold flex items-center gap-2 ${selectedLeadId === lead.id ? 'text-indigo-900' : 'text-gray-900'}`}>
                                            {lead.first_name} {lead.last_name}

                                            {/* --- SIDEBAR: HIRING BADGE (ROCKET) --- */}
                                            {lead.hiring_signal && (
                                                <Rocket className="w-4 h-4 text-green-600 fill-green-100" />
                                            )}
                                        </h3>

                                        <p className="text-sm text-gray-500 flex items-center gap-1 mt-1">
                                            <Briefcase className="w-3 h-3" />
                                            {lead.designation}
                                        </p>

                                        {/* --- SIDEBAR: "Scanning for..." TEXT --- */}
                                        {lead.hiring_signal && lead.ai_variables?.hiring_roles ? (
                                            <p className="text-xs text-green-700 font-medium mt-2 bg-green-50 px-2 py-1 rounded w-fit max-w-full truncate border border-green-100">
                                                looking for: {lead.ai_variables.hiring_roles}
                                            </p>
                                        ) : (
                                            <p className="text-xs text-gray-400 mt-0.5">{lead.company_name}</p>
                                        )}
                                    </div>
                                    <ChevronRight className={`w-4 h-4 mt-1 flex-shrink-0 ${selectedLeadId === lead.id ? 'text-indigo-500' : 'text-gray-300'}`} />
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* --- RIGHT PANEL: DETAILS & EMAILS --- */}
            <div className="flex-1 flex flex-col h-screen overflow-hidden">
                {loadingDetail || !selectedLeadDetail ? (
                    <div className="flex-1 flex items-center justify-center">
                        {loadingDetail ? <Loader2 className="w-8 h-8 animate-spin text-indigo-600" /> : <p>Select a lead</p>}
                    </div>
                ) : (
                    <>
                        {/* Header */}
                        <div className="bg-white p-6 border-b border-gray-200 shadow-sm z-10">
                            <div className="flex justify-between items-start">
                                <div>
                                    <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                                        {selectedLeadDetail.first_name} {selectedLeadDetail.last_name}

                                        {/* --- HEADER: HIRING DETECTED BADGE --- */}
                                        {selectedLeadDetail.hiring_signal && (
                                            <span className="bg-green-100 text-green-900 text-xs px-2.5 mt-1 py-0.5 rounded-full border border-green-200 flex items-center gap-1 font-medium">
                                                <Rocket className="w-3 h-3" /> Hiring Detected
                                            </span>
                                        )}
                                    </h2>
                                    <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                                        <span className="flex items-center gap-1 bg-gray-100 px-2 py-1 rounded">
                                            <Briefcase className="w-3 h-3" /> {selectedLeadDetail.company_name}
                                        </span>
                                        <span className="flex items-center gap-1 bg-green-100 text-green-700 px-2 py-1 rounded">
                                            <CheckCircle2 className="w-3 h-3" /> {selectedLeadDetail.sector}
                                        </span>
                                    </div>
                                </div>

                                {/* --- THE 4 BUTTONS --- */}
                                <div className="flex gap-2">
                                    {/* 1. Automate */}
                                    <button className="flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors text-sm">
                                        <Clock className="w-4 h-4" />
                                        Automate
                                    </button>

                                    {/* 2. ✨ AI PERSONALIZE (Primary Action) */}
                                    <button
                                        onClick={handleEnrichment}
                                        disabled={isEnriching}
                                        className={`flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-sm shadow-md transition-all transform hover:-translate-y-0.5
                                        ${isEnriching
                                                ? 'bg-gray-100 text-gray-400 cursor-wait'
                                                : 'bg-gradient-to-r from-orange-400 to-pink-500 text-white hover:from-orange-500 hover:to-pink-600'
                                            }`}
                                    >
                                        {isEnriching ? (
                                            <> <Loader2 className="w-4 h-4 animate-spin" /> Analyzing... </>
                                        ) : (
                                            <> <BrainCircuit className="w-4 h-4" /> AI Personalize </>
                                        )}
                                    </button>

                                    {/* 3. Go to Enrichment (Secondary) */}
                                    <Link href="/enrichment">
                                        <button className="flex items-center gap-2 px-3 py-2 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-700 font-medium hover:bg-yellow-100 transition-colors text-sm h-full">
                                            <Sparkles className="w-4 h-4 text-yellow-600" />
                                            Enrichment
                                        </button>
                                    </Link>

                                    {/* 4. Push to Instantly */}
                                    <button className="flex items-center gap-2 px-4 py-2 bg-indigo-600 rounded-lg text-white font-medium hover:bg-indigo-700 shadow-lg shadow-indigo-200 transition-all text-sm"
                                        onClick={handlePushSequence}>
                                        <Send className="w-4 h-4" />
                                        Push to Instantly
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Scrollable Email Content */}
                        <div className="flex-1 overflow-y-auto p-8 bg-gray-50">
                            <div className="max-w-3xl mx-auto space-y-8">

                                {/* Template 1 - HAS REWRITE BUTTON */}
                                <EmailCard
                                    title="Email 1: Pain-Led Intro"
                                    body={selectedLeadDetail.email_1_body}
                                    onBodyChange={(text: string) => updateLocalEmailBody('email_1_body', text)}
                                    onSend={() => handleSend(1)}
                                    color="blue"
                                    // Pass handleEnrichment here to enable the rewrite button
                                    onRegenerate={handleEnrichment}
                                />

                                {/* Template 2 */}
                                <EmailCard
                                    title="Email 2: Case Reinforcement"
                                    body={selectedLeadDetail.email_2_body}
                                    onBodyChange={(text: string) => updateLocalEmailBody('email_2_body', text)}
                                    onSend={() => handleSend(2)}
                                    color="purple"
                                />

                                {/* Template 3 */}
                                <EmailCard
                                    title="Email 3: Direct Ask"
                                    body={selectedLeadDetail.email_3_body}
                                    onBodyChange={(text: string) => updateLocalEmailBody('email_3_body', text)}
                                    onSend={() => handleSend(3)}
                                    color="orange"
                                />

                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}

// --- SUB COMPONENT FOR EMAIL CARD (EDITABLE) ---
function EmailCard({ title, body, onSend, color, onBodyChange, onRegenerate }: any) {
    const colors: any = {
        blue: "border-l-blue-500",
        purple: "border-l-purple-500",
        orange: "border-l-orange-500"
    };

    return (
        <div className={`bg-white rounded-xl shadow-sm border border-gray-200 border-l-4 ${colors[color]} overflow-hidden`}>
            <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
                <h4 className="font-semibold text-gray-700 flex items-center gap-2">
                    <Mail className="w-4 h-4 text-gray-400" />
                    {title}
                </h4>

                <div className="flex gap-3">
                    {/* NEW BUTTON: REGENERATE (Only shown if onRegenerate is passed) */}
                    {onRegenerate && (
                        <button
                            onClick={onRegenerate}
                            className="flex items-center gap-1 bg-amber-100 text-xs font-medium text-orange-600 hover:text-orange-800 hover:bg-orange-50 px-2 py-1 rounded transition-colors"
                            title="Rewrite the AI Hook using saved data"
                        >
                            <Sparkles className="w-3 h-3" />
                            Update Personalization
                        </button>
                    )}

                    <button
                        onClick={onSend}
                        className="flex items-center gap-1 text-xs font-bold text-indigo-600 hover:text-indigo-800 hover:underline"
                    >
                        <Send className="w-3 h-3" />
                        Send Now
                    </button>
                </div>
            </div>
            <div className="p-0">
                <textarea
                    className="w-full h-64 p-6 text-gray-600 text-sm leading-relaxed font-mono border-none focus:ring-2 focus:ring-inset focus:ring-indigo-100 resize-none outline-none"
                    value={body || ""}
                    onChange={(e) => onBodyChange(e.target.value)}
                    placeholder="Generating email..."
                />
            </div>
        </div>
    );
} 