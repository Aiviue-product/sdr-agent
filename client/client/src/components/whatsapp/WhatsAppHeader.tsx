/**
 * WhatsApp Header Component
 * Top bar with template selector, import button, and activity button.
 */
import { WhatsAppTemplate } from '../../types/whatsapp';

interface WhatsAppHeaderProps {
    templates: WhatsAppTemplate[];
    selectedTemplate: string;
    onTemplateChange: (template: string) => void;
    onImportFromEmail: () => void;
    onImportFromLinkedIn: () => void;
    onAddLead: () => void;
    onOpenActivity: () => void;
    isImporting: boolean;
}

export default function WhatsAppHeader({
    templates,
    selectedTemplate,
    onTemplateChange,
    onImportFromEmail,
    onImportFromLinkedIn,
    onAddLead,
    onOpenActivity,
    isImporting
}: WhatsAppHeaderProps) {
    return (
        <header className="bg-gradient-to-r from-green-600 to-green-700 text-white px-6 py-4 shadow-lg">
            <div className="flex items-center justify-between">
                {/* Title */}
                <div className="flex items-center gap-3">
                    <div className="text-3xl">📱</div>
                    <div>
                        <h1 className="text-xl font-bold">WhatsApp Outreach</h1>
                        <p className="text-green-200 text-sm">Send template messages via WATI</p>
                    </div>
                </div>

                {/* Controls */}
                <div className="flex items-center gap-4">
                    {/* Add Lead Button */}
                    <button
                        onClick={onAddLead}
                        className="flex items-center gap-2 bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors border border-white/30"
                    >
                        <span>➕</span>
                        Add Lead
                    </button>

                    {/* Template Selector */}
                    <div className="flex items-center gap-2">
                        <label className="text-sm text-green-100 font-medium">Template:</label>
                        <select
                            value={selectedTemplate}
                            onChange={(e) => onTemplateChange(e.target.value)}
                            className="bg-white/20 text-white border border-white/40 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-white/50 backdrop-blur-sm font-semibold"
                        >
                            {templates.map((t) => (
                                <option key={t.name} value={t.name} className="text-stone-900 bg-white">
                                    {t.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Import Buttons */}
                    <div className="flex items-center gap-2">
                        <button
                            onClick={onImportFromEmail}
                            disabled={isImporting}
                            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 shadow-md"
                        >
                            {isImporting ? (
                                <>
                                    <span className="animate-spin text-xs">⏳</span>
                                    Importing...
                                </>
                            ) : (
                                <>
                                    <span>📩</span>
                                    Import from Email
                                </>
                            )}
                        </button>

                        <button
                            onClick={onImportFromLinkedIn}
                            disabled={isImporting}
                            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 shadow-md"
                        >
                            {isImporting ? (
                                <>
                                    <span className="animate-spin text-xs">⏳</span>
                                    Importing...
                                </>
                            ) : (
                                <>
                                    <span>🔗</span>
                                    Import from LinkedIn
                                </>
                            )}
                        </button>
                    </div>

                    {/* Activity Button */}
                    <button
                        onClick={onOpenActivity}
                        className="flex items-center gap-2 bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                    >
                        <span>📋</span>
                        Activity Log
                    </button>
                </div>
            </div>
        </header>
    );
}
