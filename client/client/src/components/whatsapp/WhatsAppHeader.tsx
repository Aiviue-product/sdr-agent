import Link from 'next/link';
import { WhatsAppTemplate } from '../../types/whatsapp';

interface WhatsAppHeaderProps {
    templates: WhatsAppTemplate[];
    selectedTemplate: string;
    onTemplateChange: (template: string) => void;
    onImportFromEmail: () => void;
    onImportFromLinkedIn: () => void;
    onAddLead: () => void;
    onOpenActivity: () => void;
    onSync: () => void;
    isImportingEmail: boolean;
    isImportingLinkedIn: boolean;
    isSyncing: boolean;
}

export default function WhatsAppHeader({
    templates,
    selectedTemplate,
    onTemplateChange,
    onImportFromEmail,
    onImportFromLinkedIn,
    onAddLead,
    onOpenActivity,
    onSync,
    isImportingEmail,
    isImportingLinkedIn,
    isSyncing
}: WhatsAppHeaderProps) {
    return (
        <header className="bg-gradient-to-r from-green-600 to-green-700 text-white px-6 py-4 shadow-lg">
            <div className="flex items-center justify-between">
                {/* Title */}
                <div className="flex items-center gap-3 flex-shrink-0">
                    <div className="text-3xl">📱</div>
                    <div>
                        <h1 className="text-xl font-bold leading-none">WhatsApp Outreach</h1>
                        <p className="text-green-200 text-xs mt-1 whitespace-nowrap">Send template messages via WATI</p>
                    </div>
                </div>

                {/* Controls */}
                <div className="flex items-center gap-4 overflow-x-auto no-scrollbar pb-1">
                    {/* Nav: Back to Home */}
                    <Link
                        href="/"
                        className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm font-bold transition-colors border border-white/10 whitespace-nowrap shadow-sm"
                        title="Back to Home"
                    >
                        <span>🏠</span>
                        Home
                    </Link>

                    {/* Vertical Divider */}
                    <div className="w-px h-8 bg-white/20 mx-1" />

                    {/* Sync Button */}
                    <button
                        onClick={onSync}
                        disabled={isSyncing}
                        className="flex items-center gap-2 bg-white/20 hover:bg-yellow-600 text-white px-4 py-2 rounded-lg text-sm font-bold transition-colors disabled:opacity-50 shadow-md whitespace-nowrap"
                        title="Sync with WATI"
                    >
                        {isSyncing ? (
                            <><span className="animate-spin">🔄</span> Syncing</>
                        ) : (
                            <><span className="">🔄</span> Sync</>
                        )}
                    </button>

                    {/* Add Lead Button */}
                    <button
                        onClick={onAddLead}
                        className="flex items-center gap-2 bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors border border-white/30 whitespace-nowrap"
                    >
                        <span>➕</span>
                        Add Lead
                    </button>

                    {/* Template Selector */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                        <label className="text-sm text-green-100 font-medium whitespace-nowrap">Template:</label>
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
                            disabled={isImportingEmail}
                            className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 shadow-md whitespace-nowrap"
                        >
                            {isImportingEmail ? <span className="animate-spin">⏳</span> : <span>📩</span>}
                            Email import
                        </button>

                        <button
                            onClick={onImportFromLinkedIn}
                            disabled={isImportingLinkedIn}
                            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 shadow-md whitespace-nowrap"
                        >
                            {isImportingLinkedIn ? <span className="animate-spin">⏳</span> : <span>🔗</span>}
                            LinkedIn import
                        </button>
                    </div>

                    {/* Activity Button */}
                    <button
                        onClick={onOpenActivity}
                        className="flex items-center gap-2 bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
                    >
                        <span>📋</span>
                        Log
                    </button>
                </div>
            </div>
        </header>
    );
}
