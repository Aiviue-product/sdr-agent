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
    bulkSendWhatsApp,
    createWhatsAppLead,
    deleteWhatsAppLead,
    fetchWhatsAppLeadDetail,
    fetchWhatsAppLeads,
    getConversation,
    getTemplates,
    getWhatsAppActivities,
    getWhatsAppConfig,
    globalSyncWati,
    importFromEmailLeads,
    importFromLinkedInLeads,
    sendWhatsApp,
    syncMessageStatus,
    updateWhatsAppLead
} from '../services/whatsapp-service/api';
import {
    CreateLeadRequest,
    WhatsAppActivity,
    WhatsAppLeadDetail,
    WhatsAppLeadSummary,
    WhatsAppMessage,
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

    // Conversation
    const [messages, setMessages] = useState<WhatsAppMessage[]>([]);
    const [loadingMessages, setLoadingMessages] = useState(false);

    // Templates
    const [templates, setTemplates] = useState<WhatsAppTemplate[]>([]);
    const [selectedTemplate, setSelectedTemplate] = useState<string>('');

    // Actions
    const [isSending, setIsSending] = useState(false);
    const [isImportingEmail, setIsImportingEmail] = useState(false);
    const [isImportingLinkedIn, setIsImportingLinkedIn] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [isSyncing, setIsSyncing] = useState(false);
    const [isGlobalSyncing, setIsGlobalSyncing] = useState(false);
    const [isBulkSending, setIsBulkSending] = useState(false);

    // Lead Modal (Add/Edit)
    const [showLeadModal, setShowLeadModal] = useState(false);
    const [editingLead, setEditingLead] = useState<WhatsAppLeadDetail | null>(null);
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

    const loadConversation = useCallback(async (leadId: number) => {
        setLoadingMessages(true);
        try {
            const response = await getConversation(leadId);
            // Reverse messages for WhatsApp style (newest at bottom)
            setMessages(response.messages.reverse());
        } catch (error) {
            console.error('Failed to load conversation:', error);
        } finally {
            setLoadingMessages(false);
        }
    }, []);

    const loadLeadDetail = useCallback(async (leadId: number) => {
        setLoadingDetail(true);
        try {
            const detail = await fetchWhatsAppLeadDetail(leadId);
            setSelectedLeadDetail(detail);
            // Also load conversation
            loadConversation(leadId);
        } catch (error) {
            toast.error('Failed to load lead details');
            console.error(error);
        } finally {
            setLoadingDetail(false);
        }
    }, [loadConversation]);

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

    // Background WATI config check - runs once on page load
    useEffect(() => {
        const checkConfig = async () => {
            try {
                const config = await getWhatsAppConfig();
                if (!config.configured) {
                    toast.error('⚠️ WATI is not configured. Check your API settings.', {
                        duration: 5000,
                        icon: '⚙️'
                    });
                }
            } catch (error) {
                console.error('Config check failed:', error);
                toast.error('Unable to verify WATI configuration', { duration: 3000 });
            }
        };
        checkConfig();
    }, []);

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
        setIsImportingEmail(true);
        try {
            const result = await importFromEmailLeads();
            toast.success(`Imported ${result.inserted} new, updated ${result.updated} leads`);
            loadLeads();
        } catch (error) {
            toast.error('Failed to import leads');
            console.error(error);
        } finally {
            setIsImportingEmail(false);
        }
    };

    const handleImportFromLinkedIn = async () => {
        setIsImportingLinkedIn(true);
        try {
            const result = await importFromLinkedInLeads();
            toast.success(`Imported ${result.inserted} new, updated ${result.updated} leads`);
            loadLeads();
        } catch (error) {
            toast.error('Failed to import LinkedIn leads');
            console.error(error);
        } finally {
            setIsImportingLinkedIn(false);
        }
    };

    const handleSaveLead = async (data: CreateLeadRequest) => {
        setIsSavingLead(true);
        try {
            if (editingLead) {
                // Update existing lead
                const lead = await updateWhatsAppLead(editingLead.id, data);
                toast.success(`Lead ${lead.first_name} updated successfully`);
                // Refresh the detail panel with updated data
                loadLeadDetail(lead.id);
            } else {
                // Create new lead
                const lead = await createWhatsAppLead(data);
                toast.success(`Lead ${lead.first_name} created successfully`);
                setSelectedLeadId(lead.id);
            }
            closeLeadModal();
            loadLeads();
        } catch (error) {
            const err = error as Error;
            toast.error(err.message || 'Failed to save lead');
        } finally {
            setIsSavingLead(false);
        }
    };

    const handleEditLead = (lead: WhatsAppLeadDetail) => {
        setEditingLead(lead);
        setShowLeadModal(true);
    };

    const closeLeadModal = () => {
        setShowLeadModal(false);
        setEditingLead(null);
    };

    const handleDeleteLead = async (leadId: number) => {
        setIsDeleting(true);
        try {
            await deleteWhatsAppLead(leadId);
            toast.success('Lead deleted successfully');
            setSelectedLeadId(null);
            setSelectedLeadDetail(null);
            loadLeads();
        } catch (error) {
            const err = error as Error;
            toast.error(err.message || 'Failed to delete lead');
        } finally {
            setIsDeleting(false);
        }
    };

    const handleSyncStatus = async (leadId: number) => {
        setIsSyncing(true);
        try {
            const result = await syncMessageStatus(leadId);
            if (result.success) {
                toast.success('Status synced from WATI');
                // Refresh lead detail to show updated status
                loadLeadDetail(leadId);
            } else {
                toast.error('Sync returned no updates');
            }
        } catch (error) {
            const err = error as Error;
            toast.error(err.message || 'Failed to sync status');
        } finally {
            setIsSyncing(false);
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

    const handleBulkSend = async () => {
        if (selectedForBulk.size === 0) {
            toast.error('No leads selected');
            return;
        }
        if (!selectedTemplate) {
            toast.error('Please select a template first');
            return;
        }

        setIsBulkSending(true);
        try {
            const leadIds = Array.from(selectedForBulk);
            const result = await bulkSendWhatsApp({
                lead_ids: leadIds,
                template_name: selectedTemplate,
                broadcast_name: `bulk_${Date.now()}`
            });

            if (result.success) {
                toast.success(`✅ Sent: ${result.success_count} | ❌ Failed: ${result.failed_count}`);
                clearBulkSelection();
                loadLeads(); // Refresh left panel
                // Also refresh the selected lead's detail if it was in the bulk send
                if (selectedLeadId && leadIds.includes(selectedLeadId)) {
                    loadLeadDetail(selectedLeadId);
                }
            } else {
                toast.error('Bulk send failed');
            }
        } catch (error) {
            const err = error as Error;
            toast.error(err.message || 'Bulk send failed');
        } finally {
            setIsBulkSending(false);
        }
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
    const handleGlobalSync = async () => {
        setIsGlobalSyncing(true);
        try {
            const result = await globalSyncWati();
            if (result.success) {
                toast.success(`Sync complete! Leads: ${result.leads_processed}, Messages: ${result.messages_synced}`);

                // Refresh all UI data
                await Promise.all([
                    loadTemplates(),
                    loadLeads()
                ]);

                // If a lead is selected, refresh its details too
                if (selectedLeadId) {
                    loadLeadDetail(selectedLeadId);
                }
            } else {
                toast.error('Sync failed');
            }
        } catch (error) {
            const err = error as Error;
            toast.error(err.message || 'Failed to sync data');
        } finally {
            setIsGlobalSyncing(false);
        }
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
                onAddLead={() => {
                    setEditingLead(null);
                    setShowLeadModal(true);
                }}
                onOpenActivity={() => openActivityModal()}
                onSync={handleGlobalSync}
                isImportingEmail={isImportingEmail}
                isImportingLinkedIn={isImportingLinkedIn}
                isSyncing={isGlobalSyncing}
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
                    onBulkSend={handleBulkSend}
                    isBulkSending={isBulkSending}
                    hasTemplate={!!selectedTemplate}
                />

                {/* Right Panel: Lead Details */}
                <WhatsAppDetailPanel
                    leadDetail={selectedLeadDetail}
                    messages={messages}
                    loadingDetails={loadingDetail}
                    loadingMessages={loadingMessages}
                    selectedTemplate={selectedTemplate}
                    onSendWhatsApp={handleSendWhatsApp}
                    onOpenActivity={(id, name) => openActivityModal(id, name)}
                    onDeleteLead={handleDeleteLead}
                    onSyncStatus={handleSyncStatus}
                    onEditLead={handleEditLead}
                    isSending={isSending}
                    isDeleting={isDeleting}
                    isSyncing={isSyncing}
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
                onClose={closeLeadModal}
                onSave={handleSaveLead}
                lead={editingLead}
                isSaving={isSavingLead}
            />
        </div>
    );
}
