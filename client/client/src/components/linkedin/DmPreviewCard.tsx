'use client';

import { Copy, MessageCircle } from 'lucide-react';

interface DmPreviewCardProps {
    dm: string | null | undefined;
    onCopy: () => void;
}

export default function DmPreviewCard({ dm, onCopy }: DmPreviewCardProps) {
    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-100 flex justify-between items-center">
                <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                    <MessageCircle className="w-4 h-4 text-blue-600" />
                    AI-Generated LinkedIn DM
                </h3>
                <button
                    onClick={onCopy}
                    className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                    <Copy className="w-4 h-4" />
                    Copy
                </button>
            </div>
            <div className="p-6">
                <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                    {dm || 'No DM generated yet. Run a new search to generate DMs.'}
                </p>
                <p className="text-xs text-gray-400 mt-4">
                    {dm?.length || 0} / 400 characters
                </p>
            </div>
        </div>
    );
}
