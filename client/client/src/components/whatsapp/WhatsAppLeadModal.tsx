/**
 * WhatsApp Lead Modal
 * Modal for adding or editing a WhatsApp lead manually.
 */
import React, { useEffect, useState } from 'react';
import { CreateLeadRequest, WhatsAppLeadDetail } from '../../types/whatsapp';

interface WhatsAppLeadModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (data: CreateLeadRequest) => Promise<void>;
    lead?: WhatsAppLeadDetail | null;
    isSaving: boolean;
}

export default function WhatsAppLeadModal({
    isOpen,
    onClose,
    onSave,
    lead,
    isSaving
}: WhatsAppLeadModalProps) {
    const [formData, setFormData] = useState<CreateLeadRequest>({
        mobile_number: '',
        first_name: '',
        last_name: '',
        company_name: '',
        email: '',
        designation: '',
        linkedin_url: ''
    });

    useEffect(() => {
        if (lead) {
            setFormData({
                mobile_number: lead.mobile_number,
                first_name: lead.first_name,
                last_name: lead.last_name || '',
                company_name: lead.company_name || '',
                email: lead.email || '',
                designation: lead.designation || '',
                linkedin_url: lead.linkedin_url || ''
            });
        } else {
            setFormData({
                mobile_number: '',
                first_name: '',
                last_name: '',
                company_name: '',
                email: '',
                designation: '',
                linkedin_url: ''
            });
        }
    }, [lead, isOpen]);

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        await onSave(formData);
    };

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in duration-200">
                {/* Header */}
                <div className="bg-green-600 px-6 py-4 flex items-center justify-between text-white">
                    <h2 className="text-xl font-bold">
                        {lead ? 'Edit Lead' : 'Add New WhatsApp Lead'}
                    </h2>
                    <button onClick={onClose} className="hover:bg-white/20 p-1 rounded-full transition-colors">
                        ✕
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-1">
                            <label className="text-[10px] font-bold text-stone-600 uppercase tracking-wider">First Name *</label>
                            <input
                                type="text"
                                required
                                value={formData.first_name}
                                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                                className="w-full px-3 py-2 border border-stone-200 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 focus:outline-none transition-all text-stone-900 font-medium placeholder:text-stone-300"
                                placeholder="John"
                            />
                        </div>
                        <div className="space-y-1">
                            <label className="text-[10px] font-bold text-stone-600 uppercase tracking-wider">Last Name</label>
                            <input
                                type="text"
                                value={formData.last_name}
                                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                                className="w-full px-3 py-2 border border-stone-200 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 focus:outline-none transition-all text-stone-900 font-medium placeholder:text-stone-300"
                                placeholder="Doe"
                            />
                        </div>
                    </div>

                    <div className="space-y-1">
                        <label className="text-[10px] font-bold text-stone-600 uppercase tracking-wider">Mobile Number *</label>
                        <input
                            type="text"
                            required
                            value={formData.mobile_number}
                            onChange={(e) => setFormData({ ...formData, mobile_number: e.target.value })}
                            className="w-full px-3 py-2 border border-stone-200 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 focus:outline-none transition-all text-stone-900 font-medium placeholder:text-stone-300"
                            placeholder="e.g. 919876543210"
                        />
                        <p className="text-[10px] text-stone-400 font-medium">Include country code without + or spaces.</p>
                    </div>

                    <div className="space-y-1">
                        <label className="text-[10px] font-bold text-stone-600 uppercase tracking-wider">Company Name</label>
                        <input
                            type="text"
                            value={formData.company_name}
                            onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                            className="w-full px-3 py-2 border border-stone-200 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 focus:outline-none transition-all text-stone-900 font-medium placeholder:text-stone-300"
                            placeholder="Google"
                        />
                    </div>

                    <div className="space-y-1">
                        <label className="text-[10px] font-bold text-stone-600 uppercase tracking-wider">Email Address</label>
                        <input
                            type="email"
                            value={formData.email}
                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                            className="w-full px-3 py-2 border border-stone-200 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 focus:outline-none transition-all text-stone-900 font-medium placeholder:text-stone-300"
                            placeholder="john@example.com"
                        />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-1">
                            <label className="text-[10px] font-bold text-stone-600 uppercase tracking-wider">Designation</label>
                            <input
                                type="text"
                                value={formData.designation}
                                onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                                className="w-full px-3 py-2 border border-stone-200 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 focus:outline-none transition-all text-stone-900 font-medium placeholder:text-stone-300"
                                placeholder="Manager"
                            />
                        </div>
                        <div className="space-y-1">
                            <label className="text-[10px] font-bold text-stone-600 uppercase tracking-wider">LinkedIn URL</label>
                            <input
                                type="text"
                                value={formData.linkedin_url}
                                onChange={(e) => setFormData({ ...formData, linkedin_url: e.target.value })}
                                className="w-full px-3 py-2 border border-stone-200 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 focus:outline-none transition-all text-stone-900 font-medium placeholder:text-stone-300"
                                placeholder="https://linkedin.com/in/..."
                            />
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="pt-4 flex items-center justify-end gap-3 border-t border-gray-100">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-sm bg-stone-500 text-white font-medium hover:bg-stone-700 rounded-lg transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={isSaving}
                            className="bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded-lg text-sm font-bold shadow-lg shadow-green-200 transition-all disabled:opacity-50 flex items-center gap-2"
                        >
                            {isSaving ? (
                                <>
                                    <span className="animate-spin text-xs">⏳</span>
                                    Saving...
                                </>
                            ) : (
                                <>
                                    <span>💾</span>
                                    Save Lead
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
