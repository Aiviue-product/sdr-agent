/**
 * WhatsApp Chat History Component
 * Shows scrollable WhatsApp-style conversation bubbles.
 */
import { useEffect, useRef } from 'react';
import { WhatsAppMessage } from '../../types/whatsapp';

interface WhatsAppChatHistoryProps {
    messages: WhatsAppMessage[];
    loading: boolean;
}

export default function WhatsAppChatHistory({ messages, loading }: WhatsAppChatHistoryProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom like WhatsApp
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center bg-[#e5ddd5]">
                <div className="animate-spin text-2xl">⏳</div>
            </div>
        );
    }

    if (messages.length === 0) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center bg-[#e5ddd5] p-6 text-center">
                <div className="text-4xl mb-4 opacity-50">💬</div>
                <p className="text-stone-500 font-medium whitespace-pre-wrap">
                    No conversation history yet.{"\n"}Messages you send or receive will appear here.
                </p>
            </div>
        );
    }

    const formatTime = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    const getDayLabel = (dateStr: string) => {
        const date = new Date(dateStr);
        const today = new Date();
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);

        if (date.toDateString() === today.toDateString()) return 'TODAY';
        if (date.toDateString() === yesterday.toDateString()) return 'YESTERDAY';

        return date.toLocaleDateString(undefined, {
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        }).toUpperCase();
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'SENT': return <span title="Sent">✓</span>;
            case 'DELIVERED': return <span title="Delivered" className="text-gray-400">✓✓</span>;
            case 'READ': return <span title="Read" className="text-blue-500 font-bold">✓✓</span>;
            case 'FAILED': return <span title="Failed" className="text-red-500">!</span>;
            default: return null;
        }
    };

    // Group messages by date
    const groupedMessages: { date: string, msgs: WhatsAppMessage[] }[] = [];
    messages.forEach(msg => {
        const dateLabel = getDayLabel(msg.created_at);
        const lastGroup = groupedMessages[groupedMessages.length - 1];

        if (lastGroup && lastGroup.date === dateLabel) {
            lastGroup.msgs.push(msg);
        } else {
            groupedMessages.push({ date: dateLabel, msgs: [msg] });
        }
    });

    return (
        <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto p-4 space-y-6 bg-[#e5ddd5] chat-container scroll-smooth"
            style={{
                backgroundImage: 'url("https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png")',
                backgroundRepeat: 'repeat',
                backgroundSize: '300px'
            }}
        >
            {groupedMessages.map((group) => (
                <div key={group.date} className="space-y-4">
                    {/* Day Header */}
                    <div className="flex justify-center sticky top-0 z-10">
                        <span className="bg-[#d1eaed] text-[#54656f] text-[11px] font-bold px-3 py-1 rounded-lg shadow-sm">
                            {group.date}
                        </span>
                    </div>

                    {group.msgs.filter(m => m.message_text).map((msg) => {
                        const isOutbound = msg.direction === 'outbound';

                        return (
                            <div
                                key={msg.id}
                                className={`flex mb-2 ${isOutbound ? 'justify-end' : 'justify-start'}`}
                            >
                                <div
                                    className={`max-w-[85%] min-w-[80px] rounded-lg px-2.5 py-1.5 shadow-sm relative ${isOutbound
                                        ? 'bg-[#dcf8c6] rounded-tr-none'
                                        : 'bg-white rounded-tl-none'
                                        }`}
                                >
                                    {/* Bubble Tail */}
                                    <div className={`absolute top-0 w-0 h-0 border-t-[8px] border-t-transparent ${isOutbound
                                        ? '-right-[6px] border-l-[8px] border-l-[#dcf8c6]'
                                        : '-left-[6px] border-r-[8px] border-r-white'
                                        }`} />

                                    {/* Message Text */}
                                    <p className="text-[13px] text-gray-800 pr-10 leading-relaxed whitespace-pre-wrap">
                                        {msg.message_text}
                                    </p>

                                    {/* Meta: Time + Status */}
                                    <div className="flex items-center justify-end gap-1 mt-0.5 text-[9px] text-gray-400 absolute bottom-1 right-1.5">
                                        <span>{formatTime(msg.created_at)}</span>
                                        {isOutbound && getStatusIcon(msg.status)}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            ))}
        </div>
    );
}
