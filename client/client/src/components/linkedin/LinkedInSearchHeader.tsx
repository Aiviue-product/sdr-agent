'use client';

import { ArrowLeft, Loader2, Search, Users } from 'lucide-react';
import Link from 'next/link';

interface LinkedInSearchHeaderProps {
    searchKeywords: string;
    onKeywordsChange: (value: string) => void;
    dateFilter: string;
    onDateFilterChange: (value: any) => void;
    postsPerKeyword: number;
    onPostsPerKeywordChange: (value: number) => void;
    onSearch: () => void;
    onOpenActivity: () => void;
    isSearching: boolean;
}

export default function LinkedInSearchHeader({
    searchKeywords,
    onKeywordsChange,
    dateFilter,
    onDateFilterChange,
    postsPerKeyword,
    onPostsPerKeywordChange,
    onSearch,
    onOpenActivity,
    isSearching
}: LinkedInSearchHeaderProps) {
    return (
        <div className="bg-white border-b border-pink-300 p-4 shadow-sm z-10">
            <div className="max-w-6xl mx-auto">
                <div className="flex items-center gap-4 mb-4">
                    <Link href="/" className="text-gray-500 hover:text-gray-800 flex items-center gap-1 text-xs font-bold transition-colors">
                        <ArrowLeft className="w-3 h-3" /> Back to Home
                    </Link>
                    <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                        <Search className="w-5 h-5 text-blue-600" />
                        LinkedIn Signal Search
                    </h1>
                </div>

                <div className="flex items-end gap-4 flex-wrap">
                    <div className="flex-1 min-w-[300px]">
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                            Keywords (comma-separated)
                        </label>
                        <input
                            type="text"
                            value={searchKeywords}
                            onChange={(e) => onKeywordsChange(e.target.value)}
                            placeholder="hiring software engineer, looking for developers"
                            className="w-full px-4 py-2 border border-pink-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-gray-900 placeholder:text-gray-400 bg-white"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                            Date Range
                        </label>
                        <select
                            value={dateFilter}
                            onChange={(e) => onDateFilterChange(e.target.value)}
                            className="px-4 py-2 border border-pink-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white text-gray-900"
                        >
                            <option value="past-24h">Past 24 Hours</option>
                            <option value="past-week">Past Week</option>
                            <option value="past-month">Past Month</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                            Posts/Keyword
                        </label>
                        <input
                            type="number"
                            value={postsPerKeyword}
                            onChange={(e) => onPostsPerKeywordChange(parseInt(e.target.value) || 10)}
                            min={1}
                            max={50}
                            className="w-20 px-3 py-2 border border-pink-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-gray-900 bg-white"
                        />
                    </div>

                    <div className="flex items-center gap-2">
                        <button
                            onClick={onSearch}
                            disabled={isSearching}
                            className={`flex items-center gap-2 px-6 py-2 rounded-lg font-bold transition-all
                                ${isSearching
                                    ? 'bg-gray-200 text-gray-400 cursor-wait'
                                    : 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-200'
                                }`}
                        >
                            {isSearching ? (
                                <><Loader2 className="w-4 h-4 animate-spin" /> Searching...</>
                            ) : (
                                <><Search className="w-4 h-4" /> Search</>
                            )}
                        </button>

                        <button
                            onClick={onOpenActivity}
                            className="flex items-center gap-2 px-6 py-2 rounded-lg font-bold bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-700 hover:to-pink-700 shadow-lg shadow-purple-200 transition-all"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                            Global Activity
                        </button>

                        <Link
                            href="/linkedin-signals/leads"
                            className="flex items-center gap-2 px-6 py-2 rounded-lg font-bold bg-gradient-to-r from-teal-600 to-cyan-600 text-white hover:from-teal-700 hover:to-cyan-700 shadow-lg shadow-teal-200 transition-all"
                        >
                            <Users className="w-4 h-4" />
                            Show My Leads
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
