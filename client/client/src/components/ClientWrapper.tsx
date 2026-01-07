'use client';

import { ReactNode } from 'react';
import ErrorBoundary from './ErrorBoundary';

interface ClientWrapperProps {
    children: ReactNode;
}

/**
 * ClientWrapper Component
 * Wraps children with error boundary for client-side error handling
 */
export function ClientWrapper({ children }: ClientWrapperProps) {
    return (
        <ErrorBoundary>
            {children}
        </ErrorBoundary>
    );
}
