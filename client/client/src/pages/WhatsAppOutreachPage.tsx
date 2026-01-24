/**
 * WhatsApp Outreach Page
 * Main page for WhatsApp lead management and messaging.
 * 
 * Layout: Similar to LinkedIn module with left sidebar (leads list) and right panel (details).
 */
import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import WhatsAppActivityModal from '../components/whatsapp/WhatsAppActivityModal';
import WhatsAppDetailPanel from '../components/whatsapp/WhatsAppDetailPanel';
import WhatsAppHeader from '../components/whatsapp/WhatsAppHeader';
import WhatsAppLeadModal from '../components/whatsapp/WhatsAppLeadModal';
import WhatsAppLeadsList from '../components/whatsapp/WhatsAppLeadsList';
import {
    createWhatsAppLead,
    fetchWhatsAppLeadDetail,
    fetchWhatsAppLeads,
    getTemplates,
    getWhatsAppActivities,
    importFromEmailLeads,
    importFromLinkedInLeads,
    sendWhatsApp
} from '../services/whatsapp-service/api';
import {
    CreateLeadRequest,
    WhatsAppActivity,
    WhatsAppLeadDetail,
    WhatsAppLeadSummary,
    WhatsAppTemplate
} from '../types/whatsapp';

export default function WhatsAppOutreachPage() {
    // ============================================
    // STATE
    // ============================================

    // Leads
    const [leads, setLeads] = useState<WhatsAppLeadSummary[]>([]);
    const [loadingLeads, setLoadingLeads] = useState(true);
    const [totalCount, setTotalCount] = useState(0);
    const [currentPage, setCurrentPage] = useState(0);
    const [sourceFilter, setSourceFilter] = useState<string>('');
    const pageLimit = 50;

    // Selected Lead
    const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
    const [selectedLeadDetail, setSelectedLeadDetail] = useState<WhatsAppLeadDetail | null>(null);
    const [loadingDetail, setLoadingDetail] = useState(false);

    // Templates
    const [templates, setTemplates] = useState<WhatsAppTemplate[]>([]);
    const [selectedTemplate, setSelectedTemplate] = useState<string>('');

    // Actions
    const [isSending, setIsSending] = useState(false);
    const [isImporting, setIsImporting] = useState(false);

    // Lead Modal (Add/Edit)
    const [showLeadModal, setShowLeadModal] = useState(false);
    const [isSavingLead, setIsSavingLead] = useState(false);

    // Bulk Selection
    const [selectedForBulk, setSelectedForBulk] = useState<Set<number>>(new Set());

    // Activity Modal
    const [showActivityModal, setShowActivityModal] = useState(false);
    const [activities, setActivities] = useState<WhatsAppActivity[]>([]);
    const [loadingActivities, setLoadingActivities] = useState(false);
    const [activityLeadId, setActivityLeadId] = useState<number | null>(null);
    const [activityLeadName, setActivityLeadName] = useState<string>('');

    // ============================================
    // DATA LOADING
    // ============================================

    const loadLeads = useCallback(async () => {
        setLoadingLeads(true);
        try {
            const response = await fetchWhatsAppLeads(
                currentPage * pageLimit,
                pageLimit,
                sourceFilter || undefined
            );
            setLeads(response.leads);
            setTotalCount(response.total_count);
        } catch (error) {
            toast.error('Failed to load leads');
            console.error(error);
        } finally {
            setLoadingLeads(false);
        }
    }, [currentPage, sourceFilter]);

    const loadLeadDetail = useCallback(async (leadId: number) => {
        setLoadingDetail(true);
        try {
            const detail = await fetchWhatsAppLeadDetail(leadId);
            setSelectedLeadDetail(detail);
        } catch (error) {
            toast.error('Failed to load lead details');
            console.error(error);
        } finally {
            setLoadingDetail(false);
        }
    }, []);

    const loadTemplates = useCallback(async () => {
        try {
            const response = await getTemplates();
            setTemplates(response.templates);
            if (response.templates.length > 0 && !selectedTemplate) {
                const welcomeTemplate = response.templates.find(t => t.name.toLowerCase().includes('welcome')) || response.templates[0];
                setSelectedTemplate(welcomeTemplate.name);
            }
        } catch (error) {
            console.error('Failed to load templates:', error);
        }
    }, [selectedTemplate]);

    const loadActivities = useCallback(async (leadId?: number, leadName?: string) => {
        setLoadingActivities(true);
        setActivityLeadId(leadId || null);
        setActivityLeadName(leadName || '');

        try {
            const response = await getWhatsAppActivities({
                leadId,
                globalOnly: !leadId
            });
            setActivities(response.activities);
        } catch (error) {
            console.error('Failed to load activities:', error);
        } finally {
            setLoadingActivities(false);
        }
    }, []);

    // ============================================
    // EFFECTS
    // ============================================

    useEffect(() => {
        loadLeads();
    }, [loadLeads]);

    useEffect(() => {
        loadTemplates();
    }, [loadTemplates]);

    useEffect(() => {
        if (selectedLeadId) {
            loadLeadDetail(selectedLeadId);
        } else {
            setSelectedLeadDetail(null);
        }
    }, [selectedLeadId, loadLeadDetail]);

    // Auto-select first lead
    useEffect(() => {
        if (leads.length > 0 && !selectedLeadId) {
            setSelectedLeadId(leads[0].id);
        }
    }, [leads, selectedLeadId]);

    // ============================================
    // ACTIONS
    // ============================================

    const handleSendWhatsApp = async () => {
        if (!selectedLeadId || !selectedTemplate) {
            toast.error('Select a lead and template');
            return;
        }

        setIsSending(true);
        try {
            const result = await sendWhatsApp(selectedLeadId, {
                template_name: selectedTemplate
            });

            if (result.success) {
                toast.success(`WhatsApp sent to ${selectedLeadDetail?.first_name}`);
                loadLeads();
                loadLeadDetail(selectedLeadId);
            } else {
                toast.error(result.error || 'Failed to send');
            }
        } catch (error) {
            toast.error('Failed to send WhatsApp');
            console.error(error);
        } finally {
            setIsSending(false);
        }
    };

    const handleImportFromEmail = async () => {
        setIsImporting(true);
        try {
            const result = await importFromEmailLeads();
            toast.success(`Imported ${result.inserted} new, updated ${result.updated} leads`);
            loadLeads();
        } catch (error) {
            toast.error('Failed to import leads');
            console.error(error);
        } finally {
            setIsImporting(false);
        }
    };

    const handleImportFromLinkedIn = async () => {
        setIsImporting(true);
        try {
            const result = await importFromLinkedInLeads();
            toast.success(`Imported ${result.inserted} new, updated ${result.updated} leads`);
            loadLeads();
        } catch (error) {
            toast.error('Failed to import LinkedIn leads');
            console.error(error);
        } finally {
            setIsImporting(false);
        }
    };

    const handleSaveLead = async (data: CreateLeadRequest) => {
        setIsSavingLead(true);
        try {
            const lead = await createWhatsAppLead(data);
            toast.success(`Lead ${lead.first_name} created successfully`);
            setShowLeadModal(false);
            loadLeads();
            setSelectedLeadId(lead.id);
        } catch (error) {
            const err = error as Error;
            toast.error(err.message || 'Failed to save lead');
        } finally {
            setIsSavingLead(false);
        }
    };

    const toggleBulkSelection = (leadId: number) => {
        setSelectedForBulk(prev => {
            const newSet = new Set(prev);
            if (newSet.has(leadId)) {
                newSet.delete(leadId);
            } else {
                newSet.add(leadId);
            }
            return newSet;
        });
    };

    const clearBulkSelection = () => {
        setSelectedForBulk(new Set());
    };

    const openActivityModal = (leadId?: number, leadName?: string) => {
        setShowActivityModal(true);
        loadActivities(leadId, leadName);
    };

    const closeActivityModal = () => {
        setShowActivityModal(false);
        setActivities([]);
        setActivityLeadId(null);
        setActivityLeadName('');
    };

    // ============================================
    // RENDER
    // ============================================

    return (
        <div className="flex flex-col h-screen bg-gray-50">
            {/* Header */}
            <WhatsAppHeader
                templates={templates}
                selectedTemplate={selectedTemplate}
                onTemplateChange={setSelectedTemplate}
                onImportFromEmail={handleImportFromEmail}
                onImportFromLinkedIn={handleImportFromLinkedIn}
                onAddLead={() => setShowLeadModal(true)}
                onOpenActivity={() => openActivityModal()}
                isImporting={isImporting}
            />

            {/* Main Content */}
            <div className="flex flex-1 overflow-hidden">
                {/* Left Panel: Leads List */}
                <WhatsAppLeadsList
                    leads={leads}
                    loading={loadingLeads}
                    selectedLeadId={selectedLeadId}
                    onSelectLead={setSelectedLeadId}
                    totalCount={totalCount}
                    currentPage={currentPage}
                    onPageChange={setCurrentPage}
                    pageLimit={pageLimit}
                    sourceFilter={sourceFilter}
                    onSourceFilterChange={setSourceFilter}
                    selectedForBulk={selectedForBulk}
                    onToggleBulk={toggleBulkSelection}
                    onClearBulk={clearBulkSelection}
                />

                {/* Right Panel: Lead Details */}
                <WhatsAppDetailPanel
                    leadDetail={selectedLeadDetail}
                    loading={loadingDetail}
                    selectedTemplate={selectedTemplate}
                    onSendWhatsApp={handleSendWhatsApp}
                    onOpenActivity={(id, name) => openActivityModal(id, name)}
                    isSending={isSending}
                />
            </div>

            {/* Activity Modal */}
            <WhatsAppActivityModal
                isOpen={showActivityModal}
                onClose={closeActivityModal}
                activities={activities}
                loading={loadingActivities}
                leadName={activityLeadName}
            />

            {/* Lead Modal */}
            <WhatsAppLeadModal
                isOpen={showLeadModal}
                onClose={() => setShowLeadModal(false)}
                onSave={handleSaveLead}
                isSaving={isSavingLead}
            />
        </div>
    );
}
