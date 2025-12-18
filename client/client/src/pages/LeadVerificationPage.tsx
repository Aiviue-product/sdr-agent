/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import { AlertCircle, CheckCircle2, Download, Loader2, Megaphone, ShieldCheck, Zap } from 'lucide-react';
import { useRouter } from 'next/navigation';
import React, { useState } from 'react';
import { FileUploader } from '../components/FileUploader';
import { verifyLeads } from '../services/email-verification/api';

export const LeadVerificationPage = () => {
    const router = useRouter();
    const [file, setFile] = useState<File | null>(null);
    const [mode, setMode] = useState<'individual' | 'bulk'>('individual');

    // Status now tracks the flow: idle -> loading -> success (options shown) -> error
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');

    // We store the verified file URL here so we can download it later
    const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

    const handleVerify = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) return;

        setStatus('loading');
        setErrorMessage('');
        setDownloadUrl(null);

        try {
            // NOTE: Ensure your verifyLeads API returns the Blob object!
            const responseBlob = await verifyLeads(file, mode);

            // Create a local URL for the verified file
            const url = window.URL.createObjectURL(responseBlob as Blob);
            setDownloadUrl(url);

            setStatus('success');
        } catch (err: any) {
            setStatus('error');
            setErrorMessage(err.message || 'Something went wrong');
        }
    };

    const handleDownload = () => {
        if (downloadUrl) {
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = 'verified_leads_output.xlsx';
            document.body.appendChild(a);
            a.click();
            a.remove();
        }
    };

    const handleMoveToCampaign = () => {
        // Later you will implement the actual route
        // router.push('/campaigns/new'); 
        alert("Redirecting to Campaign Setup...");
    };

    return (
        <div className="min-h-screen bg-purple-100 py-12 px-4 sm:px-6 lg:px-8 font-sans flex flex-col justify-center">
            <div className="max-w-xl mx-auto w-full">
                {/* Header Section */}
                <div className="text-center mb-10">
                    <div className="inline-flex items-center justify-center p-3 bg-indigo-600 rounded-xl shadow-lg mb-4">
                        <ShieldCheck className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
                        Lead Verification Pro
                    </h1>
                    <p className="mt-2 text-gray-600">
                        Securely verify top-priority leads using AIVI.
                    </p>
                </div>

                {/* Main Card */}
                <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
                    <div className="p-6 sm:p-8 space-y-8">

                        {/* Step 1: File Upload */}
                        <div className="space-y-3">
                            <label className="text-sm font-bold text-gray-900 uppercase tracking-wide">
                                1. Upload Lead Data
                            </label>
                            <FileUploader
                                onFileSelect={setFile}
                                selectedFile={file}
                                disabled={status === 'loading' || status === 'success'}
                            />
                        </div>

                        {/* Step 2: Mode Selection */}
                        <div className="space-y-3">
                            <label className="text-sm font-bold text-gray-900 uppercase tracking-wide">
                                2. Verification Speed
                            </label>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <button
                                    type="button"
                                    onClick={() => setMode('individual')}
                                    disabled={status === 'loading' || status === 'success'}
                                    className={`
                                        relative flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all
                                        ${mode === 'individual'
                                            ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                                            : 'border-gray-200 hover:border-gray-300 text-gray-600'}
                                    `}
                                >
                                    <ShieldCheck className="w-6 h-6 mb-2" />
                                    <span className="font-semibold text-sm">Precision Mode</span>
                                    <span className="text-xs opacity-75 mt-1">Individual checks (Slower)</span>
                                </button>

                                <button
                                    type="button"
                                    onClick={() => setMode('bulk')}
                                    disabled={status === 'loading' || status === 'success'}
                                    className={`
                                        relative flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all
                                        ${mode === 'bulk'
                                            ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                                            : 'border-gray-200 hover:border-gray-300 text-gray-600'}
                                    `}
                                >
                                    <Zap className="w-6 h-6 mb-2" />
                                    <span className="font-semibold text-sm">Turbo Mode</span>
                                    <span className="text-xs opacity-75 mt-1">Bulk API (Fast)</span>
                                </button>
                            </div>
                        </div>

                        {/* Initial Verification Action Button (Hidden after success) */}
                        {status !== 'success' && (
                            <button
                                onClick={handleVerify}
                                disabled={!file || status === 'loading'}
                                className={`
                                    w-full flex items-center justify-center py-4 px-6 rounded-xl text-white font-bold text-lg shadow-lg
                                    transform transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500
                                    ${!file || status === 'loading'
                                        ? 'bg-gray-300 cursor-not-allowed'
                                        : 'bg-indigo-600 hover:bg-indigo-700 hover:-translate-y-0.5'}
                                `}
                            >
                                {status === 'loading' ? (
                                    <>
                                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                        Processing Leads...
                                    </>
                                ) : (
                                    'Verify Leads'
                                )}
                            </button>
                        )}
                    </div>

                    {/* SUCCESS STATE: Two Buttons for User Choice */}
                    {status === 'success' && (
                        <div className="bg-green-50 p-6 sm:p-8 border-t border-green-100 animate-in slide-in-from-bottom-5">
                            <div className="flex items-center gap-3 mb-6">
                                <div className="p-2 bg-green-100 rounded-full">
                                    <CheckCircle2 className="w-6 h-6 text-green-600" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-bold text-green-900">Verification Successful!</h3>
                                    <p className="text-sm text-green-700">Your data is ready. What would you like to do next?</p>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                {/* Button 1: Download */}
                                <button
                                    onClick={handleDownload}
                                    className="flex items-center justify-center py-3 px-4 rounded-xl border-2 border-green-600 text-green-700 font-bold bg-white hover:bg-green-50 transition-colors shadow-sm"
                                >
                                    <Download className="w-5 h-5 mr-2" />
                                    Download Leads
                                </button>

                                {/* Button 2: Move to Campaign */}
                                <button
                                    onClick={handleMoveToCampaign}
                                    className="flex items-center justify-center py-3 px-4 rounded-xl bg-indigo-600 text-white font-bold hover:bg-indigo-700 shadow-md transition-all hover:-translate-y-0.5"
                                >
                                    <Megaphone className="w-5 h-5 mr-2" />
                                    Move to Campaign
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Error State */}
                    {status === 'error' && (
                        <div className="bg-red-50 p-4 border-t border-red-100 flex items-start gap-3 animate-in slide-in-from-bottom-5">
                            <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                            <div>
                                <p className="font-medium text-red-900">Verification Failed</p>
                                <p className="text-sm text-red-700">{errorMessage}</p>
                            </div>
                        </div>
                    )}
                </div>

                <p className="text-center text-sm text-stone-600 mt-8">
                    Powered by Aiviue
                </p>
            </div>
        </div>
    );
};