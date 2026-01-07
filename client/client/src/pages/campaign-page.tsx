/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import {
    AlertTriangle,
    ArrowLeft,
    BrainCircuit,
    Briefcase,
    Check,
    CheckCircle2,
    CheckSquare,
    ChevronRight,
    Loader2,
    Mail,
    Rocket,
    Send,
    Sparkles,
    Square,
    User,
    Users,
    X
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import {
    bulkCheckEligibility,
    bulkPushToInstantly,
    enrichLead,
    fetchLeadDetails,
    fetchLeads,
    sendEmailMock,
    sendSequenceToInstantly
} from '../services/campaign-service/api';

import { BulkCheckResponse, BulkPushResponse, Lead } from "../types/types";

export default function CampaignPage() {
    const [leads, setLeads] = useState<Lead[]>([]);
    const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
    const [selectedLeadDetail, setSelectedLeadDetail] = useState<Lead | null>(null);
    const [loadingList, setLoadingList] = useState(true);
    const [loadingDetail, setLoadingDetail] = useState(false);

    // Loading state for the Personalize Button
    const [isEnriching, setIsEnriching] = useState(false);

    // State for incomplete leads alert
    const [incompleteLeadsCount, setIncompleteLeadsCount] = useState(0);
    const [showAlert, setShowAlert] = useState(true);

    // --- BULK SELECTION STATE ---
    const [selectedLeadIds, setSelectedLeadIds] = useState<Set<number>>(new Set());
    const [showBulkModal, setShowBulkModal] = useState(false);
    const [bulkCheckResult, setBulkCheckResult] = useState<BulkCheckResponse | null>(null);
    const [isBulkPushing, setIsBulkPushing] = useState(false);
    const [bulkPushProgress, setBulkPushProgress] = useState(0);
    const [bulkPushResult, setBulkPushResult] = useState<BulkPushResponse | null>(null);

    const MAX_SELECTION = 100;

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
            const response = await fetchLeads();
            setLeads(response.leads);
            setIncompleteLeadsCount(response.incomplete_leads_count);
            if (response.leads.length > 0 && !selectedLeadId) setSelectedLeadId(response.leads[0].id); // Auto-select first
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

    // --- AI PERSONALIZATION ---
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

    // Helper to update any email field (Subject or Body) in local state
    const updateLocalEmailField = (key: keyof Lead, newText: string) => {
        if (!selectedLeadDetail) return;
        setSelectedLeadDetail({
            ...selectedLeadDetail,
            [key]: newText
        });
    };

    const handlePushSequence = async () => {
        if (!selectedLeadDetail || !selectedLeadId) return;
        try {
            alert("🚀 Pushing full sequence to Instantly...");

            // We verify if types allow extra fields, otherwise cast to any
            // Ensure your backend receives these 'email_x_subject' fields
            await sendSequenceToInstantly(selectedLeadId, {
                email_1: selectedLeadDetail.email_1_body || "",
                email_2: selectedLeadDetail.email_2_body || "",
                email_3: selectedLeadDetail.email_3_body || "",
                // Sending Subjects as well (ensure backend maps these to subject_1, etc.)
                email_1_subject: selectedLeadDetail.email_1_subject || "",
                email_2_subject: selectedLeadDetail.email_2_subject || "",
                email_3_subject: selectedLeadDetail.email_3_subject || ""
            } as any);

            alert("✅ Lead & Sequence added successfully!");
        } catch (error) {
            console.error(error);
            alert("❌ Failed to push sequence.");
        }
    };

    const handleSend = async (templateId: number) => {
        if (!selectedLeadDetail || !selectedLeadId) return;
        let finalBody = "";
        // Note: For single send, you might want to pass subject too, 
        // but typically sendEmailMock uses just body for preview.
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

    // --- BULK SELECTION HANDLERS ---

    // Toggle single lead checkbox
    const toggleLeadSelection = (leadId: number, e: React.MouseEvent) => {
        e.stopPropagation(); // Don't trigger lead detail view

        const lead = leads.find(l => l.id === leadId);
        if (lead?.is_sent) return; // Don't allow selecting already-sent leads

        setSelectedLeadIds(prev => {
            const newSet = new Set(prev);
            if (newSet.has(leadId)) {
                newSet.delete(leadId);
            } else if (newSet.size < MAX_SELECTION) {
                newSet.add(leadId);
            }
            return newSet;
        });
    };

    // Select All (max 100, excluding already-sent)
    const handleSelectAll = () => {
        const unsent = leads.filter(l => !l.is_sent);
        if (selectedLeadIds.size === Math.min(unsent.length, MAX_SELECTION)) {
            // If all selected, deselect all
            setSelectedLeadIds(new Set());
        } else {
            // Select up to MAX_SELECTION unsent leads
            const toSelect = unsent.slice(0, MAX_SELECTION).map(l => l.id);
            setSelectedLeadIds(new Set(toSelect));
        }
    };

    // Open bulk push modal with pre-flight check
    const handleOpenBulkModal = async () => {
        if (selectedLeadIds.size === 0) return;

        try {
            const result = await bulkCheckEligibility(Array.from(selectedLeadIds));
            setBulkCheckResult(result);
            setShowBulkModal(true);
        } catch (error: any) {
            alert(`❌ Error checking leads: ${error.message}`);
        }
    };

    // Execute bulk push
    const handleBulkPush = async () => {
        if (!bulkCheckResult || bulkCheckResult.ready === 0) return;

        setIsBulkPushing(true);
        setBulkPushProgress(0);

        // Simulate progress (since we can't get real progress from API)
        const progressInterval = setInterval(() => {
            setBulkPushProgress(prev => Math.min(prev + 10, 90));
        }, 200);

        try {
            const result = await bulkPushToInstantly(bulkCheckResult.details.ready);
            setBulkPushProgress(100);
            setBulkPushResult(result);

            // Refresh leads to update is_sent status
            await loadLeads();

            // Clear selection
            setSelectedLeadIds(new Set());

        } catch (error: any) {
            alert(`❌ Bulk push failed: ${error.message}`);
        } finally {
            clearInterval(progressInterval);
            setIsBulkPushing(false);
        }
    };

    // Close modal and reset state
    const closeBulkModal = () => {
        setShowBulkModal(false);
        setBulkCheckResult(null);
        setBulkPushResult(null);
        setBulkPushProgress(0);
    };

    // Count of selectable leads (not already sent)
    const selectableLeadsCount = leads.filter(l => !l.is_sent).length;
    const allSelected = selectedLeadIds.size === Math.min(selectableLeadsCount, MAX_SELECTION) && selectableLeadsCount > 0;

    return (
        <div className="flex flex-col h-screen bg-gray-50 font-sans">

            {/* --- ALERT BANNER: Shows when some leads have missing data --- */}
            {showAlert && incompleteLeadsCount > 0 && (
                <div className="bg-amber-50 border-b border-amber-200 px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5 text-amber-600" />
                        <span className="text-amber-800 text-sm">
                            <strong>{incompleteLeadsCount} lead{incompleteLeadsCount > 1 ? 's' : ''}</strong> in this list have missing data (LinkedIn, Mobile, etc.).
                            <Link href="/enrichment" className="text-amber-900 underline font-medium ml-1 hover:text-amber-700">
                                Visit Enrichment page
                            </Link> to complete them.
                        </span>
                    </div>
                    <button
                        onClick={() => setShowAlert(false)}
                        className="text-amber-600 hover:text-amber-800 p-1"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            )}

            <div className="flex flex-1 overflow-hidden">
                {/* --- LEFT SIDEBAR: LEAD LIST --- */}
                <div className="w-1/3 border-r border-gray-200 bg-white flex flex-col">
                    <div className="p-5 border-b  border-gray-100">
                        <Link href="/" className="text-gray-500 hover:text-gray-800 flex items-center gap-1 mb-3 text-xs font-bold transition-colors">
                            <ArrowLeft className="w-3 h-3" /> Back to Home
                        </Link>
                        <h1 className="text-xl font-bold text-gray-800 bg-violet-200  flex  items-center gap-2 p-1 rounded">
                            <User className="w-5 h-5 text-indigo-700" />
                            Verified Leads
                        </h1>
                        <p className="text-sm text-stone-800 mt-1">{leads.length} potential candidates ready</p>

                        {/* --- SELECT ALL & COUNTER --- */}
                        <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
                            <button
                                onClick={handleSelectAll}
                                className="flex items-center gap-2 text-sm text-gray-600 hover:text-indigo-600 transition-colors"
                            >
                                {allSelected ? (
                                    <CheckSquare className="w-4 h-4 text-indigo-600" />
                                ) : (
                                    <Square className="w-4 h-4" />
                                )}
                                Select All (max {MAX_SELECTION})
                            </button>
                            {selectedLeadIds.size > 0 && (
                                <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded-full font-medium">
                                    {selectedLeadIds.size} selected
                                </span>
                            )}
                        </div>
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
                                        ${lead.is_sent ? 'opacity-60' : ''}
                                    `}
                                >
                                    <div className="flex items-start gap-3">
                                        {/* --- CHECKBOX --- */}
                                        <div
                                            onClick={(e) => toggleLeadSelection(lead.id, e)}
                                            className={`flex-shrink-0 mt-1 w-5 h-5 rounded border-2 flex items-center justify-center cursor-pointer transition-colors
                                                ${lead.is_sent
                                                    ? 'bg-gray-200 border-gray-300 cursor-not-allowed'
                                                    : selectedLeadIds.has(lead.id)
                                                        ? 'bg-indigo-600 border-indigo-600'
                                                        : 'border-gray-300 hover:border-indigo-400'
                                                }`}
                                        >
                                            {lead.is_sent ? (
                                                <Check className="w-3 h-3 text-gray-500" />
                                            ) : selectedLeadIds.has(lead.id) ? (
                                                <Check className="w-3 h-3 text-white" />
                                            ) : null}
                                        </div>

                                        <div className="flex-1 min-w-0">
                                            <h3 className={`font-semibold flex items-center gap-2 ${selectedLeadId === lead.id ? 'text-indigo-900' : 'text-gray-900'}`}>
                                                {lead.first_name} {lead.last_name}

                                                {/* --- HIRING BADGE (ROCKET) --- */}
                                                {lead.hiring_signal && (
                                                    <Rocket className="w-4 h-4 text-green-600 fill-green-100" />
                                                )}

                                                {/* --- SENT INDICATOR --- */}
                                                {lead.is_sent && (
                                                    <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-medium">
                                                        Sent ✓
                                                    </span>
                                                )}

                                                {/* --- NEEDS AI INDICATOR --- */}
                                                {/* Show if: not sent, has LinkedIn, AND (no ai_variables OR ai_variables is empty) AND not enriched */}
                                                {!lead.is_sent &&
                                                    lead.linkedin_url &&
                                                    (!lead.ai_variables || Object.keys(lead.ai_variables).length === 0) &&
                                                    lead.enrichment_status !== 'completed' && (
                                                        <span className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded font-medium border border-amber-200">
                                                            📝 Needs AI enrichment
                                                        </span>
                                                    )}
                                            </h3>

                                            <p className="text-sm text-gray-500 flex items-center gap-1 mt-1">
                                                <Briefcase className="w-3 h-3" />
                                                {lead.designation}
                                            </p>

                                            {/* --- "looking for..." TEXT --- */}
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
                                        {/* 1. BULK PUSH (Replaces Automate) */}
                                        <button
                                            onClick={handleOpenBulkModal}
                                            disabled={selectedLeadIds.size === 0}
                                            className={`flex items-center gap-2 px-3 py-2 rounded-lg font-medium transition-colors text-sm
                                                ${selectedLeadIds.size > 0
                                                    ? 'bg-violet-600 text-white hover:bg-violet-700 shadow-md'
                                                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                                }`}
                                        >
                                            <Users className="w-4 h-4" />
                                            Bulk Push {selectedLeadIds.size > 0 && `(${selectedLeadIds.size})`}
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
                                            <button className="flex items-center gap-2 px-3 py-2 bg-yellow-100 border border-yellow-200 rounded-lg text-yellow-700 font-medium hover:bg-yellow-100 transition-colors text-sm h-full">
                                                <Sparkles className="w-4 h-4 text-yellow-600" />
                                                Go to Enrichment
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
                                        subject={selectedLeadDetail.email_1_subject}
                                        body={selectedLeadDetail.email_1_body}
                                        onSubjectChange={(text: string) => updateLocalEmailField('email_1_subject', text)}
                                        onBodyChange={(text: string) => updateLocalEmailField('email_1_body', text)}
                                        onSend={() => handleSend(1)}
                                        color="blue"
                                        // Pass handleEnrichment here to enable the rewrite button
                                        onRegenerate={handleEnrichment}
                                    />

                                    {/* Template 2 */}
                                    <EmailCard
                                        title="Email 2: Case Reinforcement"
                                        subject={selectedLeadDetail.email_2_subject}
                                        body={selectedLeadDetail.email_2_body}
                                        onSubjectChange={(text: string) => updateLocalEmailField('email_2_subject', text)}
                                        onBodyChange={(text: string) => updateLocalEmailField('email_2_body', text)}
                                        onSend={() => handleSend(2)}
                                        color="purple"
                                    />

                                    {/* Template 3 */}
                                    <EmailCard
                                        title="Email 3: Direct Ask"
                                        subject={selectedLeadDetail.email_3_subject}
                                        body={selectedLeadDetail.email_3_body}
                                        onSubjectChange={(text: string) => updateLocalEmailField('email_3_subject', text)}
                                        onBodyChange={(text: string) => updateLocalEmailField('email_3_body', text)}
                                        onSend={() => handleSend(3)}
                                        color="orange"
                                    />

                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* === BULK PUSH MODAL === */}
            {showBulkModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
                        {/* Modal Header */}
                        <div className="bg-gradient-to-r from-violet-600 to-indigo-600 p-6 text-white">
                            <div className="flex justify-between items-center">
                                <h3 className="text-xl font-bold flex items-center gap-2">
                                    <Users className="w-6 h-6" />
                                    Bulk Push to Instantly
                                </h3>
                                <button onClick={closeBulkModal} className="hover:bg-white/20 p-1 rounded">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                        </div>

                        {/* Modal Body */}
                        <div className="p-6">
                            {/* Show result if push completed */}
                            {bulkPushResult ? (
                                <div className="space-y-4">
                                    <div className="text-center py-4">
                                        <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-3" />
                                        <h4 className="text-xl font-bold text-gray-900">Push Complete!</h4>
                                        <p className="text-gray-600 mt-1">{bulkPushResult.message}</p>
                                    </div>

                                    <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-600">Leads Uploaded:</span>
                                            <span className="font-bold text-green-600">{bulkPushResult.leads_uploaded}</span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-600">Duplicates in Instantly:</span>
                                            <span className="font-medium">{bulkPushResult.duplicated_in_instantly}</span>
                                        </div>
                                        {bulkPushResult.skipped_needs_enrichment.length > 0 && (
                                            <div className="flex justify-between text-sm">
                                                <span className="text-amber-600">Skipped (needs enrichment):</span>
                                                <span className="font-medium text-amber-600">{bulkPushResult.skipped_needs_enrichment.length}</span>
                                            </div>
                                        )}
                                        {bulkPushResult.skipped_no_email.length > 0 && (
                                            <div className="flex justify-between text-sm">
                                                <span className="text-red-600">Skipped (no email):</span>
                                                <span className="font-medium text-red-600">{bulkPushResult.skipped_no_email.length}</span>
                                            </div>
                                        )}
                                    </div>

                                    <button
                                        onClick={closeBulkModal}
                                        className="w-full py-3 bg-indigo-600 text-white font-bold rounded-lg hover:bg-indigo-700 transition-colors"
                                    >
                                        Done
                                    </button>
                                </div>
                            ) : isBulkPushing ? (
                                /* Progress State */
                                <div className="space-y-4 py-8">
                                    <div className="text-center">
                                        <Loader2 className="w-12 h-12 text-indigo-600 animate-spin mx-auto mb-3" />
                                        <h4 className="text-lg font-bold text-gray-900">Pushing leads to Instantly...</h4>
                                        <p className="text-sm text-gray-500 mt-1">This may take a moment</p>
                                    </div>

                                    {/* Progress Bar */}
                                    <div className="bg-gray-200 rounded-full h-3 overflow-hidden">
                                        <div
                                            className="bg-gradient-to-r from-violet-500 to-indigo-500 h-full transition-all duration-300"
                                            style={{ width: `${bulkPushProgress}%` }}
                                        />
                                    </div>
                                    <p className="text-center text-sm text-gray-600">{bulkPushProgress}% complete</p>
                                </div>
                            ) : bulkCheckResult ? (
                                /* Pre-flight Check Results */
                                <div className="space-y-4">
                                    <p className="text-gray-700">
                                        You are about to push <strong className="text-indigo-600">{bulkCheckResult.ready}</strong> leads to Instantly.
                                    </p>

                                    {/* Warnings */}
                                    {bulkCheckResult.needs_enrichment > 0 && (
                                        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
                                            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                                            <div>
                                                <p className="text-amber-800 font-medium text-sm">
                                                    {bulkCheckResult.needs_enrichment} lead{bulkCheckResult.needs_enrichment > 1 ? 's' : ''} need enrichment
                                                </p>
                                                <p className="text-amber-700 text-xs mt-1">
                                                    These leads have LinkedIn URLs but haven&apos;t been personalized yet. They will be skipped.
                                                </p>
                                            </div>
                                        </div>
                                    )}

                                    {bulkCheckResult.invalid_email > 0 && (
                                        <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
                                            <X className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                                            <p className="text-red-800 text-sm">
                                                {bulkCheckResult.invalid_email} lead{bulkCheckResult.invalid_email > 1 ? 's' : ''} have invalid/missing email
                                            </p>
                                        </div>
                                    )}

                                    {bulkCheckResult.already_sent > 0 && (
                                        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm text-gray-600">
                                            {bulkCheckResult.already_sent} lead{bulkCheckResult.already_sent > 1 ? 's' : ''} already sent (skipped)
                                        </div>
                                    )}

                                    {/* Summary */}
                                    <div className="bg-indigo-50 rounded-lg p-4">
                                        <div className="flex justify-between items-center">
                                            <span className="text-indigo-900 font-medium">Ready to push:</span>
                                            <span className="text-2xl font-bold text-indigo-600">{bulkCheckResult.ready}</span>
                                        </div>
                                    </div>

                                    {/* Action Buttons */}
                                    <div className="flex gap-3 pt-2">
                                        <button
                                            onClick={closeBulkModal}
                                            className="flex-1 py-3 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            onClick={handleBulkPush}
                                            disabled={bulkCheckResult.ready === 0}
                                            className={`flex-1 py-3 font-bold rounded-lg transition-colors flex items-center justify-center gap-2
                                                ${bulkCheckResult.ready > 0
                                                    ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                                                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                                }`}
                                        >
                                            <Send className="w-4 h-4" />
                                            Confirm & Push
                                        </button>
                                    </div>
                                </div>
                            ) : null}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// --- SUB COMPONENT FOR EMAIL CARD (EDITABLE) ---
function EmailCard({ title, subject, body, onSend, color, onSubjectChange, onBodyChange, onRegenerate }: any) {
    const colors: any = {
        blue: "border-l-blue-500",
        purple: "border-l-purple-500",
        orange: "border-l-orange-500"
    };

    return (
        <div className={`bg-white rounded-xl shadow-sm border border-gray-200 border-l-4 ${colors[color]} overflow-hidden`}>
            {/* Card Header & Controls */}
            <div className="p-4 border-b border-gray-100 flex flex-col gap-3 bg-gray-50">

                {/* Top Row: Title & Buttons */}
                <div className="flex justify-between items-center">
                    <h4 className="font-semibold text-gray-700 flex items-center gap-2">
                        <Mail className="w-4 h-4 text-gray-400" />
                        {title}
                    </h4>

                    <div className="flex gap-3">
                        {/* REGENERATE (Only shown if onRegenerate is passed) */}
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

                {/* Subject Line Input Row */}
                <div className="flex items-center gap-2 bg-indigo-50 px-3 py-2 rounded border border-gray-200 shadow-sm">
                    <span className="text-gray-400 text-xs font-bold uppercase tracking-wide">Subject:</span>
                    <input
                        className="flex-1 text-sm font-medium text-gray-800 outline-none placeholder:text-gray-300"
                        value={subject || ""}
                        onChange={(e) => onSubjectChange(e.target.value)}
                        placeholder="Subject line will appear here..."
                    />
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