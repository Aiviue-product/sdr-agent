'use client';

import { Building2, ChevronRight, Rocket, User } from 'lucide-react';
import { LinkedInLead } from '../../types/linkedin';

interface LeadCardProps {
    lead: LinkedInLead;
    isSelected: boolean;
    isBulkSelected: boolean;
    onSelect: (id: number) => void;
    onToggleBulk: (id: number) => void;
}

export default function LeadCard({
    lead,
    isSelected,
    isBulkSelected,
    onSelect,
    onToggleBulk
}: LeadCardProps) {
    return (
        <div
            onClick={() => onSelect(lead.id)}
            className={`
                p-4 border-b border-gray-50 cursor-pointer transition-colors hover:bg-gray-50
                ${isSelected ? 'bg-blue-50 border-l-4 border-l-blue-600' : 'border-l-4 border-l-transparent'}
            `}
        >
            <div className="flex items-start gap-3">
                <input
                    type="checkbox"
                    checked={isBulkSelected}
                    onChange={(e) => {
                        e.stopPropagation();
                        onToggleBulk(lead.id);
                    }}
                    onClick={(e) => e.stopPropagation()}
                    className="w-4 h-4 mt-3 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                />

                <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0
                    ${lead.is_company ? 'bg-purple-100' : 'bg-blue-100'}`}
                >
                    {lead.is_company ? (
                        <Building2 className="w-5 h-5 text-purple-600" />
                    ) : (
                        <User className="w-5 h-5 text-blue-600" />
                    )}
                </div>

                <div className="flex-1 min-w-0">
                    <h3 className={`font-semibold flex items-center gap-2 ${isSelected ? 'text-blue-900' : 'text-gray-900'}`}>
                        <span className="truncate">{lead.full_name}</span>
                        {lead.hiring_signal && (
                            <Rocket className="w-4 h-4 text-green-600 fill-green-100 flex-shrink-0" />
                        )}
                        {lead.connection_status === 'pending' && (
                            <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded font-bold flex-shrink-0">
                                Pending
                            </span>
                        )}
                        {lead.connection_status === 'connected' && (
                            <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-bold flex-shrink-0">
                                Connected
                            </span>
                        )}
                        {lead.is_dm_sent && (
                            <span className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-bold flex-shrink-0">
                                Sent ✓
                            </span>
                        )}
                    </h3>
                    <p className="text-sm text-gray-500 truncate mt-0.5">
                        {lead.headline || lead.company_name || 'No headline'}
                    </p>
                    {lead.hiring_signal && lead.hiring_roles && (
                        <p className="text-xs text-green-700 font-medium mt-1.5 bg-green-50 px-2 py-1 rounded w-fit max-w-full truncate border border-green-100">
                            🏢 {lead.hiring_roles}
                        </p>
                    )}
                </div>
                <ChevronRight className={`w-4 h-4 mt-3 flex-shrink-0 ${isSelected ? 'text-blue-500' : 'text-gray-300'}`} />
            </div>
        </div>
    );
}
