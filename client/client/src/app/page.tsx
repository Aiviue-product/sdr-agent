'use client';

import { AlertCircle, CheckCircle2, Loader2, ShieldCheck, Zap } from 'lucide-react';
import React, { useState } from 'react';
import { FileUploader } from '../components/FileUploader';
import { verifyLeads } from '../services/email-verification/api';

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<'individual' | 'bulk'>('individual');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setStatus('loading');
    setErrorMessage('');

    try {
      await verifyLeads(file, mode);
      setStatus('success');
    } catch (err: any) {
      setStatus('error');
      setErrorMessage(err.message || 'Something went wrong');
    }
  };

  return (
    <main className="min-h-screen bg-purple-200 py-12 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-xl mx-auto">
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
          <div className="p-8 space-y-8">

            {/* Step 1: File Upload */}
            <div className="space-y-3">
              <label className="text-sm font-bold text-gray-900 uppercase tracking-wide">
                1. Upload Lead Data
              </label>
              <FileUploader
                onFileSelect={setFile}
                selectedFile={file}
                disabled={status === 'loading'}
              />
            </div>

            {/* Step 2: Mode Selection */}
            <div className="space-y-3">
              <label className="text-sm font-bold text-gray-900 uppercase tracking-wide">
                2. Verification Speed
              </label>
              <div className="grid grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() => setMode('individual')}
                  disabled={status === 'loading'}
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
                  disabled={status === 'loading'}
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

            {/* Action Button */}
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
                'Start Verification & Download'
              )}
            </button>
          </div>

          {/* Status Footer */}
          {status === 'success' && (
            <div className="bg-green-50 p-4 border-t border-green-100 flex items-start gap-3 animate-in slide-in-from-bottom-5">
              <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-green-900">Verification Complete!</p>
                <p className="text-sm text-green-700">Your processed file has been downloaded automatically.</p>
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="bg-red-50 p-4 border-t border-red-100 flex items-start gap-3 animate-in slide-in-from-bottom-5">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
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
    </main>
  );
}