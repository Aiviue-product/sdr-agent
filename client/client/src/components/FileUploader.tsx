'use client';

import { FileSpreadsheet, UploadCloud, X } from 'lucide-react';
import React, { useCallback, useState } from 'react';
import toast from 'react-hot-toast';

interface FileUploaderProps {
    onFileSelect: (file: File | null) => void;
    selectedFile: File | null;
    disabled?: boolean;
}

export const FileUploader: React.FC<FileUploaderProps> = ({
    onFileSelect,
    selectedFile,
    disabled
}) => {
    const [isDragging, setIsDragging] = useState(false);

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setIsDragging(true);
        } else if (e.type === 'dragleave') {
            setIsDragging(false);
        }
    }, []);

    const validateFile = (file: File): boolean => {
        const MAX_SIZE = 10 * 1024 * 1024; // 10MB
        const allowedExtensions = ['.xlsx', '.csv'];
        const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();

        if (!allowedExtensions.includes(extension)) {
            toast.error('Please upload an Excel (.xlsx) or CSV file.');
            return false;
        }

        if (file.size > MAX_SIZE) {
            toast.error('File is too large. Max allowed size is 10MB.');
            return false;
        }

        return true;
    };

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);

        if (disabled) return;

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const file = e.dataTransfer.files[0];
            if (validateFile(file)) {
                onFileSelect(file);
            }
        }
    }, [onFileSelect, disabled]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            if (validateFile(file)) {
                onFileSelect(file);
            }
        }
    };

    if (selectedFile) {
        return (
            <div className="flex items-center justify-between p-4 bg-blue-50 border border-blue-200 rounded-lg animate-in fade-in slide-in-from-bottom-2">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 rounded-full">
                        <FileSpreadsheet className="w-6 h-6 text-blue-600" />
                    </div>
                    <div>
                        <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
                        <p className="text-xs text-gray-500">{(selectedFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                </div>
                {!disabled && (
                    <button
                        onClick={() => onFileSelect(null)}
                        className="p-1 hover:bg-blue-100 rounded-full transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                )}
            </div>
        );
    }

    return (
        <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`
        relative group cursor-pointer flex flex-col items-center justify-center w-full h-48 
        rounded-xl border-2 border-dashed transition-all duration-200 ease-in-out
        ${isDragging
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-300 bg-gray-50 hover:bg-gray-100 hover:border-gray-400'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
        >
            <input
                type="file"
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
                onChange={handleChange}
                accept=".xlsx,.csv"
                disabled={disabled}
            />
            <div className="flex flex-col items-center text-center p-4">
                <div className={`p-3 rounded-full mb-3 ${isDragging ? 'bg-blue-100' : 'bg-gray-100 group-hover:bg-gray-200'}`}>
                    <UploadCloud className={`w-8 h-8 ${isDragging ? 'text-blue-500' : 'text-gray-400'}`} />
                </div>
                <p className="text-sm font-medium text-gray-700">
                    <span className="text-blue-600">Click to upload</span> or drag and drop
                </p>
                <p className="text-xs text-gray-500 mt-1">Excel (.xlsx) or CSV files only</p>
            </div>
        </div>
    );
}; 