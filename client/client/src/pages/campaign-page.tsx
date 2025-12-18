/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import {
    Briefcase,
    CheckCircle2,
    ChevronRight,
    Clock,
    Loader2,
    Mail,
    Send,
    User
} from 'lucide-react';
import { useEffect, useState } from 'react';
// Ensure this path points to your api.ts
import {
    fetchLeadDetails,
    fetchLeads,
    Lead,
    sendEmailMock
} from '../services/campaign-service/api';

export default function CampaignPage() {
    const [leads, setLeads] = useState<Lead[]>([]);
    const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
    const [selectedLeadDetail, setSelectedLeadDetail] = useState<Lead | null>(null);
    const [loadingList, setLoadingList] = useState(true);
    const [loadingDetail, setLoadingDetail] = useState(false);

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
            if (data.length > 0) setSelectedLeadId(data[0].id); // Auto-select first
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

    // --- HELPER: Update local state when user types in the textarea ---
    const updateLocalEmailBody = (templateKey: 'email_1_body' | 'email_2_body' | 'email_3_body', newText: string) => {
        if (!selectedLeadDetail) return;
        setSelectedLeadDetail({
            ...selectedLeadDetail,
            [templateKey]: newText
        });
    };

    // --- ACTION: Send the specific email content to Backend ---
    const handleSend = async (templateId: number) => {
        if (!selectedLeadDetail || !selectedLeadId) return;

        // Pick the correct body text based on which button was clicked
        let finalBody = "";
        if (templateId === 1) finalBody = selectedLeadDetail.email_1_body || "";
        if (templateId === 2) finalBody = selectedLeadDetail.email_2_body || "";
        if (templateId === 3) finalBody = selectedLeadDetail.email_3_body || "";

        try {
            alert(` Sending to Instantly.ai...`);
            // Pass the edited body content to the API
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
                                    <div>
                                        <h3 className={`font-semibold ${selectedLeadId === lead.id ? 'text-indigo-900' : 'text-gray-900'}`}>
                                            {lead.first_name} {lead.last_name}
                                        </h3>
                                        <p className="text-sm text-gray-500 flex items-center gap-1 mt-1">
                                            <Briefcase className="w-3 h-3" />
                                            {lead.designation}
                                        </p>
                                        <p className="text-xs text-gray-400 mt-0.5">{lead.company_name}</p>
                                    </div>
                                    <ChevronRight className={`w-4 h-4 mt-1 ${selectedLeadId === lead.id ? 'text-indigo-500' : 'text-gray-300'}`} />
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
                                    <h2 className="text-2xl font-bold text-gray-900">
                                        {selectedLeadDetail.first_name} {selectedLeadDetail.last_name}
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

                                <div className="flex gap-3">
                                    <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors">
                                        <Clock className="w-4 h-4" />
                                        Automate (Cron)
                                    </button>
                                    <button className="flex items-center gap-2 px-4 py-2 bg-indigo-600 rounded-lg text-white font-medium hover:bg-indigo-700 shadow-lg shadow-indigo-200 transition-all">
                                        <Send className="w-4 h-4" />
                                        Push to Instantly.ai
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Scrollable Email Content */}
                        <div className="flex-1 overflow-y-auto p-8 bg-gray-50">
                            <div className="max-w-3xl mx-auto space-y-8">

                                {/* Template 1 */}
                                <EmailCard
                                    title="Email 1: Pain-Led Intro"
                                    body={selectedLeadDetail.email_1_body}
                                    onBodyChange={(text: string) => updateLocalEmailBody('email_1_body', text)}
                                    onSend={() => handleSend(1)}
                                    color="blue"
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
function EmailCard({ title, body, onSend, color, onBodyChange }: any) {
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
                <button
                    onClick={onSend}
                    className="text-xs font-bold text-indigo-600 hover:text-indigo-800 hover:underline"
                >
                    Send Now
                </button>
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